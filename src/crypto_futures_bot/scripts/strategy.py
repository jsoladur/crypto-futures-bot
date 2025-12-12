from typing import Any

import pandas as pd
from backtesting import Strategy

from crypto_futures_bot.domain.enums import CandleStickEnum
from crypto_futures_bot.domain.vo.candlestick_indicators import CandleStickIndicators
from crypto_futures_bot.infrastructure.services.orders_analytics_service import OrdersAnalyticsService
from crypto_futures_bot.infrastructure.tasks.signals_task_service import SignalsTaskService


class BotStrategy(Strategy):
    # These will be injected
    signals_service: SignalsTaskService
    orders_service: OrdersAnalyticsService
    symbol_market_config: Any

    def init(self):
        # Indicators are already computed in the dataframe passed to Backtest
        pass

    def next(self):
        # Need at least 2 candles to compare PREV and LAST
        if len(self.data) < 2:
            return

        def get_series(idx):
            # idx is -1 (last) or -2 (prev)
            timestamp = self.data.index[idx]
            return pd.Series(
                {
                    "ema50": self.data.ema50[idx],
                    "macd_hist": self.data.macd_hist[idx],
                    "stoch_rsi_k": self.data.stoch_rsi_k[idx],
                    "stoch_rsi_d": self.data.stoch_rsi_d[idx],
                    "close": self.data.Close[idx],
                    "atr": self.data.atr[idx],
                    "timestamp": timestamp,
                }
            )

        prev_series = get_series(-2)
        last_series = get_series(-1)

        prev_candle = CandleStickIndicators.from_series(symbol="TEST", index=CandleStickEnum.PREV, series=prev_series)
        last_candle = CandleStickIndicators.from_series(symbol="TEST", index=CandleStickEnum.LAST, series=last_series)

        # Check signals
        # We access private methods of signals_service
        is_long_entry = self.signals_service._is_long_entry(prev_candle, last_candle)
        is_short_entry = self.signals_service._is_short_entry(prev_candle, last_candle)
        is_long_exit = self.signals_service._is_long_exit(prev_candle, last_candle)
        is_short_exit = self.signals_service._is_short_exit(prev_candle, last_candle)

        entry_price = self.data.Close[-1]

        # Exit logic
        if self.position:
            if self.position.is_long and is_long_exit:
                self.position.close()
            elif self.position.is_short and is_short_exit:
                self.position.close()

        # Entry logic
        if not self.position:
            if is_long_entry:
                sl_pct = self.orders_service.get_stop_loss_percent_value(
                    avg_entry_price=entry_price,
                    last_candlestick_indicators=last_candle,
                    symbol_market_config=self.symbol_market_config,
                )
                tp_pct = self.orders_service.get_take_profit_percent_value(
                    avg_entry_price=entry_price,
                    last_candlestick_indicators=last_candle,
                    symbol_market_config=self.symbol_market_config,
                )

                sl_price = self.orders_service.get_stop_loss_price(
                    entry_price=entry_price,
                    stop_loss_percent_value=sl_pct,
                    is_long=True,
                    symbol_market_config=self.symbol_market_config,
                )
                tp_price = self.orders_service.get_take_profit_price(
                    entry_price=entry_price,
                    take_profit_percent_value=tp_pct,
                    is_long=True,
                    symbol_market_config=self.symbol_market_config,
                )

                self.buy(sl=sl_price, tp=tp_price)

            elif is_short_entry:
                sl_pct = self.orders_service.get_stop_loss_percent_value(
                    avg_entry_price=entry_price,
                    last_candlestick_indicators=last_candle,
                    symbol_market_config=self.symbol_market_config,
                )
                tp_pct = self.orders_service.get_take_profit_percent_value(
                    avg_entry_price=entry_price,
                    last_candlestick_indicators=last_candle,
                    symbol_market_config=self.symbol_market_config,
                )

                sl_price = self.orders_service.get_stop_loss_price(
                    entry_price=entry_price,
                    stop_loss_percent_value=sl_pct,
                    is_long=False,
                    symbol_market_config=self.symbol_market_config,
                )
                tp_price = self.orders_service.get_take_profit_price(
                    entry_price=entry_price,
                    take_profit_percent_value=tp_pct,
                    is_long=False,
                    symbol_market_config=self.symbol_market_config,
                )

                self.sell(sl=sl_price, tp=tp_price)
