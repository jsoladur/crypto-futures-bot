from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from crypto_futures_bot.infrastructure.adapters.futures_exchange.base import AbstractFuturesExchangeService
from crypto_futures_bot.infrastructure.database.models.tracked_crypto_currency import TrackedCryptoCurrency
from crypto_futures_bot.interfaces.telegram.services.vo.tracked_crypto_currency_item import TrackedCryptoCurrencyItem


class TrackedCryptoCurrencyService:
    def __init__(
        self, sessionmaker: async_sessionmaker, futures_exchange_service: AbstractFuturesExchangeService
    ) -> None:
        self._sessionmaker = sessionmaker
        self._futures_exchange_service = futures_exchange_service

    async def find_all(self) -> list[TrackedCryptoCurrencyItem]:
        async with self._sessionmaker() as session:
            result = await session.execute(select(TrackedCryptoCurrency))
            entities = result.scalars().all()
            return [TrackedCryptoCurrencyItem(currency=entity.currency) for entity in entities]

    async def get_non_tracked_crypto_currencies(self) -> list[str]:
        tracked_currencies = await self.find_all()
        tracked_currencies = [currency.currency for currency in tracked_currencies]
        all_currencies = await self._futures_exchange_service.get_trading_crypto_currencies()
        return [currency for currency in all_currencies if currency not in tracked_currencies]
