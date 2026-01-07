import logging
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pandas as pd
import pytest
from dependency_injector.containers import Container
from faker import Faker

from crypto_futures_bot.infrastructure.adapters.futures_exchange.vo.account_info import AccountInfo
from crypto_futures_bot.infrastructure.adapters.futures_exchange.vo.symbol_ticker import SymbolTicker
from crypto_futures_bot.infrastructure.services.crypto_technical_analysis_service import CryptoTechnicalAnalysisService
from crypto_futures_bot.infrastructure.services.tracked_crypto_currency_service import TrackedCryptoCurrencyService
from tests.helpers.constants import MOCK_CRYPTO_CURRENCIES

logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def should_get_tracked_crypto_currency_prices_properly(
    faker: Faker, test_environment: tuple[Container, ...]
) -> None:
    application_container, *_ = test_environment
    crypto_technical_analysis_service: CryptoTechnicalAnalysisService = (
        application_container.infrastructure_container().services_container().crypto_technical_analysis_service()
    )
    tracked_crypto_currency_service: TrackedCryptoCurrencyService = (
        application_container.infrastructure_container().services_container().tracked_crypto_currency_service()
    )

    currency = faker.random_element(MOCK_CRYPTO_CURRENCIES)
    await tracked_crypto_currency_service.add(currency)

    account_info = AccountInfo(currency_code="USDT")
    symbol_ticker = SymbolTicker(
        timestamp=int(datetime.now(UTC).timestamp() * 1000), symbol=f"{currency}/USDT:USDT", close=faker.pyfloat()
    )
    mock_get_account_info = AsyncMock(return_value=account_info)
    mock_get_symbol_tickers = AsyncMock(return_value=[symbol_ticker])

    with (
        patch.object(
            crypto_technical_analysis_service._futures_exchange_service, "get_account_info", mock_get_account_info
        ),
        patch.object(
            crypto_technical_analysis_service._futures_exchange_service, "get_symbol_tickers", mock_get_symbol_tickers
        ),
    ):
        tickers = await crypto_technical_analysis_service.get_tracked_crypto_currency_prices()
        assert len(tickers) == 1
        assert tickers[0].base_asset == currency

    await tracked_crypto_currency_service.remove(currency)


@pytest.mark.asyncio
async def should_get_technical_analysis_properly(faker: Faker, test_environment: tuple[Container, ...]) -> None:
    application_container, *_ = test_environment
    crypto_technical_analysis_service: CryptoTechnicalAnalysisService = (
        application_container.infrastructure_container().services_container().crypto_technical_analysis_service()
    )

    # Sample OHLCV data for 100 periods
    ohlcv_data = [
        [
            1672531200000 + i * 900000,  # timestamp (15m intervals)
            faker.pyfloat(min_value=100, max_value=200),  # Open
            faker.pyfloat(min_value=100, max_value=200),  # High
            faker.pyfloat(min_value=100, max_value=200),  # Low
            faker.pyfloat(min_value=100, max_value=200),  # Close
            faker.pyfloat(min_value=1000, max_value=5000),  # Volume
        ]
        for i in range(100)
    ]
    mock_fetch_ohlcv = AsyncMock(return_value=ohlcv_data)

    with patch.object(crypto_technical_analysis_service._futures_exchange_service, "fetch_ohlcv", mock_fetch_ohlcv):
        symbol = "BTC/USDT"
        df = await crypto_technical_analysis_service.get_technical_analysis(symbol)
        assert isinstance(df, pd.DataFrame)
        assert not df.empty
        expected_columns = [
            "Open",
            "High",
            "Low",
            "Close",
            "Volume",
            "ema50",
            "macd_line",
            "macd_signal",
            "macd_hist",
            "stoch_rsi",
            "stoch_rsi_k",
            "stoch_rsi_d",
            "rsi",
            "atr",
            "volume_sma",
            "relative_volume",
        ]
        for col in expected_columns:
            assert col in df.columns


@pytest.mark.asyncio
async def should_get_candlestick_indicators_properly(faker: Faker, test_environment: tuple[Container, ...]) -> None:
    application_container, *_ = test_environment
    crypto_technical_analysis_service: CryptoTechnicalAnalysisService = (
        application_container.infrastructure_container().services_container().crypto_technical_analysis_service()
    )
    # Sample OHLCV data for 100 periods
    ohlcv_data = [
        [
            1672531200000 + i * 900000,  # timestamp (15m intervals)
            faker.pyfloat(min_value=100, max_value=200),  # Open
            faker.pyfloat(min_value=100, max_value=200),  # High
            faker.pyfloat(min_value=100, max_value=200),  # Low
            faker.pyfloat(min_value=100, max_value=200),  # Close
            faker.pyfloat(min_value=1000, max_value=5000),  # Volume
        ]
        for i in range(100)
    ]
    mock_fetch_ohlcv = AsyncMock(return_value=ohlcv_data)

    with patch.object(crypto_technical_analysis_service._futures_exchange_service, "fetch_ohlcv", mock_fetch_ohlcv):
        symbol = "BTC/USDT"
        indicators = await crypto_technical_analysis_service.get_candlestick_indicators(symbol)
        assert indicators is not None
        assert indicators.symbol == symbol
