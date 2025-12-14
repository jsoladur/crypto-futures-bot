import math

from crypto_futures_bot.config.configuration_properties import ConfigurationProperties
from crypto_futures_bot.domain.vo import CandleStickIndicators, PositionMetrics
from crypto_futures_bot.infrastructure.adapters.futures_exchange.base import AbstractFuturesExchangeService
from crypto_futures_bot.infrastructure.adapters.futures_exchange.vo.symbol_market_config import SymbolMarketConfig
from crypto_futures_bot.infrastructure.services.base import AbstractService
from crypto_futures_bot.infrastructure.services.push_notification_service import PushNotificationService
from crypto_futures_bot.interfaces.telegram.services.telegram_service import TelegramService


class OrdersAnalyticsService(AbstractService):
    def __init__(
        self,
        configuration_properties: ConfigurationProperties,
        push_notification_service: PushNotificationService,
        futures_exchange_service: AbstractFuturesExchangeService,
        telegram_service: TelegramService,
    ) -> None:
        super().__init__(push_notification_service, telegram_service)
        self._configuration_properties = configuration_properties
        self._futures_exchange_service = futures_exchange_service

    async def get_open_position_metrics(self) -> list[PositionMetrics]:
        positions = await self._futures_exchange_service.get_open_positions()
        tickers = await self._futures_exchange_service.get_symbol_tickers(
            symbols=[position.symbol for position in positions]
        )
        tickers = {ticker.symbol: ticker for ticker in tickers}
        ret = []
        for position in positions:
            ticker = tickers[position.symbol]
            symbol_market_config = await self._futures_exchange_service.get_symbol_market_config(ticker.base_asset)
            ret.append(PositionMetrics(position=position, symbol_market_config=symbol_market_config, ticker=ticker))
        return ret

    def get_stop_loss_percent_value(
        self,
        avg_entry_price: float,
        *,
        last_candlestick_indicators: CandleStickIndicators,
        symbol_market_config: SymbolMarketConfig,
    ) -> float:
        stop_price = round(
            avg_entry_price - (last_candlestick_indicators.atr * self._configuration_properties.atr_sl_mult),
            ndigits=symbol_market_config.price_precision,
        )
        stop_loss_percent_value = abs(self._ceil_round((1 - (stop_price / avg_entry_price)) * 100, ndigits=2))
        return stop_loss_percent_value

    def get_stop_loss_price(
        self,
        entry_price: float,
        *,
        stop_loss_percent_value: float,
        is_long: bool,
        symbol_market_config: SymbolMarketConfig,
    ) -> float:
        stop_loss_price = round(
            entry_price * (1 - stop_loss_percent_value / 100)
            if is_long
            else entry_price * (1 + stop_loss_percent_value / 100),
            ndigits=symbol_market_config.price_precision,
        )
        return stop_loss_price

    def get_take_profit_percent_value(
        self,
        avg_entry_price: float,
        *,
        last_candlestick_indicators: CandleStickIndicators,
        symbol_market_config: SymbolMarketConfig,
    ) -> float:
        take_profit_price = round(
            avg_entry_price + (last_candlestick_indicators.atr * self._configuration_properties.atr_tp_mult),
            ndigits=symbol_market_config.price_precision,
        )
        take_profit_percent_value = abs(self._floor_round((1 - (take_profit_price / avg_entry_price)) * 100, ndigits=2))
        return take_profit_percent_value

    def get_take_profit_price(
        self,
        entry_price: float,
        *,
        take_profit_percent_value: float,
        is_long: bool,
        symbol_market_config: SymbolMarketConfig,
    ) -> float:
        take_profit_price = round(
            entry_price * (1 + take_profit_percent_value / 100)
            if is_long
            else entry_price * (1 - take_profit_percent_value / 100),
            ndigits=symbol_market_config.price_precision,
        )
        return take_profit_price

    def calculate_break_even_price(
        self, entry_price: float, *, symbol_market_config: SymbolMarketConfig, is_long: bool
    ) -> float:
        taker_fees = self._futures_exchange_service.get_taker_fee()
        if is_long:
            # For Longs: Exit Price must be higher to cover entry + exit fees
            # Formula: Entry * (1 + fee) / (1 - fee)
            fee_multiplier = (1.0 + taker_fees) / (1.0 - taker_fees)
        else:
            # For Shorts: Exit Price must be lower to cover entry + exit fees
            # Formula: Entry * (1 - fee) / (1 + fee)
            fee_multiplier = (1.0 - taker_fees) / (1.0 + taker_fees)
        break_even_price = round(entry_price * fee_multiplier, ndigits=symbol_market_config.price_precision)
        return break_even_price

    def _ceil_round(self, value: float, *, ndigits: int) -> float:
        factor = 10**ndigits
        return math.ceil(value * factor) / factor

    def _floor_round(self, value: float, *, ndigits: int) -> float:
        factor = 10**ndigits
        return math.floor(value * factor) / factor
