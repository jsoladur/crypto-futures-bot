import logging
from typing import Any, override

import backoff
import cachebox
import ccxt.async_support as ccxt

from crypto_futures_bot.config.configuration_properties import ConfigurationProperties
from crypto_futures_bot.constants import DEFAULT_IN_MEMORY_CACHE_TTL_IN_SECONDS
from crypto_futures_bot.infrastructure.adapters.futures_exchange.base import AbstractFuturesExchangeService
from crypto_futures_bot.infrastructure.adapters.futures_exchange.types import Timeframe
from crypto_futures_bot.infrastructure.adapters.futures_exchange.vo import AccountInfo, PortfolioBalance

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
        self._client = ccxt.mexc(
            {
                "apiKey": self._configuration_properties.mexc_api_key,
                "secret": self._configuration_properties.mexc_api_secret,
                "options": {"defaultType": "swap"},
            }
        )

    @override
    async def get_account_info(self, *, client: Any | None = None) -> AccountInfo:
        return AccountInfo(currency_code=self._configuration_properties.currency_code)

    @override
    def get_portfolio_balance(self) -> PortfolioBalance:
        raise NotImplementedError()

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
    async def get_crypto_currencies(self) -> list[str]:
        futures_markets = await self._load_futures_markets()
        return list(futures_markets.keys())

    @override
    async def fetch_ohlcv(self, symbol: str, *, timeframe: Timeframe = "15m", limit: int = 251) -> list[list[Any]]:
        ohlcv = await self._client.fetch_ohlcv(symbol=symbol, timeframe=timeframe, limit=limit)
        return ohlcv

    @cachebox.cachedmethod(
        cachebox.TTLCache(0, ttl=DEFAULT_IN_MEMORY_CACHE_TTL_IN_SECONDS), key_maker=lambda _, __: "futures_markets"
    )
    async def _load_futures_markets(self) -> dict[str, dict[str, Any]]:
        account_info = await self.get_account_info()
        markets = await self._client.fetch_swap_markets()
        ret = {
            market["base"]: market
            for market in markets
            if market.get("quote") == account_info.currency_code
            and market.get("active", False)
            and market.get("swap", False)
        }
        return ret
