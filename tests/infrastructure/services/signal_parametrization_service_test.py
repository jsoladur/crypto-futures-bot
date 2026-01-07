import logging

import pytest
from dependency_injector.containers import Container
from faker import Faker

from crypto_futures_bot.domain.vo import SignalParametrizationItem
from crypto_futures_bot.infrastructure.services.signal_parametrization_service import SignalParametrizationService
from tests.helpers.constants import MOCK_CRYPTO_CURRENCIES

logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def should_save_and_find_parametrization_properly(faker: Faker, test_environment: tuple[Container, ...]) -> None:
    application_container, *_ = test_environment
    signal_parametrization_service: SignalParametrizationService = (
        application_container.infrastructure_container().services_container().signal_parametrization_service()
    )

    currency = faker.random_element(MOCK_CRYPTO_CURRENCIES)

    # Initial find
    initial_params = await signal_parametrization_service.find_by_crypto_currency(currency)
    assert initial_params.crypto_currency == currency
    # Assert default values, assuming SignalParametrizationItem has defaults
    assert initial_params.atr_sl_mult is not None

    # Save new params
    new_params = SignalParametrizationItem(
        crypto_currency=currency,
        atr_sl_mult=faker.pyfloat(min_value=1, max_value=3, right_digits=1),
        atr_tp_mult=faker.pyfloat(min_value=1, max_value=5, right_digits=1),
        long_entry_oversold_threshold=faker.pyint(min_value=20, max_value=30),
        short_entry_overbought_threshold=faker.pyint(min_value=70, max_value=80),
    )
    await signal_parametrization_service.save_or_update(new_params)

    # Find again
    updated_params = await signal_parametrization_service.find_by_crypto_currency(currency)
    assert updated_params.crypto_currency == currency
    assert updated_params.atr_sl_mult == new_params.atr_sl_mult
    assert updated_params.atr_tp_mult == new_params.atr_tp_mult
    assert updated_params.long_entry_oversold_threshold == new_params.long_entry_oversold_threshold
    assert updated_params.short_entry_overbought_threshold == new_params.short_entry_overbought_threshold
