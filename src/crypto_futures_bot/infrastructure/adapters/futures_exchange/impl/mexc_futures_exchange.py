import logging
from typing import Any, override

import backoff
import cachebox
import ccxt.async_support as ccxt

from crypto_futures_bot.config.configuration_properties import ConfigurationProperties
from crypto_futures_bot.constants import DEFAULT_IN_MEMORY_CACHE_TTL_IN_SECONDS, MEXC_FUTURES_TAKER_FEES
from crypto_futures_bot.domain.types import Timeframe
from crypto_futures_bot.infrastructure.adapters.futures_exchange.base import AbstractFuturesExchangeService
from crypto_futures_bot.infrastructure.adapters.futures_exchange.vo import (
    AccountInfo,
    PortfolioBalance,
    SymbolMarketConfig,
    SymbolTicker,
)

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
        # XXX:For more info about: https://docs.ccxt.com/exchanges/mexc
        commons_options = {
            "apiKey": self._configuration_properties.mexc_api_key,
            "secret": self._configuration_properties.mexc_api_secret,
            # switch it to False if you don't want the HTTP log
            "verbose": self._configuration_properties.futures_exchange_debug_mode,
        }
        self._spot_client = ccxt.mexc({**commons_options, "options": {"defaultType": "spot"}})
        self._futures_client = ccxt.mexc({**commons_options, "options": {"defaultType": "swap"}})

    @override
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
    async def post_init(self) -> None:
        await self._spot_client.load_markets()
        await self._futures_client.load_markets()

    @override
    async def get_account_info(self, *, client: Any | None = None) -> AccountInfo:
        return AccountInfo(currency_code=self._configuration_properties.currency_code)

    @override
    async def get_portfolio_balance(self) -> PortfolioBalance:
        account_info = await self.get_account_info()
        spot_balance = await self._get_spot_total_balance(account_info)
        swap_balance = await self._get_futures_total_balance(account_info)
        return PortfolioBalance(
            spot_balance=round(spot_balance, ndigits=2),
            futures_balance=round(swap_balance, ndigits=2),
            currency_code=account_info.currency_code,
        )

    @override
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
        return sorted(list(futures_markets.keys()))

    @override
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
    async def get_symbol_ticker(self, symbol: str) -> SymbolTicker:
        raw_ticker = await self._futures_client.fetch_ticker(symbol)
        return SymbolTicker(
            timestamp=raw_ticker["timestamp"],
            symbol=symbol,
            close=raw_ticker["close"],
            bid=raw_ticker["bid"],
            ask=raw_ticker["ask"],
        )

    @override
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
    async def get_symbol_tickers(self, *, symbols: list[str] | None = None) -> list[SymbolTicker]:
        raw_tickers = await self._futures_client.fetch_tickers(symbols=symbols)
        ret = [
            SymbolTicker(
                timestamp=raw_ticker["timestamp"],
                symbol=raw_ticker["symbol"],
                close=raw_ticker["close"],
                bid=raw_ticker["bid"],
                ask=raw_ticker["ask"],
            )
            for raw_ticker in raw_tickers.values()
        ]
        return ret

    @override
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
    async def fetch_ohlcv(
        self, symbol: str, *, timeframe: Timeframe = "15m", limit: int = 251, since: int | None = None
    ) -> list[list[Any]]:
        ohlcv = await self._futures_client.fetch_ohlcv(symbol=symbol, timeframe=timeframe, limit=limit, since=since)
        return ohlcv

    @override
    async def get_symbol_market_config(self, crypto_currency: str) -> SymbolMarketConfig:
        futures_markets = await self._load_futures_markets()
        raw_future_market = futures_markets.get(crypto_currency)
        if not raw_future_market:
            raise ValueError(f"Future market not found for {crypto_currency}")
        return SymbolMarketConfig(
            symbol=raw_future_market["symbol"],
            price_precision=int(raw_future_market["info"]["priceScale"]),
            amount_precision=int(raw_future_market["info"]["amountScale"]),
        )

    @override
    def get_taker_fee(self) -> float:
        return MEXC_FUTURES_TAKER_FEES

    @cachebox.cachedmethod(
        cachebox.TTLCache(0, ttl=DEFAULT_IN_MEMORY_CACHE_TTL_IN_SECONDS), key_maker=lambda _, __: "futures_markets"
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
    async def _load_futures_markets(self) -> dict[str, dict[str, Any]]:
        account_info = await self.get_account_info()
        markets = await self._futures_client.fetch_swap_markets()
        ret = {
            market["base"]: market
            for market in markets
            if market.get("quote") == account_info.currency_code
            and market.get("active", False)
            and market.get("swap", False)
        }
        return ret

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
    async def _get_spot_total_balance(self, account_info: AccountInfo) -> float:
        spot_balances = await self._spot_client.fetch_balance()
        spot_prices = await self._get_spot_prices()
        spot_totals = spot_balances.get("total", {})
        ret = spot_totals.pop(account_info.currency_code.upper(), 0.0)
        for currency, amount in spot_totals.items():
            if amount > 0:
                ret += amount * spot_prices[f"{currency}/{account_info.currency_code}"]
        return ret

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
    async def _get_futures_total_balance(self, account_info: AccountInfo) -> float:
        futures_balances = await self._futures_client.fetch_balance()
        account_currency_balance = next(
            (
                balance
                for balance in futures_balances["info"]["data"]
                if balance["currency"].upper() == account_info.currency_code.upper()
            ),
            None,
        )
        ret = 0.0
        if account_currency_balance is not None:
            ret += float(account_currency_balance.get("equity", 0.0))
        return ret

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
    async def _get_spot_prices(self) -> dict[str, float]:
        spot_tickers = await self._spot_client.fetch_tickers()
        return {symbol: ticker["last"] for symbol, ticker in spot_tickers.items()}
