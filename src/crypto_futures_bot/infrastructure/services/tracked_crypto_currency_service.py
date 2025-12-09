from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from crypto_futures_bot.infrastructure.database.models.tracked_crypto_currency import TrackedCryptoCurrency
from crypto_futures_bot.interfaces.telegram.services.vo.tracked_crypto_currency_item import TrackedCryptoCurrencyItem


class TrackedCryptoCurrencyService:
    def __init__(self, sessionmaker: async_sessionmaker) -> None:
        self._sessionmaker = sessionmaker

    async def find_all(self) -> list[TrackedCryptoCurrencyItem]:
        async with self._sessionmaker() as session:
            result = await session.execute(select(TrackedCryptoCurrency))
            entities = result.scalars().all()
            return [TrackedCryptoCurrencyItem(currency=entity.currency) for entity in entities]
