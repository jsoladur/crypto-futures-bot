import asyncio
import logging
import math
from dataclasses import replace
from typing import Any, override

import backoff
import ccxt.async_support as ccxt

from crypto_futures_bot.config.configuration_properties import ConfigurationProperties
from crypto_futures_bot.constants import (
    BITGET_FUTURES_TAKER_FEES,
    BITGET_MARKET_ORDER_SAFETY_FACTOR,
    BITGET_MARKET_ORDER_SLIPPAGE_BUFFER,
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


class BitgetFuturesExchangeService(AbstractFuturesExchangeService):
    def __init__(self, configuration_properties: ConfigurationProperties) -> None:
        super().__init__()
        self._configuration_properties = configuration_properties
        if (
            self._configuration_properties.bitget_api_key is None
            or self._configuration_properties.bitget_api_secret is None
            or self._configuration_properties.bitget_api_passphrase is None
        ):
            raise ValueError("Bitget API key, secret and passphrase are required")
        # XXX: For more info about: https://docs.ccxt.com/exchanges/bitget
        commons_options = {
            "apiKey": self._configuration_properties.bitget_api_key,
            "secret": self._configuration_properties.bitget_api_secret,
            "password": self._configuration_properties.bitget_api_passphrase,
            "verbose": self._configuration_properties.futures_exchange_debug_mode,
            "timeout": self._configuration_properties.futures_exchange_timeout,
            "enableRateLimit": True,
        }
        self._spot_client = ccxt.bitget({**commons_options, "options": {"defaultType": "spot"}})
        self._futures_client = ccxt.bitget({**commons_options, "options": {"defaultType": "swap"}})
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
        spot_balance = await self._get_spot_total_balance(account_info)
        swap_balance = await self._get_futures_total_balance(account_info)
        return PortfolioBalance(
            spot_balance=self._floor_round(spot_balance, ndigits=2),
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
        # Bitget fetch_ticker info object natively includes 'markPrice'
        mark_price = raw_ticker.get("info", {}).get("markPrice")
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
                raw_ticker, mark_price=raw_ticker.get("info", {}).get("markPrice")
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
        # Bitget's unified precision returns step sizes (e.g. 0.0001), not digit counts.
        # Use raw info fields: pricePlace/volumePlace are already integer digit counts.
        info = raw_future_market.get("info", {})
        ret = SymbolMarketConfig(
            symbol=raw_future_market["symbol"],
            price_precision=int(info.get("pricePlace", 0)),
            amount_precision=int(info.get("volumePlace", 0)),
            contract_size=float(raw_future_market.get("contractSize", 1.0)),
            max_leverage=int(info.get("maxLever", 1)),
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
        raise NotImplementedError("Operation not supported in Bitget exchange")

    @override
    async def create_market_position_order(self, position: CreateMarketPositionOrder) -> Position:
        symbol = position.symbol
        symbol_ticker = await self.get_symbol_ticker(symbol=symbol)
        crypto_currency = symbol.split("/")[0]
        symbol_market_config = await self.get_symbol_market_config(crypto_currency=crypto_currency)

        # 1. Fetch taker fee rate
        # Fetch taker fee rate
        taker_fee_rate = self.get_taker_fee()

        # 3. Use Ask/Bid instead of Mark Price for accurate execution cost
        if position.position_type == PositionTypeEnum.LONG:
            execution_price = symbol_ticker.ask if symbol_ticker.ask else symbol_ticker.mark_price
            # Long Bankruptcy Price is lower than entry
            bankruptcy_factor = 1 - (1 / position.leverage)
        else:
            execution_price = symbol_ticker.bid if symbol_ticker.bid else symbol_ticker.mark_price
            # Short Bankruptcy Price is higher than entry
            bankruptcy_factor = 1 + (1 / position.leverage)

        # 4. Calculate Effective Margin Rate based on Bitget's actual risk engine
        estimated_closing_fee_rate = taker_fee_rate * bankruptcy_factor

        effective_margin_rate = (1 + BITGET_MARKET_ORDER_SLIPPAGE_BUFFER) * (
            (1 / position.leverage) + taker_fee_rate + estimated_closing_fee_rate
        )

        max_affordable_nominal = self._floor_round(position.initial_margin / effective_margin_rate, ndigits=4)

        # Pick the smaller value (Safety factor optional here, but good for dust protection)
        final_nominal = min(position.notional_size, max_affordable_nominal)

        # 5. Calculate the raw amount in Base Currency (expected by CCXT)
        raw_amount = (final_nominal / execution_price) * BITGET_MARKET_ORDER_SAFETY_FACTOR

        # 6. Format the amount safely using the exchange's precision
        amount = (
            int(raw_amount)
            if symbol_market_config.contract_size >= 1.0
            else self._floor_round(raw_amount, ndigits=symbol_market_config.amount_precision)
        )

        order = await self._place_market_order(position, amount)
        await self._wait_for_order_to_close(order["id"], position=position)
        opened_position = await self._get_opened_position(position=position)

        # 7. Inject TP/SL
        return replace(
            opened_position, stop_loss_price=position.stop_loss_price, take_profit_price=position.take_profit_price
        )

    @override
    def get_taker_fee(self) -> float:
        return BITGET_FUTURES_TAKER_FEES

    # --- Private helper methods ---

    async def _get_raw_stop_orders(self) -> list[dict[str, Any]]:
        """
        Fetches all pending stop/plan orders across all USDT-M symbols.
        """
        account_info = await self.get_account_info()
        product_type = f"{account_info.currency_code.upper()}-FUTURES"
        ret = await self._futures_client.fetch_open_orders(
            params={
                "stop": True,
                "planType": "profit_loss",  # Filters for TP/SL
                "productType": product_type,  # MANDATORY when symbol is None
            }
        )
        return ret

    async def _place_market_order(self, position: CreateMarketPositionOrder, amount: float | int) -> dict[str, Any]:
        account_info = await self.get_account_info()
        async with self._order_lock:
            # 1. Determine sides and modes
            order_side = "buy" if position.position_type == PositionTypeEnum.LONG else "sell"
            hold_side = "long" if position.position_type == PositionTypeEnum.LONG else "short"
            margin_mode = str(position.open_type.value).lower()
            # CCXT wrapper for Bitget's /api/v2/mix/account/set-margin-mode
            await self._futures_client.set_margin_mode(
                marginMode=margin_mode,
                symbol=position.symbol,
                params={"marginCoin": account_info.currency_code.upper()},
            )
            # --- Explicitly Set Leverage ---
            leverage_params = {
                "marginCoin": account_info.currency_code.upper(),
                "marginMode": margin_mode,
                "holdSide": hold_side,
            }
            await self._futures_client.set_leverage(
                leverage=position.leverage, symbol=position.symbol, params=leverage_params
            )

            # 2. Base parameters for the order
            product_type = f"{account_info.currency_code.upper()}-FUTURES"
            params: dict[str, Any] = {
                "marginCoin": account_info.currency_code.upper(),
                "marginMode": margin_mode,
                "tradeSide": "open",
                "productType": product_type,
            }

            # 3. Attach Order-Level TP/SL
            if position.stop_loss_price is not None:
                params["presetStopLossPrice"] = str(position.stop_loss_price)
                params["presetStopLossExecutePrice"] = ""
                params["presetStopLossType"] = "mark_price"

            if position.take_profit_price is not None:
                params["presetStopSurplusPrice"] = str(position.take_profit_price)
                params["presetStopSurplusExecutePrice"] = ""
                params["presetStopSurplusType"] = "mark_price"

            # 4. Place market order
            return await self._futures_client.create_order(
                symbol=position.symbol, type="market", side=order_side, amount=amount, params=params
            )

    async def _wait_for_order_to_close(self, order_id: str, *, position: CreateMarketPositionOrder) -> None:
        fetched_order = await self._futures_client.fetch_order(order_id, symbol=position.symbol)
        while fetched_order.get("status", "open") not in ["closed", "canceled"]:
            await asyncio.sleep(delay=2.0)
            fetched_order = await self._futures_client.fetch_order(order_id, symbol=position.symbol)
        if fetched_order.get("status") != "closed":
            raise ValueError(
                f"Order for {position.symbol} :: {position.position_type}, status is {fetched_order.get('status')}"
            )

    async def _get_opened_position(self, *, position: CreateMarketPositionOrder) -> Position:
        open_positions = await self.get_open_positions()
        opened_position = next(
            (
                pos
                for pos in open_positions
                if pos.symbol == position.symbol and pos.position_type == position.position_type
            ),
            None,
        )
        if not opened_position:
            raise ValueError(f"Created position not found for symbol: {position.symbol}")
        return opened_position

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
            # Bitget doesn't have fetch_swap_markets(); use markets loaded in post_init()
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
    async def _get_spot_total_balance(self, account_info: AccountInfo) -> float:
        spot_balances = await self._spot_client.fetch_balance()
        spot_prices = await self._get_spot_prices()
        spot_totals = spot_balances.get("total", {})
        ret = spot_totals.pop(account_info.currency_code.upper(), 0.0)
        for currency, amount in spot_totals.items():
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
        # Bitget returns balance in a unified structure; extract the currency-specific data
        currency = account_info.currency_code.upper()
        total = float(futures_balances.get("total", {}).get(currency, 0.0))
        free = float(futures_balances.get("free", {}).get(currency, 0.0))
        used = float(futures_balances.get("used", {}).get(currency, 0.0))
        # Map to exchange-agnostic balance fields
        info = futures_balances.get("info", {})
        unrealized_pl = float(info.get("unrealizedPL") or 0.0) if isinstance(info, dict) else 0.0
        return {
            "equity": total,
            "availableBalance": free,
            "positionMargin": used,
            "cashBalance": total - unrealized_pl,
            "unrealizedPnl": unrealized_pl,
        }

    def _convert_raw_ticker_to_symbol_ticker(
        self, raw_ticker: dict[str, Any], *, mark_price: float | None = None
    ) -> SymbolTicker:
        return SymbolTicker(
            timestamp=raw_ticker["timestamp"],
            symbol=raw_ticker["symbol"],
            close=raw_ticker["close"],
            bid=raw_ticker["bid"],
            ask=raw_ticker["ask"],
            mark_price=float(mark_price) if mark_price is not None else None,
        )

    def _map_raw_position(self, raw_position: dict[str, Any], *, raw_stop_orders: list[dict[str, Any]]) -> Position:
        info = raw_position.get("info", {})

        # 1. Deterministic ID & Match Criteria
        hold_side = raw_position.get("side") or info.get("holdSide", "UNKNOWN")
        pos_side_lower = hold_side.lower()
        ccxt_symbol = raw_position.get("symbol", "UNKNOWN")
        margin_coin = info.get("marginCoin", "UNKNOWN")
        margin_mode = raw_position.get("marginMode", "isolated").lower()

        composite_id = f"{info.get('symbol', ccxt_symbol)}-{margin_coin}-{pos_side_lower}-{margin_mode}"

        # 2. Safely extract the fee
        deducted_fee_str = info.get("deductedFee")
        total_fee_str = info.get("totalFee")
        fee = (
            abs(float(deducted_fee_str)) if deducted_fee_str else (abs(float(total_fee_str)) if total_fee_str else 0.0)
        )

        # 3. Find matching Partial TP/SL orders using generator expressions
        tp_order = next(
            (
                order
                for order in raw_stop_orders
                if order.get("symbol") == ccxt_symbol
                and order.get("info", {}).get("posSide", "").lower() == pos_side_lower
                and order.get("info", {}).get("planType") == "profit_plan"
            ),
            None,
        )

        sl_order = next(
            (
                order
                for order in raw_stop_orders
                if order.get("symbol") == ccxt_symbol
                and order.get("info", {}).get("posSide", "").lower() == pos_side_lower
                and order.get("info", {}).get("planType") == "loss_plan"
            ),
            None,
        )

        # 4. Resolve final TP/SL values (Preferring the found stop orders)
        tp_trigger = tp_order.get("triggerPrice") if tp_order else None
        sl_trigger = sl_order.get("triggerPrice") if sl_order else None

        take_profit = (
            float(tp_trigger)
            if tp_trigger
            else (float(tp_str) if (tp_str := info.get("takeProfit") or raw_position.get("takeProfitPrice")) else None)
        )

        stop_loss = (
            float(sl_trigger)
            if sl_trigger
            else (float(sl_str) if (sl_str := info.get("stopLoss") or raw_position.get("stopLossPrice")) else None)
        )

        return Position(
            position_id=composite_id,
            symbol=ccxt_symbol,
            initial_margin=float(raw_position.get("initialMargin") or 0.0),
            leverage=int(raw_position.get("leverage") or 1),
            liquidation_price=float(raw_position.get("liquidationPrice") or 0.0),
            open_type=self._map_margin_mode(margin_mode),
            position_type=self._map_position_type(hold_side),
            entry_price=float(raw_position.get("entryPrice") or 0.0),
            contracts=float(raw_position.get("contracts") or 0.0),
            contract_size=float(raw_position.get("contractSize") or 1.0),
            fee=round(fee, ndigits=4),
            stop_loss_price=stop_loss,
            take_profit_price=take_profit,
        )

    def _map_position_type(self, side: str) -> PositionTypeEnum:
        """Map the raw 'side' field from the exchange to PositionTypeEnum."""
        match side.lower():
            case "long":
                return PositionTypeEnum.LONG
            case "short":
                return PositionTypeEnum.SHORT
            case _:
                raise ValueError(f"Unknown position side: {side}")

    def _map_margin_mode(self, margin_mode: str) -> PositionOpenTypeEnum:
        """Map the raw 'marginMode' from the exchange to PositionOpenTypeEnum."""
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
