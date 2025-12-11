import math

from crypto_futures_bot.config.configuration_properties import ConfigurationProperties
from crypto_futures_bot.domain.vo import CandleStickIndicators
from crypto_futures_bot.infrastructure.adapters.futures_exchange.vo.symbol_market_config import SymbolMarketConfig
from crypto_futures_bot.infrastructure.services.base import AbstractService
from crypto_futures_bot.infrastructure.services.push_notification_service import PushNotificationService
from crypto_futures_bot.interfaces.telegram.services.telegram_service import TelegramService


class OrdersAnalyticsService(AbstractService):
    def __init__(
        self,
        configuration_properties: ConfigurationProperties,
        push_notification_service: PushNotificationService,
        telegram_service: TelegramService,
    ) -> None:
        super().__init__(push_notification_service, telegram_service)
        self._configuration_properties = configuration_properties

    def calculate_stop_loss_percent_value(
        self,
        avg_entry_price: float,
        *,
        last_candlestick_indicators: CandleStickIndicators,
        trading_market_config: SymbolMarketConfig,
    ) -> float:
        stop_price = round(
            avg_entry_price - (last_candlestick_indicators.atr * self._configuration_properties.atr_sl_mult),
            ndigits=trading_market_config.price_precision,
        )
        stop_loss_percent_value = self._ceil_round((1 - (stop_price / avg_entry_price)) * 100, ndigits=2)
        return stop_loss_percent_value

    def calculate_take_profit_percent_value(
        self,
        avg_entry_price: float,
        *,
        last_candlestick_indicators: CandleStickIndicators,
        trading_market_config: SymbolMarketConfig,
    ) -> float:
        take_profit_price = round(
            avg_entry_price + (last_candlestick_indicators.atr * self._configuration_properties.atr_tp_mult),
            ndigits=trading_market_config.price_precision,
        )
        take_profit_percent_value = self._floor_round((1 - (take_profit_price / avg_entry_price)) * 100, ndigits=2)
        return take_profit_percent_value

    def _ceil_round(self, value: float, *, ndigits: int) -> float:
        factor = 10**ndigits
        return math.ceil(value * factor) / factor

    def _floor_round(self, value: float, *, ndigits: int) -> float:
        factor = 10**ndigits
        return math.floor(value * factor) / factor
