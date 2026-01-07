import logging

import pytest
from dependency_injector.containers import Container
from faker import Faker

from crypto_futures_bot.infrastructure.services.auto_trader_crypto_currency_service import (
    AutoTraderCryptoCurrencyService,
)
from crypto_futures_bot.infrastructure.services.tracked_crypto_currency_service import TrackedCryptoCurrencyService
from tests.helpers.constants import MOCK_CRYPTO_CURRENCIES

logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def should_toggle_auto_trader_for_a_crypto_currency_properly(
    faker: Faker, test_environment: tuple[Container, ...]
) -> None:
    application_container, *_ = test_environment

    auto_trader_crypto_currency_service: AutoTraderCryptoCurrencyService = (
        application_container.infrastructure_container().services_container().auto_trader_crypto_currency_service()
    )
    tracked_crypto_currency_service: TrackedCryptoCurrencyService = (
        application_container.infrastructure_container().services_container().tracked_crypto_currency_service()
    )

    crypto_currency = faker.random_element(MOCK_CRYPTO_CURRENCIES)

    await tracked_crypto_currency_service.add(crypto_currency)

    all_items = await auto_trader_crypto_currency_service.find_all()
    assert len(all_items) > 0
    item, *_ = [item for item in all_items if item.currency == crypto_currency]
    assert not item.activated

    is_enabled = await auto_trader_crypto_currency_service.is_enabled_for(crypto_currency)
    assert not is_enabled

    await auto_trader_crypto_currency_service.toggle_for(crypto_currency)

    is_enabled = await auto_trader_crypto_currency_service.is_enabled_for(crypto_currency)
    assert is_enabled

    all_items = await auto_trader_crypto_currency_service.find_all()
    item, *_ = [item for item in all_items if item.currency == crypto_currency]
    assert item.activated

    await auto_trader_crypto_currency_service.toggle_for(crypto_currency)

    is_enabled = await auto_trader_crypto_currency_service.is_enabled_for(crypto_currency)
    assert not is_enabled

    all_items = await auto_trader_crypto_currency_service.find_all()
    item, *_ = [item for item in all_items if item.currency == crypto_currency]
    assert not item.activated

    await tracked_crypto_currency_service.remove(crypto_currency)
