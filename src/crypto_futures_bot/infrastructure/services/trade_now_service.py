from crypto_futures_bot.domain.vo import (
    PositionHints,
    SignalParametrizationItem,
    TrackedCryptoCurrencyItem,
    TradeNowHints,
)
from crypto_futures_bot.infrastructure.adapters.futures_exchange.base import AbstractFuturesExchangeService
from crypto_futures_bot.infrastructure.services.crypto_technical_analysis_service import CryptoTechnicalAnalysisService
from crypto_futures_bot.infrastructure.services.orders_analytics_service import OrdersAnalyticsService
from crypto_futures_bot.infrastructure.services.signal_parametrization_service import SignalParametrizationService


class TradeNowService:
    def __init__(
        self,
        futures_exchange_service: AbstractFuturesExchangeService,
        signal_parametrization_service: SignalParametrizationService,
        crypto_technical_analysis_service: CryptoTechnicalAnalysisService,
        orders_analytics_service: OrdersAnalyticsService,
    ):
        self._futures_exchange_service = futures_exchange_service
        self._signal_parametrization_service = signal_parametrization_service
        self._crypto_technical_analysis_service = crypto_technical_analysis_service
        self._orders_analytics_service = orders_analytics_service

    async def get_trade_now_hints(
        self,
        tracked_crypto_currency: TrackedCryptoCurrencyItem,
        *,
        signal_parametrization_item: SignalParametrizationItem | None = None,
    ) -> TradeNowHints:
        account_info = await self._futures_exchange_service.get_account_info()
        symbol = tracked_crypto_currency.to_symbol(account_info)
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
        long_move_sl_to_break_even_price, long_move_sl_to_first_target_profit_price, long_take_profit_price = (
            self._orders_analytics_service.get_take_profit_price_levels(
                entry_price=ticker.ask_or_close,
                is_long=True,
                last_candlestick_indicators=candlestick_indicators,
                signal_parametrization_item=signal_parametrization_item,
                symbol_market_config=symbol_market_config,
            )
        )
        short_move_sl_to_break_even_price, short_move_sl_to_first_target_profit_price, short_take_profit_price = (
            self._orders_analytics_service.get_take_profit_price_levels(
                entry_price=ticker.bid_or_close,
                is_long=False,
                last_candlestick_indicators=candlestick_indicators,
                signal_parametrization_item=signal_parametrization_item,
                symbol_market_config=symbol_market_config,
            )
        )
        return TradeNowHints(
            ticker=ticker,
            candlestick_indicators=candlestick_indicators,
            stop_loss_percent_value=stop_loss_percent_value,
            take_profit_percent_value=take_profit_percent_value,
            long=PositionHints(
                entry_price=ticker.ask_or_close,
                break_even_price=self._orders_analytics_service.calculate_break_even_price(
                    entry_price=ticker.ask_or_close, symbol_market_config=symbol_market_config, is_long=True
                ),
                is_long=True,
                stop_loss_price=self._orders_analytics_service.get_stop_loss_price(
                    entry_price=ticker.ask_or_close,
                    stop_loss_percent_value=stop_loss_percent_value,
                    is_long=True,
                    symbol_market_config=symbol_market_config,
                ),
                move_sl_to_break_even_price=long_move_sl_to_break_even_price,
                move_sl_to_first_target_profit_price=long_move_sl_to_first_target_profit_price,
                take_profit_price=long_take_profit_price,
            ),
            short=PositionHints(
                entry_price=ticker.bid_or_close,
                break_even_price=self._orders_analytics_service.calculate_break_even_price(
                    entry_price=ticker.bid_or_close, symbol_market_config=symbol_market_config, is_long=False
                ),
                is_long=False,
                stop_loss_price=self._orders_analytics_service.get_stop_loss_price(
                    entry_price=ticker.bid_or_close,
                    stop_loss_percent_value=stop_loss_percent_value,
                    is_long=False,
                    symbol_market_config=symbol_market_config,
                ),
                move_sl_to_break_even_price=short_move_sl_to_break_even_price,
                move_sl_to_first_target_profit_price=short_move_sl_to_first_target_profit_price,
                take_profit_price=short_take_profit_price,
            ),
        )
