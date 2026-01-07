import asyncio
import logging
from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock, patch

import pandas as pd
import pytest
from dependency_injector.containers import Container
from faker import Faker
from pyee.asyncio import AsyncIOEventEmitter

from crypto_futures_bot.constants import SIGNALS_EVALUATION_RESULT_EVENT_NAME
from crypto_futures_bot.domain.enums import CandleStickEnum, PushNotificationTypeEnum
from crypto_futures_bot.domain.vo import (
    CandleStickIndicators,
    PositionHints,
    SignalParametrizationItem,
    TrackedCryptoCurrencyItem,
    TradeNowHints,
)
from crypto_futures_bot.infrastructure.adapters.futures_exchange.vo import AccountInfo, SymbolTicker
from crypto_futures_bot.infrastructure.tasks.signals_task_service import SignalsTaskService
from tests.helpers.constants import MOCK_CRYPTO_CURRENCIES

logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def should_evaluate_signals_and_emit_event_when_entry_signal_is_found(
    faker: Faker, test_environment: tuple[Container, ...]
) -> None:
    application_container, *_ = test_environment
    signals_task_service: SignalsTaskService = (
        application_container.infrastructure_container().tasks_container().signals_task_service()
    )
    event_emitter: AsyncIOEventEmitter = application_container.infrastructure_container().event_emitter()

    # Mock data
    currency = faker.random_element(MOCK_CRYPTO_CURRENCIES)
    tracked_currency = TrackedCryptoCurrencyItem.from_currency(currency)
    account_info = AccountInfo(currency_code="USDT")
    signal_params = SignalParametrizationItem(crypto_currency=currency)
    ta_df = pd.DataFrame({"col1": [1, 2], "col2": [3, 4]})  # Dummy dataframe
    prev_candle = CandleStickIndicators(
        symbol=tracked_currency.to_symbol(account_info),
        timestamp=datetime.now(UTC),
        index=CandleStickEnum.PREV,
        stoch_rsi_k=0.1,
        stoch_rsi_d=0.2,
        closing_price=100,
        ema50=90,
        macd_hist=-1,
        highest_price=faker.pyfloat(),
        lowest_price=faker.pyfloat(),
        opening_price=faker.pyfloat(),
        macd_line=faker.pyfloat(),
        macd_signal=faker.pyfloat(),
        stoch_rsi=faker.pyfloat(),
        rsi=faker.pyfloat(),
        atr=faker.pyfloat(),
        relative_volume=faker.pyfloat(),
    )
    last_candle = CandleStickIndicators(
        symbol=tracked_currency.to_symbol(account_info),
        timestamp=datetime.now(UTC),
        index=CandleStickEnum.LAST,
        stoch_rsi_k=0.3,
        stoch_rsi_d=0.2,
        closing_price=110,
        ema50=95,
        macd_hist=1,
        highest_price=faker.pyfloat(),
        lowest_price=faker.pyfloat(),
        opening_price=faker.pyfloat(),
        macd_line=faker.pyfloat(),
        macd_signal=faker.pyfloat(),
        stoch_rsi=faker.pyfloat(),
        rsi=faker.pyfloat(),
        atr=faker.pyfloat(),
        relative_volume=faker.pyfloat(),
    )
    position_hints = PositionHints(
        is_long=True,
        is_safe=faker.pybool(),
        margin=faker.pyfloat(positive=True),
        leverage=faker.pyint(min_value=1, max_value=50),
        notional_size=faker.pyfloat(positive=True),
        liquidation_price=faker.pyfloat(positive=True),
        entry_price=faker.pyfloat(positive=True),
        break_even_price=faker.pyfloat(positive=True),
        stop_loss_price=faker.pyfloat(positive=True),
        move_sl_to_break_even_price=faker.pyfloat(positive=True),
        move_sl_to_first_target_profit_price=faker.pyfloat(positive=True),
        take_profit_price=faker.pyfloat(positive=True),
        potential_loss=faker.pyfloat(positive=True),
        potential_profit=faker.pyfloat(positive=True),
    )
    trade_now_hints = TradeNowHints(
        ticker=Mock(spec=SymbolTicker),
        candlestick_indicators=last_candle,
        stop_loss_percent_value=2.0,
        take_profit_percent_value=4.0,
        long=position_hints,
        short=position_hints,
    )

    # Mock services
    mock_get_account_info = AsyncMock(return_value=account_info)
    mock_find_all_tracked = AsyncMock(return_value=[tracked_currency])
    mock_find_params = AsyncMock(return_value=signal_params)
    mock_get_ta = AsyncMock(return_value=ta_df)

    def get_candle_side_effect(symbol, index, technical_analysis_df=None):
        if index == CandleStickEnum.PREV:
            return prev_candle
        return last_candle

    mock_get_candle = AsyncMock(side_effect=get_candle_side_effect)

    mock_get_active_subscriptions = AsyncMock(return_value=["chat123"])
    mock_exists_market_signal = AsyncMock(return_value=False)
    mock_get_symbol_ticker = AsyncMock(return_value=Mock(spec=SymbolTicker))
    mock_get_trade_now_hints = AsyncMock(return_value=trade_now_hints)
    mock_send_message = AsyncMock()
    mock_emit = Mock()

    event_emitter.on(SIGNALS_EVALUATION_RESULT_EVENT_NAME, mock_emit)

    with (
        patch.object(signals_task_service._futures_exchange_service, "get_account_info", mock_get_account_info),
        patch.object(signals_task_service._tracked_crypto_currency_service, "find_all", mock_find_all_tracked),
        patch.object(signals_task_service._signal_parametrization_service, "find_by_crypto_currency", mock_find_params),
        patch.object(signals_task_service._crypto_technical_analysis_service, "get_technical_analysis", mock_get_ta),
        patch.object(
            signals_task_service._crypto_technical_analysis_service, "get_candlestick_indicators", mock_get_candle
        ),
        patch.object(
            signals_task_service._push_notification_service,
            "get_actived_subscription_by_type",
            mock_get_active_subscriptions,
        ),
        patch.object(
            signals_task_service._market_signal_service, "exists_market_signal_by_timestamp", mock_exists_market_signal
        ),
        patch.object(signals_task_service._futures_exchange_service, "get_symbol_ticker", mock_get_symbol_ticker),
        patch.object(signals_task_service._trade_now_service, "get_trade_now_hints", mock_get_trade_now_hints),
        patch.object(signals_task_service._telegram_service, "send_message", mock_send_message),
    ):
        # The logic for long entry should be met with the mocked candles
        # trend_ok: 110 > 95 -> True
        # stoch_cross: 0.1 <= 0.2 and 0.3 > 0.2 -> True
        # stoch_condition: 0.1 < 0.25 (default) -> True
        # macd_positive: 1 > 0 -> True

        await signals_task_service._run()

        # Let event loop run for event to be emitted and handled
        await asyncio.sleep(0.01)

        # Assertions
        mock_get_account_info.assert_called()
        mock_find_all_tracked.assert_called()
        mock_find_params.assert_called_with(crypto_currency=currency)
        mock_get_ta.assert_called_with(symbol=tracked_currency.to_symbol(account_info))
        assert mock_get_candle.call_count == 2
        mock_get_active_subscriptions.assert_called_with(notification_type=PushNotificationTypeEnum.SIGNALS)
        mock_exists_market_signal.assert_called()
        mock_get_trade_now_hints.assert_called()
        mock_send_message.assert_called()

        mock_emit.assert_called()
        emitted_arg = mock_emit.call_args[0][0]
        assert emitted_arg.crypto_currency == tracked_currency
        assert emitted_arg.long_entry is True
        assert emitted_arg.short_entry is False

    event_emitter.remove_listener(SIGNALS_EVALUATION_RESULT_EVENT_NAME, mock_emit)
