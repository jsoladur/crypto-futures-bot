import logging
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from dependency_injector.containers import Container
from faker import Faker

from crypto_futures_bot.domain.enums import (
    CandleStickEnum,
    OpenPositionResultTypeEnum,
    PositionOpenTypeEnum,
    PositionTypeEnum,
)
from crypto_futures_bot.domain.vo import (
    CandleStickIndicators,
    PositionHints,
    PositionMetrics,
    RiskManagementItem,
    SignalParametrizationItem,
    TrackedCryptoCurrencyItem,
    TradeNowHints,
)
from crypto_futures_bot.infrastructure.adapters.futures_exchange.vo.account_info import AccountInfo
from crypto_futures_bot.infrastructure.adapters.futures_exchange.vo.futures_wallet import FuturesWallet
from crypto_futures_bot.infrastructure.adapters.futures_exchange.vo.portfolio_balance import PortfolioBalance
from crypto_futures_bot.infrastructure.adapters.futures_exchange.vo.position import Position
from crypto_futures_bot.infrastructure.adapters.futures_exchange.vo.symbol_market_config import SymbolMarketConfig
from crypto_futures_bot.infrastructure.adapters.futures_exchange.vo.symbol_ticker import SymbolTicker
from crypto_futures_bot.infrastructure.services.trade_now_service import TradeNowService
from tests.helpers.constants import MOCK_CRYPTO_CURRENCIES

logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def should_get_trade_now_hints_properly(faker: Faker, test_environment: tuple[Container, ...]) -> None:
    application_container, *_ = test_environment
    trade_now_service: TradeNowService = (
        application_container.infrastructure_container().services_container().trade_now_service()
    )

    currency = faker.random_element(MOCK_CRYPTO_CURRENCIES)
    symbol = f"{currency}/USDT:USDT"
    tracked_currency = TrackedCryptoCurrencyItem.from_currency(currency)
    account_info = AccountInfo(currency_code="USDT")
    portfolio_balance = PortfolioBalance(spot_balance=1000.0, futures_balance=500.0, currency_code="USDT")
    futures_wallet = FuturesWallet(
        currency="USDT",
        equity=faker.pyfloat(),
        position_margin=faker.pyfloat(),
        available_balance=250.0,
        cash_balance=faker.pyfloat(),
        unrealized_pnl=faker.pyfloat(),
    )
    ticker = SymbolTicker(timestamp=int(datetime.now(UTC).timestamp() * 1000), symbol=symbol, close=100.0)
    signal_params = SignalParametrizationItem(crypto_currency=currency)
    market_config = SymbolMarketConfig(symbol=symbol, price_precision=2, amount_precision=3, contract_size=0.001)
    candlestick_indicators = CandleStickIndicators(
        symbol=ticker.symbol,
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

    with (
        patch.object(
            trade_now_service._futures_exchange_service, "get_account_info", AsyncMock(return_value=account_info)
        ),
        patch.object(
            trade_now_service._futures_exchange_service,
            "get_portfolio_balance",
            AsyncMock(return_value=portfolio_balance),
        ),
        patch.object(
            trade_now_service._futures_exchange_service, "get_futures_wallet", AsyncMock(return_value=futures_wallet)
        ),
        patch.object(trade_now_service._futures_exchange_service, "get_symbol_ticker", AsyncMock(return_value=ticker)),
        patch.object(
            trade_now_service._signal_parametrization_service,
            "find_by_crypto_currency",
            AsyncMock(return_value=signal_params),
        ),
        patch.object(
            trade_now_service._futures_exchange_service,
            "get_symbol_market_config",
            AsyncMock(return_value=market_config),
        ),
        patch.object(
            trade_now_service._crypto_technical_analysis_service,
            "get_candlestick_indicators",
            AsyncMock(return_value=candlestick_indicators),
        ),
        patch.object(trade_now_service._tracked_crypto_currency_service, "count", AsyncMock(return_value=1)),
        patch.object(trade_now_service._risk_management_service, "get", AsyncMock(return_value=RiskManagementItem())),
    ):
        hints = await trade_now_service.get_trade_now_hints(tracked_currency)
        assert isinstance(hints, TradeNowHints)
        assert hints.long is not None
        assert hints.short is not None


@pytest.mark.asyncio
async def should_open_position_successfully(faker: Faker, test_environment: tuple[Container, ...]) -> None:
    application_container, *_ = test_environment
    trade_now_service: TradeNowService = (
        application_container.infrastructure_container().services_container().trade_now_service()
    )

    currency = faker.random_element(MOCK_CRYPTO_CURRENCIES)
    symbol = f"{currency}/USDT:USDT"
    tracked_currency = TrackedCryptoCurrencyItem.from_currency(currency)
    position_hints = PositionHints(
        is_long=True,
        is_safe=faker.pybool(),
        margin=100.0,
        leverage=10,
        notional_size=faker.pyfloat(),
        liquidation_price=faker.pyfloat(),
        entry_price=faker.pyfloat(),
        break_even_price=faker.pyfloat(),
        stop_loss_price=90.0,
        move_sl_to_break_even_price=faker.pyfloat(),
        move_sl_to_first_target_profit_price=faker.pyfloat(),
        take_profit_price=110.0,
        potential_loss=faker.pyfloat(),
        potential_profit=faker.pyfloat(),
    )
    ticker = SymbolTicker(timestamp=int(datetime.now(UTC).timestamp() * 1000), symbol=symbol, close=100.0)
    candlestick_indicators = CandleStickIndicators(
        symbol=symbol,
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
        ticker=ticker,
        candlestick_indicators=candlestick_indicators,
        stop_loss_percent_value=faker.pyfloat(),
        take_profit_percent_value=faker.pyfloat(),
        long=position_hints,
        short=position_hints,
    )
    opened_position = Position(
        position_id=faker.pystr(),
        symbol=symbol,
        leverage=10,
        entry_price=25000.0,
        position_type=PositionTypeEnum.LONG,
        liquidation_price=faker.pyfloat(),
        contracts=faker.pyfloat(),
        contract_size=faker.pyfloat(),
        fee=faker.pyfloat(),
        initial_margin=faker.pyfloat(),
        open_type=PositionOpenTypeEnum.ISOLATED,
    )

    with (
        patch.object(
            trade_now_service._orders_analytics_service, "get_open_position_metrics", AsyncMock(return_value=[])
        ),
        patch.object(trade_now_service, "get_trade_now_hints", AsyncMock(return_value=trade_now_hints)),
        patch.object(
            trade_now_service._futures_exchange_service,
            "create_market_position_order",
            AsyncMock(return_value=opened_position),
        ),
        patch.object(trade_now_service._orders_analytics_service, "get_metrics_by_position_id", AsyncMock()),
        patch.object(
            trade_now_service._futures_exchange_service,
            "get_account_info",
            AsyncMock(return_value=AccountInfo(currency_code="USDT")),
        ),
    ):
        result = await trade_now_service.open_position(tracked_currency, PositionTypeEnum.LONG)
        assert result.result_type == OpenPositionResultTypeEnum.SUCCESS


@pytest.mark.asyncio
async def should_not_open_position_if_already_open(faker: Faker, test_environment: tuple[Container, ...]) -> None:
    application_container, *_ = test_environment
    trade_now_service: TradeNowService = (
        application_container.infrastructure_container().services_container().trade_now_service()
    )

    currency = faker.random_element(MOCK_CRYPTO_CURRENCIES)
    symbol = f"{currency}/USDT:USDT"
    tracked_currency = TrackedCryptoCurrencyItem.from_currency(currency)
    existing_position = Position(
        position_id=faker.pystr(),
        symbol=symbol,
        leverage=10,
        entry_price=25000.0,
        position_type=PositionTypeEnum.LONG,
        liquidation_price=faker.pyfloat(),
        contracts=faker.pyfloat(),
        contract_size=faker.pyfloat(),
        fee=faker.pyfloat(),
        initial_margin=faker.pyfloat(),
        open_type=PositionOpenTypeEnum.ISOLATED,
    )
    market_config = SymbolMarketConfig(symbol=symbol, price_precision=2, amount_precision=3, contract_size=0.001)
    ticker = SymbolTicker(
        timestamp=int(datetime.now(UTC).timestamp() * 1000), symbol=symbol, close=100.0, mark_price=faker.pyfloat()
    )
    existing_metrics = PositionMetrics(position=existing_position, symbol_market_config=market_config, ticker=ticker)

    with (
        patch.object(
            trade_now_service._orders_analytics_service,
            "get_open_position_metrics",
            AsyncMock(return_value=[existing_metrics]),
        ),
        patch.object(
            trade_now_service._futures_exchange_service,
            "get_account_info",
            AsyncMock(return_value=AccountInfo(currency_code="USDT")),
        ),
    ):
        result = await trade_now_service.open_position(tracked_currency, PositionTypeEnum.LONG)
        assert result.result_type == OpenPositionResultTypeEnum.ALREADY_OPEN


@pytest.mark.asyncio
async def should_not_open_position_if_no_funds(faker: Faker, test_environment: tuple[Container, ...]) -> None:
    application_container, *_ = test_environment
    trade_now_service: TradeNowService = (
        application_container.infrastructure_container().services_container().trade_now_service()
    )

    currency = faker.random_element(MOCK_CRYPTO_CURRENCIES)
    symbol = f"{currency}/USDT:USDT"
    tracked_currency = TrackedCryptoCurrencyItem.from_currency(currency)
    position_hints = PositionHints(
        is_long=True,
        is_safe=faker.pybool(),
        margin=0.0,
        leverage=10,
        notional_size=faker.pyfloat(),
        liquidation_price=faker.pyfloat(),
        entry_price=faker.pyfloat(),
        break_even_price=faker.pyfloat(),
        stop_loss_price=90.0,
        move_sl_to_break_even_price=faker.pyfloat(),
        move_sl_to_first_target_profit_price=faker.pyfloat(),
        take_profit_price=110.0,
        potential_loss=faker.pyfloat(),
        potential_profit=faker.pyfloat(),
    )
    ticker = SymbolTicker(timestamp=int(datetime.now(UTC).timestamp() * 1000), symbol=symbol, close=100.0)
    candlestick_indicators = CandleStickIndicators(
        symbol=symbol,
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
        ticker=ticker,
        candlestick_indicators=candlestick_indicators,
        stop_loss_percent_value=faker.pyfloat(),
        take_profit_percent_value=faker.pyfloat(),
        long=position_hints,
        short=position_hints,
    )

    with (
        patch.object(
            trade_now_service._orders_analytics_service, "get_open_position_metrics", AsyncMock(return_value=[])
        ),
        patch.object(trade_now_service, "get_trade_now_hints", AsyncMock(return_value=trade_now_hints)),
        patch.object(
            trade_now_service._futures_exchange_service,
            "get_account_info",
            AsyncMock(return_value=AccountInfo(currency_code="USDT")),
        ),
    ):
        result = await trade_now_service.open_position(tracked_currency, PositionTypeEnum.LONG)
        assert result.result_type == OpenPositionResultTypeEnum.NO_FUNDS
