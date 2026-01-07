import asyncio
import logging
from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest
from dependency_injector.containers import Container
from faker import Faker
from pyee.asyncio import AsyncIOEventEmitter

from crypto_futures_bot.constants import MARKET_SIGNAL_EVENT_NAME, SIGNALS_EVALUATION_RESULT_EVENT_NAME
from crypto_futures_bot.domain.enums import CandleStickEnum, PositionTypeEnum
from crypto_futures_bot.domain.vo import (
    CandleStickIndicators,
    PositionHints,
    SignalsEvaluationResult,
    TrackedCryptoCurrencyItem,
    TradeNowHints,
)
from crypto_futures_bot.infrastructure.adapters.futures_exchange.vo import SymbolTicker
from crypto_futures_bot.infrastructure.services.market_signal_service import MarketSignalService
from tests.helpers.constants import MOCK_CRYPTO_CURRENCIES

logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def should_store_market_signal_when_a_signals_evaluation_result_is_received(
    faker: Faker, test_environment: tuple[Container, ...]
) -> None:
    application_container, *_ = test_environment
    market_signal_service: MarketSignalService = (
        application_container.infrastructure_container().services_container().market_signal_service()
    )
    event_emitter: AsyncIOEventEmitter = application_container.infrastructure_container().event_emitter()
    market_signal_service.configure()

    currency_str = faker.random_element(MOCK_CRYPTO_CURRENCIES)
    crypto_currency = TrackedCryptoCurrencyItem.from_currency(currency_str)
    signals_evaluation_result = SignalsEvaluationResult(
        crypto_currency=crypto_currency,
        timeframe="15m",
        timestamp=datetime.now(UTC),
        long_entry=True,
        short_entry=False,
    )

    position_hints_long = PositionHints(
        is_long=True,
        is_safe=faker.pybool(),
        margin=faker.pyfloat(),
        leverage=faker.pyfloat(),
        notional_size=faker.pyfloat(),
        liquidation_price=faker.pyfloat(),
        entry_price=faker.pyfloat(),
        break_even_price=faker.pyfloat(),
        stop_loss_price=faker.pyfloat(),
        move_sl_to_break_even_price=faker.pyfloat(),
        move_sl_to_first_target_profit_price=faker.pyfloat(),
        take_profit_price=faker.pyfloat(),
        potential_loss=faker.pyfloat(),
        potential_profit=faker.pyfloat(),
    )
    position_hints_short = PositionHints(
        is_long=False,
        is_safe=faker.pybool(),
        margin=faker.pyfloat(),
        leverage=faker.pyfloat(),
        notional_size=faker.pyfloat(),
        liquidation_price=faker.pyfloat(),
        entry_price=faker.pyfloat(),
        break_even_price=faker.pyfloat(),
        stop_loss_price=faker.pyfloat(),
        move_sl_to_break_even_price=faker.pyfloat(),
        move_sl_to_first_target_profit_price=faker.pyfloat(),
        take_profit_price=faker.pyfloat(),
        potential_loss=faker.pyfloat(),
        potential_profit=faker.pyfloat(),
    )
    symbol_ticker = SymbolTicker(
        timestamp=int(datetime.now(UTC).timestamp() * 1000), symbol=f"{currency_str}/USDT:USDT", close=faker.pyfloat()
    )
    candlestick_indicators = CandleStickIndicators(
        symbol=f"{currency_str}/USDT:USDT",
        timestamp=datetime.now(UTC),
        index=CandleStickEnum.CURRENT,
        highest_price=faker.pyfloat(),
        lowest_price=faker.pyfloat(),
        opening_price=faker.pyfloat(),
        closing_price=faker.pyfloat(),
        ema50=faker.pyfloat(),
        macd_line=faker.pyfloat(),
        macd_signal=faker.pyfloat(),
        macd_hist=faker.pyfloat(),
        stoch_rsi=faker.pyfloat(),
        stoch_rsi_k=faker.pyfloat(),
        stoch_rsi_d=faker.pyfloat(),
        rsi=faker.pyfloat(),
        atr=faker.pyfloat(),
        relative_volume=faker.pyfloat(),
    )
    trade_now_hints = TradeNowHints(
        ticker=symbol_ticker,
        candlestick_indicators=candlestick_indicators,
        stop_loss_percent_value=faker.pyfloat(),
        take_profit_percent_value=faker.pyfloat(),
        long=position_hints_long,
        short=position_hints_short,
    )
    mock_get_trade_now_hints = AsyncMock(return_value=trade_now_hints)

    market_signal_handler = Mock()
    event_emitter.add_listener(MARKET_SIGNAL_EVENT_NAME, market_signal_handler)

    with patch.object(market_signal_service._trade_now_service, "get_trade_now_hints", mock_get_trade_now_hints):
        event_emitter.emit(SIGNALS_EVALUATION_RESULT_EVENT_NAME, signals_evaluation_result)
        await asyncio.sleep(0.1)

        mock_get_trade_now_hints.assert_called_once_with(crypto_currency)
        market_signal_handler.assert_called_once()

        all_signals = await market_signal_service.find_all_market_signals(crypto_currency)
        assert len(all_signals) == 1
        assert all_signals[0].position_type == PositionTypeEnum.LONG

    event_emitter.remove_listener(MARKET_SIGNAL_EVENT_NAME, market_signal_handler)


@pytest.mark.asyncio
async def should_find_all_market_signals_properly(faker: Faker, test_environment: tuple[Container, ...]) -> None:
    application_container, *_ = test_environment
    market_signal_service: MarketSignalService = (
        application_container.infrastructure_container().services_container().market_signal_service()
    )
    event_emitter: AsyncIOEventEmitter = application_container.infrastructure_container().event_emitter()
    market_signal_service.configure()

    currency_str = faker.random_element(MOCK_CRYPTO_CURRENCIES)
    crypto_currency = TrackedCryptoCurrencyItem.from_currency(currency_str)

    # Emit a long entry signal
    signals_evaluation_result_long = SignalsEvaluationResult(
        crypto_currency=crypto_currency,
        timeframe="15m",
        timestamp=datetime.now(UTC),
        long_entry=True,
        short_entry=False,
    )
    position_hints_long = PositionHints(
        is_long=True,
        is_safe=faker.pybool(),
        margin=faker.pyfloat(),
        leverage=faker.pyfloat(),
        notional_size=faker.pyfloat(),
        liquidation_price=faker.pyfloat(),
        entry_price=faker.pyfloat(),
        break_even_price=faker.pyfloat(),
        stop_loss_price=faker.pyfloat(),
        move_sl_to_break_even_price=faker.pyfloat(),
        move_sl_to_first_target_profit_price=faker.pyfloat(),
        take_profit_price=faker.pyfloat(),
        potential_loss=faker.pyfloat(),
        potential_profit=faker.pyfloat(),
    )
    position_hints_short = PositionHints(
        is_long=False,
        is_safe=faker.pybool(),
        margin=faker.pyfloat(),
        leverage=faker.pyfloat(),
        notional_size=faker.pyfloat(),
        liquidation_price=faker.pyfloat(),
        entry_price=faker.pyfloat(),
        break_even_price=faker.pyfloat(),
        stop_loss_price=faker.pyfloat(),
        move_sl_to_break_even_price=faker.pyfloat(),
        move_sl_to_first_target_profit_price=faker.pyfloat(),
        take_profit_price=faker.pyfloat(),
        potential_loss=faker.pyfloat(),
        potential_profit=faker.pyfloat(),
    )
    symbol_ticker = SymbolTicker(
        timestamp=int(datetime.now(UTC).timestamp() * 1000), symbol=f"{currency_str}/USDT:USDT", close=faker.pyfloat()
    )
    candlestick_indicators = CandleStickIndicators(
        symbol=f"{currency_str}/USDT:USDT",
        timestamp=datetime.now(UTC),
        index=CandleStickEnum.CURRENT,
        highest_price=faker.pyfloat(),
        lowest_price=faker.pyfloat(),
        opening_price=faker.pyfloat(),
        closing_price=faker.pyfloat(),
        ema50=faker.pyfloat(),
        macd_line=faker.pyfloat(),
        macd_signal=faker.pyfloat(),
        macd_hist=faker.pyfloat(),
        stoch_rsi=faker.pyfloat(),
        stoch_rsi_k=faker.pyfloat(),
        stoch_rsi_d=faker.pyfloat(),
        rsi=faker.pyfloat(),
        atr=faker.pyfloat(),
        relative_volume=faker.pyfloat(),
    )
    trade_now_hints = TradeNowHints(
        ticker=symbol_ticker,
        candlestick_indicators=candlestick_indicators,
        stop_loss_percent_value=faker.pyfloat(),
        take_profit_percent_value=faker.pyfloat(),
        long=position_hints_long,
        short=position_hints_short,
    )
    mock_get_trade_now_hints = AsyncMock(return_value=trade_now_hints)
    with patch.object(market_signal_service._trade_now_service, "get_trade_now_hints", mock_get_trade_now_hints):
        event_emitter.emit(SIGNALS_EVALUATION_RESULT_EVENT_NAME, signals_evaluation_result_long)
        await asyncio.sleep(0.1)

    # Find all signals
    all_signals = await market_signal_service.find_all_market_signals(crypto_currency)
    assert len(all_signals) > 0

    # Find long signals
    long_signals = await market_signal_service.find_all_market_signals(
        crypto_currency, position_type=PositionTypeEnum.LONG
    )
    assert len(long_signals) > 0

    # Find short signals
    short_signals = await market_signal_service.find_all_market_signals(
        crypto_currency, position_type=PositionTypeEnum.SHORT
    )
    assert len(short_signals) == 0

    # Find signals for a specific timeframe
    timeframe_signals = await market_signal_service.find_all_market_signals(crypto_currency, timeframe="15m")
    assert len(timeframe_signals) > 0

    # Find signals for a different timeframe
    other_timeframe_signals = await market_signal_service.find_all_market_signals(crypto_currency, timeframe="1h")
    assert len(other_timeframe_signals) == 0
