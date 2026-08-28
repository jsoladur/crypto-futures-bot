import asyncio
import logging
import math
from dataclasses import replace
from decimal import Decimal
from typing import Any, override

import backoff
import ccxt.async_support as ccxt

from crypto_futures_bot.config.configuration_properties import ConfigurationProperties
from crypto_futures_bot.constants import (
    BLOFIN_FUTURES_TAKER_FEES,
    BLOFIN_MARKET_ORDER_SAFETY_FACTOR,
    BLOFIN_MARKET_ORDER_SLIPPAGE_BUFFER,
)
from crypto_futures_bot.domain.enums import PositionOpenTypeEnum, PositionTypeEnum
from crypto_futures_bot.domain.types import Timeframe
from crypto_futures_bot.infrastructure.adapters.futures_exchange.base import AbstractFuturesExchangeService
from crypto_futures_bot.infrastructure.adapters.futures_exchange.vo import (
    AccountInfo,
    CreateMarketPositionOrder,
    FuturesWallet,
    PortfolioBalance,
    Position,
    SymbolMarketConfig,
    SymbolTicker,
)

logger = logging.getLogger(__name__)


class BloFinFuturesExchangeService(AbstractFuturesExchangeService):
    def __init__(self, configuration_properties: ConfigurationProperties) -> None:
        super().__init__()
        self._configuration_properties = configuration_properties
        if (
            self._configuration_properties.blofin_api_key is None
            or self._configuration_properties.blofin_api_secret is None
            or self._configuration_properties.blofin_api_passphrase is None
        ):
            raise ValueError("BloFin API key, secret and passphrase are required")
        # XXX: For more info about: https://docs.ccxt.com/exchanges/blofin
        commons_options = {
            "apiKey": self._configuration_properties.blofin_api_key,
            "secret": self._configuration_properties.blofin_api_secret,
            "password": self._configuration_properties.blofin_api_passphrase,
            "verbose": self._configuration_properties.futures_exchange_debug_mode,
            "timeout": self._configuration_properties.futures_exchange_timeout,
            "enableRateLimit": True,
        }
        self._spot_client = ccxt.blofin({**commons_options, "options": {"defaultType": "spot"}})
        self._futures_client = ccxt.blofin({**commons_options, "options": {"defaultType": "swap"}})
        self._futures_markets_cache: dict[str, dict[str, Any]] | None = None
        self._order_lock = asyncio.Lock()

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
        funding_balance = await self._get_funding_total_balance(account_info)
        swap_balance = await self._get_futures_total_balance(account_info)
        return PortfolioBalance(
            spot_balance=self._floor_round(funding_balance, ndigits=2),
            futures_balance=self._floor_round(swap_balance, ndigits=2),
            currency_code=account_info.currency_code,
        )

    @override
    async def get_futures_wallet(self) -> FuturesWallet:
        account_info = await self.get_account_info()
        raw_balance = await self._get_futures_wallet_raw_balance(account_info)
        return FuturesWallet(
            currency=account_info.currency_code,
            equity=self._floor_round(float(raw_balance.get("equity", 0.0)), ndigits=2),
            position_margin=self._floor_round(float(raw_balance.get("positionMargin", 0.0)), ndigits=2),
            available_balance=self._floor_round(float(raw_balance.get("availableBalance", 0.0)), ndigits=2),
            cash_balance=self._floor_round(float(raw_balance.get("cashBalance", 0.0)), ndigits=2),
            unrealized_pnl=self._floor_round(float(raw_balance.get("unrealizedPnl", 0.0)), ndigits=2),
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
    async def get_symbol_ticker(self, symbol: str) -> SymbolTicker:
        raw_ticker = await self._futures_client.fetch_ticker(symbol)
        mark_price = self._extract_mark_price(raw_ticker, expected_symbol=symbol)
        if mark_price is None:
            mark_price = await self._fetch_validated_mark_price(symbol)
        return self._convert_raw_ticker_to_symbol_ticker(raw_ticker, mark_price=mark_price)

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
            self._convert_raw_ticker_to_symbol_ticker(
                raw_ticker, mark_price=self._extract_mark_price(raw_ticker, expected_symbol=raw_ticker.get("symbol"))
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
        info = raw_future_market.get("info", {})
        ret = SymbolMarketConfig(
            symbol=raw_future_market["symbol"],
            price_precision=self._step_size_to_digits(info.get("tickSize")),
            amount_precision=self._step_size_to_digits(info.get("lotSize")),
            contract_size=float(raw_future_market.get("contractSize", 1.0)),
            max_leverage=int(info.get("maxLeverage", 1)),
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
    async def get_open_positions(self) -> list[Position]:
        raw_stop_orders = await self._get_raw_stop_orders()
        raw_open_positions = await self._futures_client.fetch_positions()
        ret = [
            self._map_raw_position(raw_position, raw_stop_orders=raw_stop_orders) for raw_position in raw_open_positions
        ]
        return ret

    @override
    async def get_position_by_id(self, position_id: str) -> Position:
        raise NotImplementedError("Operation not supported in BloFin exchange")

    @override
    async def create_market_position_order(self, position: CreateMarketPositionOrder) -> Position:
        symbol = position.symbol
        symbol_ticker = await self.get_symbol_ticker(symbol=symbol)
        crypto_currency = symbol.split("/")[0]
        symbol_market_config = await self.get_symbol_market_config(crypto_currency=crypto_currency)

        taker_fee_rate = self.get_taker_fee()

        if position.position_type == PositionTypeEnum.LONG:
            execution_price = symbol_ticker.ask if symbol_ticker.ask else symbol_ticker.mark_price
            bankruptcy_factor = 1 - (1 / position.leverage)
        else:
            execution_price = symbol_ticker.bid if symbol_ticker.bid else symbol_ticker.mark_price
            bankruptcy_factor = 1 + (1 / position.leverage)

        estimated_closing_fee_rate = taker_fee_rate * bankruptcy_factor

        effective_margin_rate = (1 + BLOFIN_MARKET_ORDER_SLIPPAGE_BUFFER) * (
            (1 / position.leverage) + taker_fee_rate + estimated_closing_fee_rate
        )

        max_affordable_nominal = self._floor_round(position.initial_margin / effective_margin_rate, ndigits=4)

        final_nominal = min(position.notional_size, max_affordable_nominal)

        # BloFin `size` is contracts; CCXT forwards amount as-is (does not convert from base).
        raw_contracts = (
            final_nominal / execution_price / symbol_market_config.contract_size
        ) * BLOFIN_MARKET_ORDER_SAFETY_FACTOR
        amount = self._floor_round(raw_contracts, ndigits=symbol_market_config.amount_precision)
        if amount <= 0:
            raise ValueError(
                f"Calculated BloFin order size is 0 for {symbol} "
                f"(notional={final_nominal}, price={execution_price}, "
                f"contract_size={symbol_market_config.contract_size})"
            )

        await self._place_market_order(position, amount)
        opened_position = await self._wait_for_position_to_open(position=position)

        return replace(
            opened_position, stop_loss_price=position.stop_loss_price, take_profit_price=position.take_profit_price
        )

    @override
    def get_taker_fee(self) -> float:
        return BLOFIN_FUTURES_TAKER_FEES

    async def _get_raw_stop_orders(self) -> list[dict[str, Any]]:
        """Fetches all pending TP/SL orders across futures markets."""
        return await self._futures_client.fetch_open_orders(params={"tpsl": True})

    async def _place_market_order(self, position: CreateMarketPositionOrder, amount: float | int) -> dict[str, Any]:
        async with self._order_lock:
            order_side = "buy" if position.position_type == PositionTypeEnum.LONG else "sell"
            margin_mode = str(position.open_type.value).lower()

            await self._futures_client.set_leverage(
                leverage=position.leverage,
                symbol=position.symbol,
                params={"marginMode": margin_mode, "positionSide": "net"},
            )

            params: dict[str, Any] = {"marginMode": margin_mode, "positionSide": "net"}

            if position.stop_loss_price is not None:
                params["stopLoss"] = {"triggerPrice": str(position.stop_loss_price), "price": "-1"}

            if position.take_profit_price is not None:
                params["takeProfit"] = {"triggerPrice": str(position.take_profit_price), "price": "-1"}

            return await self._futures_client.create_order(
                symbol=position.symbol, type="market", side=order_side, amount=amount, params=params
            )

    async def _wait_for_position_to_open(self, *, position: CreateMarketPositionOrder) -> Position:
        max_attempts = 15
        for attempt in range(1, max_attempts + 1):
            open_positions = await self.get_open_positions()
            opened_position = next(
                (
                    pos
                    for pos in open_positions
                    if pos.symbol == position.symbol and pos.position_type == position.position_type
                ),
                None,
            )
            if opened_position:
                return opened_position
            logger.info(
                f"Waiting for {position.symbol} {position.position_type.value} "
                f"position to open (attempt {attempt}/{max_attempts})"
            )
            await asyncio.sleep(delay=2.0)
        raise ValueError(f"Created position not found for symbol: {position.symbol}")

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
            markets = list(self._futures_client.markets.values())
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
    async def _get_funding_total_balance(self, account_info: AccountInfo) -> float:
        funding_balances = await self._spot_client.fetch_balance(params={"accountType": "funding"})
        spot_prices = await self._get_spot_prices()
        funding_totals = funding_balances.get("total", {})
        ret = funding_totals.pop(account_info.currency_code.upper(), 0.0)
        for currency, amount in funding_totals.items():
            if amount > 0:
                price = spot_prices.get(f"{currency}/{account_info.currency_code}", 0.0)
                if price:
                    ret += amount * price
        return ret

    async def _get_futures_total_balance(self, account_info: AccountInfo) -> float:
        raw_balance = await self._get_futures_wallet_raw_balance(account_info)
        return float(raw_balance.get("equity", 0.0))

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
    async def _get_futures_wallet_raw_balance(self, account_info: AccountInfo) -> dict[str, Any]:
        futures_balances = await self._futures_client.fetch_balance()
        currency = account_info.currency_code.upper()
        total = float(futures_balances.get("total", {}).get(currency, 0.0))
        free = float(futures_balances.get("free", {}).get(currency, 0.0))
        used = float(futures_balances.get("used", {}).get(currency, 0.0))
        info = futures_balances.get("info", {})
        details = info.get("data", {}).get("details", []) if isinstance(info, dict) else []
        currency_detail = next((detail for detail in details if detail.get("currency", "").upper() == currency), {})
        unrealized_pl = float(currency_detail.get("isolatedUnrealizedPnl") or 0.0)
        return {
            "equity": total,
            "availableBalance": free,
            "positionMargin": used,
            "cashBalance": total - unrealized_pl,
            "unrealizedPnl": unrealized_pl,
        }

    async def _fetch_validated_mark_price(self, symbol: str) -> float | None:
        # CCXT BloFin sends `symbol` but the API filters on `instId`. Without instId the
        # endpoint returns every mark price and CCXT takes data[0] (usually BTC).
        inst_id = self._to_blofin_inst_id(symbol)
        mark_ticker = await self._futures_client.fetch_mark_price(symbol, params={"instId": inst_id})
        return self._extract_mark_price(mark_ticker, expected_symbol=symbol)

    def _extract_mark_price(self, raw_ticker: dict[str, Any], *, expected_symbol: str | None) -> float | None:
        if expected_symbol is None:
            return None
        info = raw_ticker.get("info") or {}
        inst_id = info.get("instId")
        ticker_symbol = raw_ticker.get("symbol")
        expected_inst_id = self._to_blofin_inst_id(expected_symbol)
        if inst_id is not None and inst_id != expected_inst_id:
            return None
        if inst_id is None and ticker_symbol not in (None, expected_symbol):
            return None
        for candidate in (raw_ticker.get("markPrice"), info.get("markPrice")):
            if candidate not in (None, ""):
                return float(candidate)
        return None

    def _to_blofin_inst_id(self, symbol: str) -> str:
        return symbol.split(":")[0].replace("/", "-")

    def _convert_raw_ticker_to_symbol_ticker(
        self, raw_ticker: dict[str, Any], *, mark_price: float | None = None
    ) -> SymbolTicker:
        resolved_mark_price = next(
            (
                value
                for value in (mark_price, raw_ticker.get("markPrice"), raw_ticker.get("last"), raw_ticker.get("close"))
                if value not in (None, "")
            ),
            None,
        )
        return SymbolTicker(
            timestamp=raw_ticker["timestamp"],
            symbol=raw_ticker["symbol"],
            close=raw_ticker["close"],
            bid=raw_ticker["bid"],
            ask=raw_ticker["ask"],
            mark_price=float(resolved_mark_price) if resolved_mark_price is not None else None,
        )

    def _map_raw_position(self, raw_position: dict[str, Any], *, raw_stop_orders: list[dict[str, Any]]) -> Position:
        info = raw_position.get("info", {})

        ccxt_symbol = raw_position.get("symbol", "UNKNOWN")
        margin_mode = raw_position.get("marginMode", "cross").lower()
        hold_side = raw_position.get("side") or info.get("positionSide", "UNKNOWN")
        pos_side_lower = hold_side.lower()
        margin_coin = self._configuration_properties.currency_code.upper()

        position_id = (
            info.get("positionId") or f"{info.get('instId', ccxt_symbol)}-{margin_coin}-{pos_side_lower}-{margin_mode}"
        )

        pos_position_side = info.get("positionSide", "").lower()

        def _matches_tpsl(order: dict[str, Any]) -> bool:
            order_info = order.get("info", {})
            order_symbol = order.get("symbol", "")
            order_position_side = order_info.get("positionSide", "").lower()
            return order_symbol == ccxt_symbol and (
                order_position_side == pos_position_side or order_position_side == pos_side_lower
            )

        tp_order = next(
            (
                order
                for order in raw_stop_orders
                if _matches_tpsl(order) and order.get("info", {}).get("tpTriggerPrice") is not None
            ),
            None,
        )

        sl_order = next(
            (
                order
                for order in raw_stop_orders
                if _matches_tpsl(order) and order.get("info", {}).get("slTriggerPrice") is not None
            ),
            None,
        )

        tp_trigger = tp_order.get("takeProfitTriggerPrice") if tp_order else None
        sl_trigger = sl_order.get("stopLossTriggerPrice") if sl_order else None

        if tp_trigger is None and tp_order is not None:
            tp_trigger_str = tp_order.get("info", {}).get("tpTriggerPrice")
            tp_trigger = float(tp_trigger_str) if tp_trigger_str is not None else None

        if sl_trigger is None and sl_order is not None:
            sl_trigger_str = sl_order.get("info", {}).get("slTriggerPrice")
            sl_trigger = float(sl_trigger_str) if sl_trigger_str is not None else None

        return Position(
            position_id=position_id,
            symbol=ccxt_symbol,
            initial_margin=self._resolve_initial_margin(raw_position),
            leverage=int(raw_position.get("leverage") or 1),
            liquidation_price=float(raw_position.get("liquidationPrice") or 0.0),
            open_type=self._map_margin_mode(margin_mode),
            position_type=self._map_position_type(hold_side),
            entry_price=float(raw_position.get("entryPrice") or 0.0),
            contracts=float(raw_position.get("contracts") or 0.0),
            contract_size=float(raw_position.get("contractSize") or 1.0),
            fee=0.0,
            stop_loss_price=sl_trigger,
            take_profit_price=tp_trigger,
        )

    def _resolve_initial_margin(self, raw_position: dict[str, Any]) -> float:
        info = raw_position.get("info", {})
        for candidate in (
            raw_position.get("initialMargin"),
            raw_position.get("collateral"),
            info.get("margin"),
            info.get("initialMargin"),
        ):
            if candidate not in (None, ""):
                value = float(candidate)
                if value > 0:
                    return value
        leverage = float(raw_position.get("leverage") or 0.0)
        contracts = float(raw_position.get("contracts") or 0.0)
        contract_size = float(raw_position.get("contractSize") or 1.0)
        entry_price = float(raw_position.get("entryPrice") or 0.0)
        notional = contracts * contract_size * entry_price
        if leverage > 0 and notional > 0:
            return notional / leverage
        return 0.0

    def _map_position_type(self, side: str) -> PositionTypeEnum:
        match side.lower():
            case "long":
                return PositionTypeEnum.LONG
            case "short":
                return PositionTypeEnum.SHORT
            case _:
                raise ValueError(f"Unknown position side: {side}")

    def _map_margin_mode(self, margin_mode: str) -> PositionOpenTypeEnum:
        match margin_mode.lower():
            case "isolated":
                return PositionOpenTypeEnum.ISOLATED
            case "cross":
                return PositionOpenTypeEnum.CROSS
            case _:
                raise ValueError(f"Unknown margin mode: {margin_mode}")

    def _floor_round(self, value: float, *, ndigits: int) -> float:
        factor = 10**ndigits
        return math.floor(value * factor) / factor

    def _step_size_to_digits(self, step_size: float | int | str | None) -> int:
        if step_size is None:
            return 0
        step_dec = Decimal(str(step_size)).normalize()
        exponent = step_dec.as_tuple().exponent
        return abs(int(exponent))
