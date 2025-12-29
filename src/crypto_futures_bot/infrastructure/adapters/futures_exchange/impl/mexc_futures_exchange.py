import logging
from typing import Any, override

import backoff
import ccxt.async_support as ccxt

from crypto_futures_bot.config.configuration_properties import ConfigurationProperties
from crypto_futures_bot.constants import MEXC_FUTURES_TAKER_FEES
from crypto_futures_bot.domain.enums import PositionOpenTypeEnum, PositionTypeEnum
from crypto_futures_bot.domain.types import Timeframe
from crypto_futures_bot.infrastructure.adapters.futures_exchange.base import AbstractFuturesExchangeService
from crypto_futures_bot.infrastructure.adapters.futures_exchange.vo import (
    AccountInfo,
    PortfolioBalance,
    Position,
    SymbolMarketConfig,
    SymbolTicker,
)
from crypto_futures_bot.infrastructure.adapters.futures_exchange.vo.futures_wallet import FuturesWallet

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
            "timeout": self._configuration_properties.futures_exchange_timeout,
            "enableRateLimit": True,
        }
        self._spot_client = ccxt.mexc({**commons_options, "options": {"defaultType": "spot"}})
        self._futures_client = ccxt.mexc({**commons_options, "options": {"defaultType": "swap"}})
        self._futures_markets_cache: dict[str, dict[str, Any]] | None = None

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
    async def get_account_info(self) -> AccountInfo:
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
    async def get_futures_wallet(self) -> FuturesWallet:
        account_info = await self.get_account_info()
        raw_data = await self._get_futures_wallet_fiat_currency_raw_balances(account_info)
        ret = FuturesWallet(
            currency=raw_data["currency"],
            # Total Net Worth (Cash + PnL)
            equity=round(float(raw_data.get("equity", 0.0)), ndigits=2),
            # Collateral currently locked in trades
            position_margin=round(float(raw_data.get("positionMargin", 0.0)), ndigits=2),
            # Liquidity available for new trades
            available_balance=round(float(raw_data.get("availableBalance", 0.0)), ndigits=2),
            # Components of Equity (useful for debugging/display)
            cash_balance=round(float(raw_data.get("cashBalance", 0.0)), ndigits=2),
            unrealized_pnl=round(float(raw_data.get("unrealized", 0.0)), ndigits=2),
        )
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
        return self._convert_raw_ticker_to_symbol_ticker(raw_ticker)

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
        ret = [self._convert_raw_ticker_to_symbol_ticker(raw_ticker) for raw_ticker in raw_tickers.values()]
        return ret

    def _convert_raw_ticker_to_symbol_ticker(self, raw_ticker: dict[str, Any]) -> SymbolTicker:
        return SymbolTicker(
            timestamp=raw_ticker["timestamp"],
            symbol=raw_ticker["symbol"],
            close=raw_ticker["close"],
            bid=raw_ticker["bid"],
            ask=raw_ticker["ask"],
            mark_price=raw_ticker["info"]["fairPrice"],
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
    async def get_open_positions(self) -> list[Position]:
        raw_open_positions = await self._futures_client.fetch_positions()
        raw_stop_orders = await self._futures_client.request(
            "/stoporder/open_orders", api=["contract", "private"], method="GET"
        )
        ret = []
        for raw_position in raw_open_positions:
            symbol_market_config = await self.get_symbol_market_config(
                crypto_currency=raw_position["symbol"].split("/")[0]
            )
            position_id = str(raw_position["info"]["positionId"])
            stop_order = next(
                (
                    stop_order
                    for stop_order in raw_stop_orders.get("data", [])
                    if stop_order.get("positionId") == position_id
                ),
                None,
            )
            ret.append(
                Position(
                    position_id=position_id,
                    symbol=raw_position["symbol"],
                    initial_margin=float(raw_position["initialMargin"]),
                    leverage=int(raw_position["leverage"]),
                    liquidation_price=float(raw_position["liquidationPrice"]),
                    open_type=self._map_open_type(int(raw_position["info"]["openType"])),
                    position_type=self._map_position_type(raw_position["side"]),
                    entry_price=float(raw_position["entryPrice"]),
                    contracts=float(raw_position["contracts"]),
                    contract_size=float(raw_position["contractSize"]),
                    fee=round(
                        float(raw_position["info"]["totalFee"]) + abs(float(raw_position["info"]["holdFee"])),
                        ndigits=symbol_market_config.price_precision,
                    ),
                    stop_loss_price=float(stop_order.get("stopLossPrice"))
                    if stop_order and "stopLossPrice" in stop_order
                    else None,
                    take_profit_price=float(stop_order.get("takeProfitPrice"))
                    if stop_order and "takeProfitPrice" in stop_order
                    else None,
                )
            )
        return ret

    @override
    def get_taker_fee(self) -> float:
        return MEXC_FUTURES_TAKER_FEES

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
        if not self._futures_markets_cache:
            account_info = await self.get_account_info()
            markets = await self._futures_client.fetch_swap_markets()
            self._futures_markets_cache = {
                market["base"]: market
                for market in markets
                if market.get("quote") == account_info.currency_code
                and market.get("active", False)
                and market.get("swap", False)
            }
        return self._futures_markets_cache

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

    async def _get_futures_total_balance(self, account_info: AccountInfo) -> float:
        ret = 0.0
        account_currency_balances = await self._get_futures_wallet_fiat_currency_raw_balances(account_info)
        if account_currency_balances is not None:
            ret += float(account_currency_balances.get("equity", 0.0))
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
    async def _get_futures_wallet_fiat_currency_raw_balances(self, account_info: AccountInfo) -> dict[str, Any] | None:
        futures_balances = await self._futures_client.fetch_balance()
        account_currency_balance = next(
            (
                balance
                for balance in futures_balances["info"]["data"]
                if balance["currency"].upper() == account_info.currency_code.upper()
            ),
            None,
        )
        return account_currency_balance

    def _convert_raw_ticker_to_symbol_ticker(self, raw_ticker: dict[str, Any]) -> SymbolTicker:
        return SymbolTicker(
            timestamp=raw_ticker["timestamp"],
            symbol=raw_ticker["symbol"],
            close=raw_ticker["close"],
            bid=raw_ticker["bid"],
            ask=raw_ticker["ask"],
            mark_price=float(raw_ticker["info"]["fairPrice"]),
        )

    def _map_position_type(self, side: str) -> PositionTypeEnum:
        """
        Map the raw 'side' field from the exchange to PositionTypeEnum using match/case.

        Args:
            side: str, e.g., "long" or "short"

        Returns:
            PositionTypeEnum.LONG or PositionTypeEnum.SHORT
        """
        match side.lower():
            case "long":
                return PositionTypeEnum.LONG
            case "short":
                return PositionTypeEnum.SHORT
            case _:
                raise ValueError(f"Unknown position side: {side}")

    def _map_open_type(self, open_type: int) -> PositionOpenTypeEnum:
        """
        Map the raw 'marginMode' from the exchange to PositionOpenTypeEnum using match/case.

        Args:
            open_type: int, e.g., 1 (isolated) or 2 (cross)

        Returns:
            PositionOpenTypeEnum.CROSS or PositionOpenTypeEnum.ISOLATED
        """
        match open_type:
            case 1:
                return PositionOpenTypeEnum.ISOLATED
            case 2:
                return PositionOpenTypeEnum.CROSS
            case _:
                raise ValueError(f"Unknown open type: {open_type}")
