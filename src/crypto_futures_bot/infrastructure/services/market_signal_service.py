import logging
from asyncio import Lock
from dataclasses import fields
from datetime import UTC, datetime, timedelta
from typing import override

from pyee.asyncio import AsyncIOEventEmitter
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from crypto_futures_bot.config.configuration_properties import ConfigurationProperties
from crypto_futures_bot.constants import SIGNALS_EVALUATION_RESULT_EVENT_NAME
from crypto_futures_bot.domain.enums import MarketActionTypeEnum, PositionTypeEnum
from crypto_futures_bot.domain.types import Timeframe
from crypto_futures_bot.domain.vo import (
    MarketSignalItem,
    SignalsEvaluationResult,
    TrackedCryptoCurrencyItem,
    TradeNowHints,
)
from crypto_futures_bot.infrastructure.database.models.market_signal import MarketSignal
from crypto_futures_bot.infrastructure.services.base import AbstractEventHandlerService
from crypto_futures_bot.infrastructure.services.decorators import transactional
from crypto_futures_bot.infrastructure.services.push_notification_service import PushNotificationService
from crypto_futures_bot.infrastructure.services.trade_now_service import TradeNowService
from crypto_futures_bot.interfaces.telegram.services.telegram_service import TelegramService

logger = logging.getLogger(__name__)


class MarketSignalService(AbstractEventHandlerService):
    def __init__(
        self,
        configuration_properties: ConfigurationProperties,
        push_notification_service: PushNotificationService,
        telegram_service: TelegramService,
        event_emitter: AsyncIOEventEmitter,
        trade_now_service: TradeNowService,
    ) -> None:
        super().__init__(push_notification_service, telegram_service, event_emitter)
        self._configuration_properties = configuration_properties
        self._trade_now_service = trade_now_service
        self._lock = Lock()

    @override
    def configure(self) -> None:
        self._event_emitter.add_listener(SIGNALS_EVALUATION_RESULT_EVENT_NAME, self._handle_signals_evaluation_result)

    @transactional(read_only=True)
    async def find_last_market_signal(
        self,
        crypto_currency: TrackedCryptoCurrencyItem,
        *,
        position_type: PositionTypeEnum,
        timeframe: Timeframe = "15m",
        session: AsyncSession | None = None,
    ) -> MarketSignalItem | None:
        query = (
            select(MarketSignal)
            .where(MarketSignal.crypto_currency == crypto_currency.currency)
            .where(MarketSignal.position_type == position_type)
            .where(MarketSignal.timeframe == timeframe)
            .order_by(MarketSignal.created_at, ascending=False)
        )
        query_result = await session.execute(query)
        last_market_signal = query_result.scalars().one_or_none()
        ret: MarketSignalItem | None = None
        if last_market_signal:
            ret = self._convert_model_to_vo(last_market_signal)
        return ret

    @transactional()
    async def _handle_signals_evaluation_result(
        self, signals_evaluation_result: SignalsEvaluationResult, *, session: AsyncSession
    ) -> None:
        async with self._lock:
            await self._apply_market_signal_retention_policy(signals_evaluation_result, session=session)
            trade_now_hints = await self._trade_now_service.get_trade_now_hints(
                signals_evaluation_result.crypto_currency
            )
            signals_field_names = [field.name for field in fields(signals_evaluation_result) if field.type is bool]
            for signals_field_name in signals_field_names:
                if getattr(signals_evaluation_result, signals_field_name):
                    self._store_market_signal_if_needed(
                        signals_evaluation_result,
                        trade_now_hints,
                        is_long=signals_field_name.startswith("long"),
                        is_entry=signals_field_name.endswith("_entry"),
                        session=session,
                    )

    def _store_market_signal_if_needed(
        self,
        signals: SignalsEvaluationResult,
        trade_now_hints: TradeNowHints,
        is_long: bool,
        is_entry: bool,
        *,
        session: AsyncSession,
    ) -> None:
        position_type = PositionTypeEnum.LONG if is_long else PositionTypeEnum.SHORT
        action_type = MarketActionTypeEnum.ENTRY if is_entry else MarketActionTypeEnum.EXIT
        last_market_signal = self.find_last_market_signal(
            signals.crypto_currency, position_type=position_type, timeframe=signals.timeframe, session=session
        )
        if last_market_signal.position_type != position_type:
            position_hints = trade_now_hints.long if is_long else trade_now_hints.short
            market_signal = MarketSignal(
                crypto_currency=signals.crypto_currency.currency,
                timeframe=signals.timeframe,
                position_type=position_type,
                action_type=action_type,
                entry_price=position_hints.entry_price if is_entry else None,
                break_even_price=position_hints.break_even_price if is_entry else None,
                stop_loss_percent_value=trade_now_hints.stop_loss_percent_value if is_entry else None,
                take_profit_percent_value=trade_now_hints.take_profit_percent_value if is_entry else None,
                stop_loss_price=position_hints.stop_loss_price if is_entry else None,
                take_profit_price=position_hints.take_profit_price if is_entry else None,
            )
            session.add(market_signal)
            await session.flush()

    async def _apply_market_signal_retention_policy(
        self, signals: SignalsEvaluationResult, *, session: AsyncSession
    ) -> None:
        expiration_date = datetime.now(tz=UTC) - timedelta(
            days=self._configuration_properties.market_signal_retention_days
        )
        query = (
            delete(MarketSignal)
            .where(MarketSignal.symbol == signals.symbol)
            .where(MarketSignal.timeframe == signals.timeframe)
            .where(MarketSignal.timestamp < expiration_date)
        )
        await session.execute(query)

    def _convert_model_to_vo(self, market_signal: MarketSignal) -> MarketSignalItem:
        return MarketSignalItem(
            crypto_currency=TrackedCryptoCurrencyItem.from_currency(market_signal.crypto_currency),
            timeframe=market_signal.timeframe,
            position_type=market_signal.position_type,
            action_type=market_signal.action_type,
            entry_price=market_signal.entry_price,
            break_even_price=market_signal.break_even_price,
            stop_loss_percent_value=market_signal.stop_loss_percent_value,
            take_profit_percent_value=market_signal.take_profit_percent_value,
            stop_loss_price=market_signal.stop_loss_price,
            take_profit_price=market_signal.take_profit_price,
        )
