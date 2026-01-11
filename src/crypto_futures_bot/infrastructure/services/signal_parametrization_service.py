from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from crypto_futures_bot.domain.vo.signal_parametrization_item import SignalParametrizationItem
from crypto_futures_bot.infrastructure.database.models.signal_parametrization import SignalParametrization
from crypto_futures_bot.infrastructure.services.decorators import transactional


class SignalParametrizationService:
    @transactional(read_only=True)
    async def find_by_crypto_currency(
        self, crypto_currency: str, *, session: AsyncSession
    ) -> SignalParametrizationItem:
        entity = await self._find_one_or_none(crypto_currency=crypto_currency, session=session)
        if entity:
            ret = SignalParametrizationItem(
                crypto_currency=entity.crypto_currency,
                atr_sl_mult=entity.atr_sl_mult,
                atr_tp_mult=entity.atr_tp_mult,
                long_entry_oversold_threshold=entity.long_entry_oversold_threshold,
                short_entry_overbought_threshold=entity.short_entry_overbought_threshold,
                double_confirm_trend=bool(entity.double_confirm_trend),
            )
        else:
            ret = SignalParametrizationItem(crypto_currency=crypto_currency)
        return ret

    @transactional()
    async def save_or_update(self, item: SignalParametrizationItem, *, session: AsyncSession) -> None:
        entity = await self._find_one_or_none(crypto_currency=item.crypto_currency, session=session)
        if entity:
            entity.atr_sl_mult = item.atr_sl_mult
            entity.atr_tp_mult = item.atr_tp_mult
            entity.long_entry_oversold_threshold = item.long_entry_oversold_threshold
            entity.short_entry_overbought_threshold = item.short_entry_overbought_threshold
            entity.double_confirm_trend = item.double_confirm_trend
        else:
            entity = SignalParametrization(
                crypto_currency=item.crypto_currency,
                atr_sl_mult=item.atr_sl_mult,
                atr_tp_mult=item.atr_tp_mult,
                long_entry_oversold_threshold=item.long_entry_oversold_threshold,
                short_entry_overbought_threshold=item.short_entry_overbought_threshold,
                double_confirm_trend=item.double_confirm_trend,
            )
            session.add(entity)
        await session.flush()

    async def _find_one_or_none(self, crypto_currency: str, *, session: AsyncSession) -> SignalParametrization | None:
        query = select(SignalParametrization).where(SignalParametrization.crypto_currency == crypto_currency)
        query_result = await session.execute(query)
        entity: SignalParametrization | None = query_result.scalars().one_or_none()
        return entity
