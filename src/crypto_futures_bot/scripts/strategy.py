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

        # 1. Define Standard Indicators
        prev_candle = CandleStickIndicators.from_series(symbol="TEST", index=CandleStickEnum.PREV, series=prev_series)
        last_candle = CandleStickIndicators.from_series(symbol="TEST", index=CandleStickEnum.LAST, series=last_series)

        current_price = self.data.Close[-1]
        current_high = self.data.High[-1]
        current_low = self.data.Low[-1]

        # 2. Check Signals
        is_long_entry = self.signals_task_service._is_long_entry(prev_candle, last_candle)
        is_short_entry = self.signals_task_service._is_short_entry(prev_candle, last_candle)

        # -----------------------------------------------------------
        # TRAILING STOP LOGIC (Manage Existing Position)
        # -----------------------------------------------------------
        if self.position:
            # FIX 1: Use the POSITION direction, not the current signal
            current_trade = self.trades[-1]
            entry_price = current_trade.entry_price

            # Calculate dynamic levels based on original entry
            trigger_level_1, trigger_level_2, _ = self.orders_analytics_service.get_take_profit_price_levels(
                entry_price=entry_price,
                is_long=self.position.is_long,  # <--- Fix: Use Position direction
                last_candlestick_indicators=last_candle,
                signal_parametrization_item=self.signal_parametrization,
                symbol_market_config=self.symbol_market_config,
            )

            # Calculate Break Even Price
            break_even_price = self.orders_analytics_service.calculate_break_even_price(
                entry_price=entry_price, symbol_market_config=self.symbol_market_config, is_long=self.position.is_long
            )

            # LONG MANAGEMENT
            if self.position.is_long:
                # Ladder Step 2: If we hit Target 2, move SL to Target 1 (Trigger Level 1)
                # Note: Your text said "move to break_even_price" here, but usually laddering moves up.
                # I implemented your text requirement: Move to 'trigger_level_1'
                # (Assuming trigger_level_1 > break_even > entry)
                if current_high >= trigger_level_2:
                    # Logic: If price hits 5% gain, lock in 2% gain.
                    if current_trade.sl < trigger_level_1:  # Only move up
                        current_trade.sl = trigger_level_1

                # Ladder Step 1: If we hit Target 1, move SL to Break Even
                elif current_high >= trigger_level_1:
                    if current_trade.sl < break_even_price:  # Only move up
                        current_trade.sl = break_even_price

            # SHORT MANAGEMENT (FIX 2: Add this block)
            else:
                # Ladder Step 2: Price drops BELOW Target 2
                if current_low <= trigger_level_2:
                    # Stop Loss moves DOWN for shorts. Check if new SL is lower than current.
                    if current_trade.sl > trigger_level_1:
                        current_trade.sl = trigger_level_1

                # Ladder Step 1: Price drops BELOW Target 1
                elif current_low <= trigger_level_1:
                    if current_trade.sl > break_even_price:
                        current_trade.sl = break_even_price

        # -----------------------------------------------------------
        # ENTRY LOGIC
        # -----------------------------------------------------------
        elif is_long_entry or is_short_entry:
            sl_pct = self.orders_analytics_service.get_stop_loss_percent_value(
                entry_price=current_price,
                last_candlestick_indicators=last_candle,
                symbol_market_config=self.symbol_market_config,
                signal_parametrization_item=self.signal_parametrization,
            )

            sl_price = self.orders_analytics_service.get_stop_loss_price(
                entry_price=current_price,
                stop_loss_percent_value=sl_pct,
                is_long=is_long_entry,
                symbol_market_config=self.symbol_market_config,
            )

            # We ignore the triggers here, we only need the Hard TP
            *_, tp_price = self.orders_analytics_service.get_take_profit_price_levels(
                entry_price=current_price,
                is_long=is_long_entry,
                last_candlestick_indicators=last_candle,
                signal_parametrization_item=self.signal_parametrization,
                symbol_market_config=self.symbol_market_config,
            )

            if is_long_entry:
                self.buy(sl=sl_price, tp=tp_price)
            else:
                self.sell(sl=sl_price, tp=tp_price)
