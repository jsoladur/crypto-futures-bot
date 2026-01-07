import logging

import pytest
from dependency_injector.containers import Container
from faker import Faker

from crypto_futures_bot.infrastructure.services.tracked_crypto_currency_service import TrackedCryptoCurrencyService
from tests.helpers.constants import MOCK_CRYPTO_CURRENCIES

logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def should_add_and_remove_tracked_crypto_currencies_properly(
    faker: Faker, test_environment: tuple[Container, ...]
) -> None:
    application_container, *_ = test_environment

    tracked_crypto_currency_service: TrackedCryptoCurrencyService = (
        application_container.infrastructure_container().services_container().tracked_crypto_currency_service()
    )

    tracked_crypto_currencies = await tracked_crypto_currency_service.find_all()
    assert len(tracked_crypto_currencies) == 0

    expected = faker.random_element(MOCK_CRYPTO_CURRENCIES)

    await tracked_crypto_currency_service.add(expected)

    tracked_crypto_currencies = await tracked_crypto_currency_service.find_all()
    assert len(tracked_crypto_currencies) > 0

    inserted, *_ = tracked_crypto_currencies
    assert inserted.currency == expected

    non_tracked_crypto_currencies = await tracked_crypto_currency_service.get_non_tracked_crypto_currencies()
    assert inserted.currency not in non_tracked_crypto_currencies

    await tracked_crypto_currency_service.remove(expected)

    tracked_crypto_currencies = await tracked_crypto_currency_service.find_all()
    assert len(tracked_crypto_currencies) == 0

    non_tracked_crypto_currencies = await tracked_crypto_currency_service.get_non_tracked_crypto_currencies()
    assert inserted.currency in non_tracked_crypto_currencies
