import json
from collections.abc import AsyncGenerator, Generator
from os import environ, path
from tempfile import NamedTemporaryFile
from types import ModuleType
from typing import Any
from unittest.mock import patch

import ccxt.async_support as ccxt
import pytest
from dependency_injector.containers import Container
from faker import Faker

from crypto_futures_bot.config.dependencies import get_application_container
from crypto_futures_bot.main import main

main_module: ModuleType | None = None


@pytest.fixture(scope="session", autouse=True)
def faker() -> Faker:
    return Faker()


@pytest.fixture(scope="session", autouse=True)
def defaults_env(faker: Faker) -> Generator[None]:
    with NamedTemporaryFile(suffix=".sqlite") as temp_db:
        environ["ROOT_USER"] = faker.user_name()
        environ["ROOT_PASSWORD"] = faker.password()
        environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{temp_db.name}"
        environ["MEXC_API_KEY"] = faker.uuid4()
        environ["MEXC_API_SECRET"] = faker.uuid4()
        environ["MEXC_WEB_AUTH_TOKEN"] = faker.uuid4()
        environ["TELEGRAM_BOT_ENABLED"] = "false"
        environ["TELEGRAM_BOT_TOKEN"] = f"{faker.pyint()}:{faker.uuid4().replace('-', '_')}"
        environ["LOGIN_ENABLED"] = "false"
        # environ["FUTURES_EXCHANGE_DEBUG_MODE"] = "true"
        yield


@pytest.fixture
async def test_environment() -> AsyncGenerator[tuple[Container, ...]]:
    # XXX: Disable background tasks
    environ["BACKGROUND_TASKS_ENABLED"] = "false"
    with (
        patch.object(ccxt.mexc, "fetch_currencies", return_value=_load_mexc_resource_file("fetch_currencies.json")),
        patch.object(ccxt.mexc, "fetch_spot_markets", return_value=_load_mexc_resource_file("fetch_spot_markets.json")),
        patch.object(ccxt.mexc, "fetch_swap_markets", return_value=_load_mexc_resource_file("fetch_swap_markets.json")),
    ):
        await main()
        application_container = get_application_container()
        yield (application_container,)
        # Cleanup
        application_container.reset_singletons()


def _load_mexc_resource_file(filename: str) -> dict[str, Any] | list[dict[str, Any]]:
    mexc_resources_folder = path.realpath(path.join(path.dirname(__file__), "helpers", "resources", "mexc"))
    with open(path.join(mexc_resources_folder, filename)) as fd:
        ret = json.loads(fd.read())
    return ret
