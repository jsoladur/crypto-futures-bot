import logging

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from crypto_futures_bot.infrastructure.adapters.futures_exchange.base import AbstractFuturesExchangeService
from crypto_futures_bot.infrastructure.database.models.tracked_crypto_currency import TrackedCryptoCurrency
from crypto_futures_bot.infrastructure.services.decorators import transactional
from crypto_futures_bot.interfaces.telegram.services.vo.tracked_crypto_currency_item import TrackedCryptoCurrencyItem

logger = logging.getLogger(__name__)


class TrackedCryptoCurrencyService:
    def __init__(self, futures_exchange_service: AbstractFuturesExchangeService) -> None:
        self._futures_exchange_service = futures_exchange_service

    @transactional(read_only=True)
    async def find_all(self, *, session: AsyncSession | None = None) -> list[TrackedCryptoCurrencyItem]:
        result = await session.execute(select(TrackedCryptoCurrency))
        entities = result.scalars().all()
        return [TrackedCryptoCurrencyItem(currency=entity.currency) for entity in entities]

    @transactional()
    async def add(self, currency: str, *, session: AsyncSession | None = None) -> None:
        currency = currency.upper()
        query = (
            select(func.count(TrackedCryptoCurrency.id))
            .select_from(TrackedCryptoCurrency)
            .where(TrackedCryptoCurrency.currency == currency)
        )
        result = await session.execute(query)
        count = result.scalar()
        if count == 0:
            favourite_crypto_currency = TrackedCryptoCurrency(currency=currency)
            session.add(favourite_crypto_currency)
            logger.info(f"Added {currency} to favourite crypto currencies")

    @transactional()
    async def remove(self, currency: str, *, session: AsyncSession | None = None) -> None:
        currency = currency.upper()
        query = delete(TrackedCryptoCurrency).where(TrackedCryptoCurrency.currency == currency)
        await session.execute(query)
        logger.info(f"Removed {currency} from favourite crypto currencies")

    @transactional(read_only=True)
    async def get_non_tracked_crypto_currencies(self, *, session: AsyncSession | None = None) -> list[str]:
        tracked_currencies = await self.find_all(session=session)
        tracked_currencies = [currency.currency for currency in tracked_currencies]
        all_currencies = await self._futures_exchange_service.get_crypto_currencies()
        return [currency for currency in all_currencies if currency not in tracked_currencies]
