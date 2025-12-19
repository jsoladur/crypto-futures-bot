import logging
from dataclasses import fields
from datetime import UTC, datetime, timedelta
from typing import override

from pyee.asyncio import AsyncIOEventEmitter
from sqlalchemy import delete, func, select
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

    @override
    def configure(self) -> None:
        self._event_emitter.add_listener(SIGNALS_EVALUATION_RESULT_EVENT_NAME, self._handle_signals_evaluation_result)

    @transactional(read_only=True)
    async def find_all_market_signals(
        self,
        crypto_currency: TrackedCryptoCurrencyItem,
        *,
        position_type: PositionTypeEnum | None = None,
        timeframe: Timeframe | None = None,
        session: AsyncSession | None = None,
    ) -> list[MarketSignalItem]:
        query = select(MarketSignal).where(MarketSignal.crypto_currency == crypto_currency.currency)
        if position_type is not None:
            query = query.where(MarketSignal.position_type == position_type)
        if timeframe is not None:
            query = query.where(MarketSignal.timeframe == timeframe)
        query = query.order_by(MarketSignal.timestamp.desc())
        query_result = await session.execute(query)
        ret = [self._convert_model_to_vo(market_signal) for market_signal in query_result.scalars().all()]
        return ret

    @transactional(read_only=True)
    async def find_last_market_signal(
        self,
        crypto_currency: TrackedCryptoCurrencyItem,
        *,
        position_type: PositionTypeEnum,
        timeframe: Timeframe = "15m",
        session: AsyncSession | None = None,
    ) -> MarketSignalItem | None:  # pragma: no cover
        query = (
            select(MarketSignal)
            .where(MarketSignal.crypto_currency == crypto_currency.currency)
            .where(MarketSignal.position_type == position_type)
            .where(MarketSignal.timeframe == timeframe)
            .order_by(MarketSignal.timestamp.desc())
            .limit(1)
        )
        query_result = await session.execute(query)
        last_market_signal = query_result.scalars().one_or_none()
        ret: MarketSignalItem | None = None
        if last_market_signal:
            ret = self._convert_model_to_vo(last_market_signal)
        return ret

    @transactional(read_only=True)
    async def exists_market_signal_by_timestamp(
        self,
        timestamp: int,
        crypto_currency: TrackedCryptoCurrencyItem,
        position_type: PositionTypeEnum,
        timeframe: Timeframe,
        *,
        session: AsyncSession | None = None,
    ) -> bool:
        query = (
            select(func.count(MarketSignal.id))
            .where(MarketSignal.timestamp == timestamp)
            .where(MarketSignal.crypto_currency == crypto_currency.currency)
            .where(MarketSignal.position_type == position_type)
            .where(MarketSignal.timeframe == timeframe)
        )
        query_result = await session.execute(query)
        count = query_result.scalar()
        return count > 0

    @transactional()
    async def _handle_signals_evaluation_result(
        self, signals_evaluation_result: SignalsEvaluationResult, *, session: AsyncSession
    ) -> None:
        await self._apply_market_signal_retention_policy(signals_evaluation_result, session=session)
        trade_now_hints = await self._trade_now_service.get_trade_now_hints(signals_evaluation_result.crypto_currency)
        signals_field_names = [field.name for field in fields(signals_evaluation_result) if field.type is bool]
        for signals_field_name in signals_field_names:
            if getattr(signals_evaluation_result, signals_field_name):
                await self._store_market_signal_if_needed(
                    signals_evaluation_result,
                    trade_now_hints,
                    is_long=signals_field_name.startswith("long"),
                    is_entry=signals_field_name.endswith("_entry"),
                    session=session,
                )

    async def _store_market_signal_if_needed(
        self,
        signals: SignalsEvaluationResult,
        trade_now_hints: TradeNowHints,
        is_long: bool,
        is_entry: bool,
        *,
        session: AsyncSession,
    ) -> None:
        timestamp = int(signals.timestamp.timestamp() * 1000)
        exists = await self.exists_market_signal_by_timestamp(
            timestamp=timestamp,
            crypto_currency=signals.crypto_currency,
            position_type=PositionTypeEnum.LONG if is_long else PositionTypeEnum.SHORT,
            timeframe=signals.timeframe,
            session=session,
        )
        if not exists:
            position_type = PositionTypeEnum.LONG if is_long else PositionTypeEnum.SHORT
            action_type = MarketActionTypeEnum.ENTRY if is_entry else MarketActionTypeEnum.EXIT
            position_hints = trade_now_hints.long if is_long else trade_now_hints.short
            market_signal = MarketSignal(
                timestamp=timestamp,
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
            .where(MarketSignal.crypto_currency == signals.crypto_currency.currency)
            .where(MarketSignal.timeframe == signals.timeframe)
            .where(MarketSignal.created_at < expiration_date)
        )
        await session.execute(query)

    def _convert_model_to_vo(self, market_signal: MarketSignal) -> MarketSignalItem:
        return MarketSignalItem(
            timestamp=market_signal.created_at,
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
