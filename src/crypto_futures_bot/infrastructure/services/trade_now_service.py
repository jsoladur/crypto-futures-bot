import math

from crypto_futures_bot.domain.enums import OpenPositionResultTypeEnum, PositionOpenTypeEnum, PositionTypeEnum
from crypto_futures_bot.domain.vo import (
    CandleStickIndicators,
    OpenPositionResult,
    PositionHints,
    RiskManagementItem,
    SignalParametrizationItem,
    TrackedCryptoCurrencyItem,
    TradeNowHints,
)
from crypto_futures_bot.infrastructure.adapters.futures_exchange.base import AbstractFuturesExchangeService
from crypto_futures_bot.infrastructure.adapters.futures_exchange.vo import (
    CreateMarketPositionOrder,
    FuturesWallet,
    PortfolioBalance,
    SymbolMarketConfig,
    SymbolTicker,
)
from crypto_futures_bot.infrastructure.services.auto_trader_crypto_currency_service import (
    AutoTraderCryptoCurrencyService,
)
from crypto_futures_bot.infrastructure.services.crypto_technical_analysis_service import CryptoTechnicalAnalysisService
from crypto_futures_bot.infrastructure.services.orders_analytics_service import OrdersAnalyticsService
from crypto_futures_bot.infrastructure.services.risk_management_service import RiskManagementService
from crypto_futures_bot.infrastructure.services.signal_parametrization_service import SignalParametrizationService
from crypto_futures_bot.infrastructure.services.tracked_crypto_currency_service import TrackedCryptoCurrencyService


class TradeNowService:
    def __init__(
        self,
        futures_exchange_service: AbstractFuturesExchangeService,
        signal_parametrization_service: SignalParametrizationService,
        crypto_technical_analysis_service: CryptoTechnicalAnalysisService,
        orders_analytics_service: OrdersAnalyticsService,
        risk_management_service: RiskManagementService,
        tracked_crypto_currency_service: TrackedCryptoCurrencyService,
        auto_trader_crypto_currency_service: AutoTraderCryptoCurrencyService,
    ):
        self._futures_exchange_service = futures_exchange_service
        self._signal_parametrization_service = signal_parametrization_service
        self._crypto_technical_analysis_service = crypto_technical_analysis_service
        self._orders_analytics_service = orders_analytics_service
        self._risk_management_service = risk_management_service
        self._tracked_crypto_currency_service = tracked_crypto_currency_service
        self._auto_trader_crypto_currency_service = auto_trader_crypto_currency_service

    async def open_position(
        self, crypto_currency: TrackedCryptoCurrencyItem, position_type: PositionTypeEnum
    ) -> OpenPositionResult:
        account_info = await self._futures_exchange_service.get_account_info()
        open_positions = await self._orders_analytics_service.get_open_position_metrics()
        symbols = set(p.position.symbol for p in open_positions)
        if crypto_currency.to_symbol(account_info) in symbols:
            ret = OpenPositionResult(
                result_type=OpenPositionResultTypeEnum.ALREADY_OPEN,
                crypto_currency=crypto_currency,
                position_type=position_type,
            )
        else:
            risk_management = await self._risk_management_service.get()
            if len(open_positions) >= risk_management.number_of_concurrent_trades:
                ret = OpenPositionResult(
                    result_type=OpenPositionResultTypeEnum.MAX_CONCURRENT_POSITIONS_REACHED,
                    crypto_currency=crypto_currency,
                    position_type=position_type,
                )
            else:
                trade_now_hints = await self.get_trade_now_hints(crypto_currency, risk_management=risk_management)
                position_hints = (
                    trade_now_hints.long if position_type == PositionTypeEnum.LONG else trade_now_hints.short
                )
                if position_hints.margin <= 0:
                    ret = OpenPositionResult(
                        result_type=OpenPositionResultTypeEnum.NO_FUNDS,
                        crypto_currency=crypto_currency,
                        position_type=position_type,
                    )
                else:
                    market_position_order = CreateMarketPositionOrder(
                        symbol=crypto_currency.to_symbol(account_info=account_info),
                        initial_margin=position_hints.margin,
                        leverage=position_hints.leverage,
                        open_type=PositionOpenTypeEnum.ISOLATED,
                        position_type=position_type,
                        stop_loss_price=position_hints.stop_loss_price,
                        take_profit_price=position_hints.take_profit_price,
                    )
                    opened_position = await self._futures_exchange_service.create_market_position_order(
                        position=market_position_order
                    )
                    position_metrics = await self._orders_analytics_service.get_metrics_by_position_id(
                        position_id=opened_position.position_id
                    )
                    ret = OpenPositionResult(
                        result_type=OpenPositionResultTypeEnum.SUCCESS,
                        crypto_currency=crypto_currency,
                        position_type=position_type,
                        position_metrics=position_metrics,
                    )
        return ret

    async def get_trade_now_hints(
        self,
        tracked_crypto_currency: TrackedCryptoCurrencyItem,
        *,
        risk_management: RiskManagementItem | None = None,
        signal_parametrization_item: SignalParametrizationItem | None = None,
    ) -> TradeNowHints:
        account_info = await self._futures_exchange_service.get_account_info()
        symbol = tracked_crypto_currency.to_symbol(account_info)
        portfolio_balance = await self._futures_exchange_service.get_portfolio_balance()
        futures_wallet = await self._futures_exchange_service.get_futures_wallet()
        ticker = await self._futures_exchange_service.get_symbol_ticker(symbol=symbol)
        signal_parametrization_item = (
            signal_parametrization_item
            or await self._signal_parametrization_service.find_by_crypto_currency(
                crypto_currency=tracked_crypto_currency.currency
            )
        )
        symbol_market_config = await self._futures_exchange_service.get_symbol_market_config(
            crypto_currency=tracked_crypto_currency.currency
        )
        candlestick_indicators = await self._crypto_technical_analysis_service.get_candlestick_indicators(symbol=symbol)
        stop_loss_percent_value = self._orders_analytics_service.get_stop_loss_percent_value(
            entry_price=ticker.ask_or_close,
            last_candlestick_indicators=candlestick_indicators,
            signal_parametrization_item=signal_parametrization_item,
            symbol_market_config=symbol_market_config,
        )
        take_profit_percent_value = self._orders_analytics_service.get_take_profit_percent_value(
            entry_price=ticker.ask_or_close,
            last_candlestick_indicators=candlestick_indicators,
            signal_parametrization_item=signal_parametrization_item,
            symbol_market_config=symbol_market_config,
        )
        long = await self._calculate_position_hints(
            portfolio_balance=portfolio_balance,
            futures_wallet=futures_wallet,
            ticker=ticker,
            stop_loss_percent_value=stop_loss_percent_value,
            candlestick_indicators=candlestick_indicators,
            signal_parametrization_item=signal_parametrization_item,
            symbol_market_config=symbol_market_config,
            risk_management=risk_management,
            is_long=True,
        )
        short = await self._calculate_position_hints(
            portfolio_balance=portfolio_balance,
            futures_wallet=futures_wallet,
            ticker=ticker,
            stop_loss_percent_value=stop_loss_percent_value,
            candlestick_indicators=candlestick_indicators,
            signal_parametrization_item=signal_parametrization_item,
            symbol_market_config=symbol_market_config,
            risk_management=risk_management,
            is_long=False,
        )
        return TradeNowHints(
            ticker=ticker,
            candlestick_indicators=candlestick_indicators,
            stop_loss_percent_value=stop_loss_percent_value,
            take_profit_percent_value=take_profit_percent_value,
            long=long,
            short=short,
        )

    async def _calculate_position_hints(
        self,
        portfolio_balance: PortfolioBalance,
        futures_wallet: FuturesWallet,
        ticker: SymbolTicker,
        stop_loss_percent_value: float,
        candlestick_indicators: CandleStickIndicators,
        signal_parametrization_item: SignalParametrizationItem,
        symbol_market_config: SymbolMarketConfig,
        *,
        is_long: bool,
        risk_management: RiskManagementItem | None = None,
        maintenance_margin_rate: float = 0.01,
    ) -> PositionHints:
        entry_price = ticker.ask_or_close if is_long else ticker.bid_or_close

        # 1. Calculate Stop Loss Price
        stop_loss_price = self._orders_analytics_service.get_stop_loss_price(
            entry_price=entry_price,
            stop_loss_percent_value=stop_loss_percent_value,
            is_long=is_long,
            symbol_market_config=symbol_market_config,
        )

        # 2. Risk & Leverage Calculation
        num_tracked_assets = await self._tracked_crypto_currency_service.count()
        num_auto_traded_enabled_assets = await self._auto_trader_crypto_currency_service.count_enabled()
        num_assets_investing = min(num_tracked_assets, num_auto_traded_enabled_assets)
        num_assets_investing = num_assets_investing if num_assets_investing > 0 else 1
        if not risk_management:
            risk_management = await self._risk_management_service.get()

        # Financial Goal: How much we WANT to risk
        desired_risk_amount = round(
            portfolio_balance.total_balance * (risk_management.percent_value / 100),
            ndigits=symbol_market_config.price_precision,
        )
        target_notional_size = round(
            desired_risk_amount / (stop_loss_percent_value / 100), ndigits=symbol_market_config.price_precision
        )
        # Margin Availability
        available_margin = round(
            min(portfolio_balance.futures_balance / num_assets_investing, futures_wallet.available_balance),
            ndigits=symbol_market_config.price_precision,
        )
        # Safety Constraint: Max Leverage < 1 / (SL% + MMR)
        max_survival_leverage = math.floor(0.95 * (1.0 / ((stop_loss_percent_value / 100) + maintenance_margin_rate)))
        # Financial Constraint: Leverage needed to hit risk target
        required_leverage = math.ceil(target_notional_size / available_margin) if available_margin > 0 else 1
        # Final Decision: Pick the smaller leverage
        final_leverage = min(
            required_leverage if required_leverage > 0 else 1, max_survival_leverage if max_survival_leverage > 0 else 1
        )
        final_leverage = final_leverage if final_leverage > 0 else 1
        # 3. Calculate Liquidation Price
        if is_long:
            liquidation_price = round(
                entry_price * (1 - (1 / final_leverage) + maintenance_margin_rate),
                ndigits=symbol_market_config.price_precision,
            )
            is_safe = liquidation_price < stop_loss_price
        else:
            liquidation_price = round(
                ticker.bid_or_close * (1 + (1 / final_leverage) - maintenance_margin_rate),
                ndigits=symbol_market_config.price_precision,
            )
            is_safe = liquidation_price > stop_loss_price

        # 4. Calculate Take Profit Prices
        move_sl_to_break_even_price, move_sl_to_first_target_profit_price, take_profit_price = (
            self._orders_analytics_service.get_take_profit_price_levels(
                entry_price=entry_price,
                is_long=is_long,
                last_candlestick_indicators=candlestick_indicators,
                signal_parametrization_item=signal_parametrization_item,
                symbol_market_config=symbol_market_config,
            )
        )

        # --- NEW: Calculate Final Potential PnL ---
        # We must use the ACTUAL size (which might be smaller than target if capped)
        final_notional_size = round(available_margin * final_leverage, ndigits=symbol_market_config.price_precision)

        # Loss: Size * % distance to SL
        # We use the percent value directly as it's cleaner, but using price diff is also fine.
        potential_loss = final_notional_size * (stop_loss_percent_value / 100)

        # Profit: Size * % distance to TP
        # We calculate the distance because we only have the TP Price, not the TP %.
        price_diff = abs(take_profit_price - entry_price)
        potential_profit = final_notional_size * (price_diff / entry_price)

        return PositionHints(
            entry_price=entry_price,
            break_even_price=self._orders_analytics_service.calculate_break_even_price(
                entry_price=entry_price, symbol_market_config=symbol_market_config, is_long=is_long
            ),
            is_long=is_long,
            is_safe=is_safe,
            margin=available_margin,
            leverage=final_leverage,
            notional_size=final_notional_size,
            liquidation_price=liquidation_price,
            stop_loss_price=stop_loss_price,
            move_sl_to_break_even_price=move_sl_to_break_even_price,
            move_sl_to_first_target_profit_price=move_sl_to_first_target_profit_price,
            take_profit_price=take_profit_price,
            potential_loss=round(potential_loss, ndigits=symbol_market_config.price_precision),
            potential_profit=round(potential_profit, ndigits=symbol_market_config.price_precision),
        )
