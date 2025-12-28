from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from crypto_futures_bot.domain.vo.risk_management_item import RiskManagementItem
from crypto_futures_bot.infrastructure.database.models.risk_management import RiskManagement
from crypto_futures_bot.infrastructure.services.decorators import transactional


class RiskManagementService:
    @transactional(read_only=True)
    async def get(self, *, session: AsyncSession | None = None) -> RiskManagementItem:
        risk_management = await self._internal_get(session=session)
        return (
            RiskManagementItem()
            if risk_management is None
            else RiskManagementItem(percent_value=risk_management.percent_value)
        )

    @transactional()
    async def update(self, risk_management_item: RiskManagementItem, *, session: AsyncSession | None = None) -> None:
        risk_management = await self._internal_get(session=session)
        if risk_management is None:
            risk_management = RiskManagement(percent_value=risk_management_item.percent_value)
            session.add(risk_management)
        else:
            risk_management.percent_value = risk_management_item.percent_value
        await session.flush()

    async def _internal_get(self, *, session: AsyncSession) -> RiskManagement | None:
        query = select(RiskManagement).limit(1)
        query_result = await session.execute(query)
        return query_result.scalars().one_or_none()
