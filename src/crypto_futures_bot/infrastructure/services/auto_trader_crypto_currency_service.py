import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from crypto_futures_bot.domain.vo import AutoTraderCryptoCurrencyItem
from crypto_futures_bot.infrastructure.database.models.auto_trader_crypto_currency import AutoTraderCryptoCurrency
from crypto_futures_bot.infrastructure.services.decorators import transactional
from crypto_futures_bot.infrastructure.services.tracked_crypto_currency_service import TrackedCryptoCurrencyService

logger = logging.getLogger(__name__)


class AutoTraderCryptoCurrencyService:
    def __init__(self, tracked_crypto_currency_service: TrackedCryptoCurrencyService) -> None:
        self._tracked_crypto_currency_service = tracked_crypto_currency_service

    @transactional(read_only=True)
    async def find_all(self, *, session: AsyncSession | None = None) -> list[AutoTraderCryptoCurrencyItem]:
        query = select(AutoTraderCryptoCurrency)
        query_result = await session.execute(query)
        entities = query_result.scalars().all()
        ret = [
            AutoTraderCryptoCurrencyItem(currency=entity.currency, activated=entity.activated) for entity in entities
        ]
        tracked_crypto_currencies = [
            item.currency for item in await self._tracked_crypto_currency_service.find_all(session=session)
        ]
        for tracked_crypto_currency in tracked_crypto_currencies:
            if not any(item.currency == tracked_crypto_currency for item in ret):
                ret.append(AutoTraderCryptoCurrencyItem(currency=tracked_crypto_currency, activated=False))
        ret = sorted(ret, key=lambda x: x.currency)
        return ret

    @transactional(read_only=True)
    async def is_enable_for(self, crypto_currency: str, *, session: AsyncSession | None = None) -> int:
        entity = await self._find_one_or_none(crypto_currency, session=session)
        return entity.activated if entity else False

    @transactional()
    async def toggle_for(self, crypto_currency: str, *, session: AsyncSession) -> AutoTraderCryptoCurrencyItem:
        entity = await self._find_one_or_none(crypto_currency, session=session)
        if entity:
            entity.activated = not entity.activated
        else:
            entity = AutoTraderCryptoCurrency(currency=crypto_currency, activated=True)
            session.add(entity)
        await session.flush()
        return AutoTraderCryptoCurrencyItem(currency=entity.currency, activated=entity.activated)

    async def _find_one_or_none(self, currency: str, *, session: AsyncSession) -> AutoTraderCryptoCurrency | None:
        query = select(AutoTraderCryptoCurrency).where(AutoTraderCryptoCurrency.currency == currency)
        query_result = await session.execute(query)
        entity: AutoTraderCryptoCurrency | None = query_result.scalars().one_or_none()
        return entity
