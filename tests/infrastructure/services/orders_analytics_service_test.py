import logging
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from dependency_injector.containers import Container
from faker import Faker

from crypto_futures_bot.domain.enums import CandleStickEnum, PositionOpenTypeEnum, PositionTypeEnum
from crypto_futures_bot.domain.vo import CandleStickIndicators, SignalParametrizationItem
from crypto_futures_bot.infrastructure.adapters.futures_exchange.vo.position import Position
from crypto_futures_bot.infrastructure.adapters.futures_exchange.vo.symbol_market_config import SymbolMarketConfig
from crypto_futures_bot.infrastructure.adapters.futures_exchange.vo.symbol_ticker import SymbolTicker
from crypto_futures_bot.infrastructure.services.orders_analytics_service import OrdersAnalyticsService

logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def should_get_open_position_metrics_properly(faker: Faker, test_environment: tuple[Container, ...]) -> None:
    application_container, *_ = test_environment
    orders_analytics_service: OrdersAnalyticsService = (
        application_container.infrastructure_container().services_container().orders_analytics_service()
    )

    symbol = "BTC/USDT"
    position = Position(
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
    ticker = SymbolTicker(timestamp=int(datetime.now(UTC).timestamp() * 1000), symbol=symbol, close=26000.0)
    market_config = SymbolMarketConfig(
        symbol=symbol, price_precision=2, amount_precision=3, contract_size=faker.pyfloat()
    )

    mock_get_open_positions = AsyncMock(return_value=[position])
    mock_get_symbol_tickers = AsyncMock(return_value=[ticker])
    mock_get_symbol_market_config = AsyncMock(return_value=market_config)

    with (
        patch.object(orders_analytics_service._futures_exchange_service, "get_open_positions", mock_get_open_positions),
        patch.object(orders_analytics_service._futures_exchange_service, "get_symbol_tickers", mock_get_symbol_tickers),
        patch.object(
            orders_analytics_service._futures_exchange_service,
            "get_symbol_market_config",
            mock_get_symbol_market_config,
        ),
    ):
        metrics = await orders_analytics_service.get_open_position_metrics()
        assert len(metrics) == 1
        assert metrics[0].position.position_id == position.position_id


def should_calculate_stop_loss_and_take_profit_properly(faker: Faker, test_environment: tuple[Container, ...]) -> None:
    application_container, *_ = test_environment
    orders_analytics_service: OrdersAnalyticsService = (
        application_container.infrastructure_container().services_container().orders_analytics_service()
    )

    entry_price = 100.0
    symbol = "BTC/USDT"
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
        atr=2.0,
        relative_volume=faker.pyfloat(),
    )
    signal_parametrization = SignalParametrizationItem(crypto_currency="BTC", atr_sl_mult=1.5, atr_tp_mult=3.0)
    market_config = SymbolMarketConfig(symbol=symbol, price_precision=2, amount_precision=3, contract_size=0.001)

    sl_percent = orders_analytics_service.get_stop_loss_percent_value(
        entry_price,
        last_candlestick_indicators=candlestick_indicators,
        signal_parametrization_item=signal_parametrization,
        symbol_market_config=market_config,
    )
    assert sl_percent == 3.0  # (2.0 * 1.5) / 100 * 100

    sl_price = orders_analytics_service.get_stop_loss_price(
        entry_price, stop_loss_percent_value=sl_percent, is_long=True, symbol_market_config=market_config
    )
    assert sl_price == 97.0

    tp_percent = orders_analytics_service.get_take_profit_percent_value(
        entry_price,
        last_candlestick_indicators=candlestick_indicators,
        signal_parametrization_item=signal_parametrization,
        symbol_market_config=market_config,
    )
    assert tp_percent == 6.0  # (2.0 * 3.0) / 100 * 100

    _, _, tp_price = orders_analytics_service.get_take_profit_price_levels(
        entry_price,
        is_long=True,
        last_candlestick_indicators=candlestick_indicators,
        signal_parametrization_item=signal_parametrization,
        symbol_market_config=market_config,
    )
    assert tp_price == 106.0


def should_calculate_break_even_price_properly(test_environment: tuple[Container, ...]) -> None:
    application_container, *_ = test_environment
    orders_analytics_service: OrdersAnalyticsService = (
        application_container.infrastructure_container().services_container().orders_analytics_service()
    )

    entry_price = 100.0
    symbol = "BTC/USDT"
    market_config = SymbolMarketConfig(symbol=symbol, price_precision=2, amount_precision=3, contract_size=0.001)
    taker_fee = 0.001  # 0.1%

    with patch.object(orders_analytics_service._futures_exchange_service, "get_taker_fee", return_value=taker_fee):
        # Long position
        break_even_long = orders_analytics_service.calculate_break_even_price(
            entry_price, symbol_market_config=market_config, is_long=True
        )
        assert break_even_long > entry_price

        # Short position
        break_even_short = orders_analytics_service.calculate_break_even_price(
            entry_price, symbol_market_config=market_config, is_long=False
        )
        assert break_even_short < entry_price
