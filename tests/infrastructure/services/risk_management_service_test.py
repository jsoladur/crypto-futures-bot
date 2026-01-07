import logging

import pytest
from dependency_injector.containers import Container
from faker import Faker

from crypto_futures_bot.domain.vo import RiskManagementItem
from crypto_futures_bot.infrastructure.services.risk_management_service import RiskManagementService

logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def should_update_and_get_risk_management_settings_properly(
    faker: Faker, test_environment: tuple[Container, ...]
) -> None:
    application_container, *_ = test_environment
    risk_management_service: RiskManagementService = (
        application_container.infrastructure_container().services_container().risk_management_service()
    )

    # Initial get
    initial_settings = await risk_management_service.get()
    assert initial_settings.percent_value is not None  # Should have a default value

    # Update
    new_value = faker.pyfloat(min_value=1, max_value=10, right_digits=2)
    new_settings = RiskManagementItem(percent_value=new_value)
    await risk_management_service.update(new_settings)

    # Get again
    updated_settings = await risk_management_service.get()
    assert updated_settings.percent_value == new_value
