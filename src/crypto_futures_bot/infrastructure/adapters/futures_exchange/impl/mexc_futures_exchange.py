import logging
from typing import Any, override

import backoff
import cachebox
import ccxt.async_support as ccxt

from crypto_futures_bot.config.configuration_properties import ConfigurationProperties
from crypto_futures_bot.constants import DEFAULT_IN_MEMORY_CACHE_TTL_IN_SECONDS, STABLE_COINS
from crypto_futures_bot.infrastructure.adapters.futures_exchange.base import AbstractFuturesExchangeService
from crypto_futures_bot.infrastructure.adapters.futures_exchange.types import Timeframe
from crypto_futures_bot.infrastructure.adapters.futures_exchange.vo import PortfolioBalance

logger = logging.getLogger(__name__)


class MEXCFuturesExchangeService(AbstractFuturesExchangeService):
    def __init__(self, configuration_properties: ConfigurationProperties):
        super().__init__()
        self._configuration_properties = configuration_properties
        if (
            self._configuration_properties.mexc_api_key is None
            or self._configuration_properties.mexc_api_secret is None
        ):
            raise ValueError("MEXC API key and secret are required")

        common_config = {
            "apiKey": self._configuration_properties.mexc_api_key,
            "secret": self._configuration_properties.mexc_api_secret,
        }
        self._spot_client = ccxt.mexc({**common_config, "options": {"defaultType": "spot"}})
        self._futures_client = ccxt.mexc({**common_config, "options": {"defaultType": "swap"}})

    @override
    def get_portfolio_balance(self) -> PortfolioBalance:
        raise NotImplementedError()

    @cachebox.cachedmethod(
        cachebox.TTLCache(0, ttl=DEFAULT_IN_MEMORY_CACHE_TTL_IN_SECONDS),
        key_maker=lambda _, __: "mexc_trading_crypto_currencies",
    )
    @backoff.on_exception(
        backoff.constant,
        exception=ccxt.BaseError,
        interval=2,
        max_tries=5,
        jitter=backoff.full_jitter,
        giveup=lambda e: isinstance(e, ccxt.BadRequest) or isinstance(e, ccxt.AuthenticationError),
        on_backoff=lambda details: logger.warning(
            f"[Retry {details['tries']}] " + f"Waiting {details['wait']:.2f}s due to {str(details['exception'])}"
        ),
    )
    async def get_trading_crypto_currencies(self, *, client: ccxt.Exchange | None = None) -> list[str]:
        markets = await self._futures_client.load_markets()
        ret = [
            market["symbol"]
            for market in markets.values()
            if market.get("active", False) and str(market["quote"]).upper() not in STABLE_COINS
        ]
        return ret

    @override
    async def fetch_ohlcv(
        self, symbol: str, timeframe: Timeframe, limit: int = 251, *, client: ccxt.Exchange | None = None
    ) -> list[list[Any]]:
        raise NotImplementedError()
