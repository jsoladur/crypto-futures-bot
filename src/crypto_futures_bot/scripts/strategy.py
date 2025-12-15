from backtesting import Strategy

from crypto_futures_bot.domain.enums import CandleStickEnum
from crypto_futures_bot.domain.vo import SignalParametrizationItem
from crypto_futures_bot.domain.vo.candlestick_indicators import CandleStickIndicators
from crypto_futures_bot.infrastructure.adapters.futures_exchange.vo import SymbolMarketConfig
from crypto_futures_bot.infrastructure.services.orders_analytics_service import OrdersAnalyticsService
from crypto_futures_bot.infrastructure.tasks.signals_task_service import SignalsTaskService


class BotStrategy(Strategy):
    # These will be injected
    signals_task_service: SignalsTaskService | None = None
    orders_analytics_service: OrdersAnalyticsService | None = None
    symbol_market_config: SymbolMarketConfig | None = None
    signal_parametrization: SignalParametrizationItem | None = None

    def init(self):
        # Indicators are already computed in the dataframe passed to Backtest
        pass

    def next(self):
        # Need at least 2 candles to compare PREV and LAST
        if len(self.data) < 2:
            return

        prev_series = self.data.df.iloc[-2]
        last_series = self.data.df.iloc[-1]
        # current_price = self.data.Close[-1]

        prev_candle = CandleStickIndicators.from_series(symbol="TEST", index=CandleStickEnum.PREV, series=prev_series)
        last_candle = CandleStickIndicators.from_series(symbol="TEST", index=CandleStickEnum.LAST, series=last_series)

        # Check signals
        # We access private methods of signals_task_service
        is_long_entry = self.signals_task_service._is_long_entry(prev_candle, last_candle)
        is_short_entry = self.signals_task_service._is_short_entry(prev_candle, last_candle)
        # is_long_exit = self.signals_task_service._is_long_exit(prev_candle, last_candle)
        # is_short_exit = self.signals_task_service._is_short_exit(prev_candle, last_candle)
        # Exit logic
        # if self.position:
        #     entry_price = self.trades[-1].entry_price
        #     break_even_price = self.orders_analytics_service.calculate_break_even_price(
        #         entry_price=entry_price, symbol_market_config=self.symbol_market_config, is_long=self.position.is_long
        #     )
        #     if self.position.is_long and is_long_exit and current_price > break_even_price:
        #         self.position.close()
        #     elif self.position.is_short and is_short_exit and current_price < break_even_price:
        #         self.position.close()
        # Entry logic
        if not self.position and (is_long_entry or is_short_entry):
            entry_price = self.data.Close[-1]
            sl_pct = self.orders_analytics_service.get_stop_loss_percent_value(
                avg_entry_price=entry_price,
                last_candlestick_indicators=last_candle,
                symbol_market_config=self.symbol_market_config,
                signal_parametrization_item=self.signal_parametrization,
            )
            tp_pct = self.orders_analytics_service.get_take_profit_percent_value(
                avg_entry_price=entry_price,
                last_candlestick_indicators=last_candle,
                symbol_market_config=self.symbol_market_config,
                signal_parametrization_item=self.signal_parametrization,
            )

            sl_price = self.orders_analytics_service.get_stop_loss_price(
                entry_price=entry_price,
                stop_loss_percent_value=sl_pct,
                is_long=is_long_entry,
                symbol_market_config=self.symbol_market_config,
            )
            tp_price = self.orders_analytics_service.get_take_profit_price(
                entry_price=entry_price,
                take_profit_percent_value=tp_pct,
                is_long=is_long_entry,
                symbol_market_config=self.symbol_market_config,
            )
            if is_long_entry:
                self.buy(sl=sl_price, tp=tp_price)
            else:
                self.sell(sl=sl_price, tp=tp_price)
