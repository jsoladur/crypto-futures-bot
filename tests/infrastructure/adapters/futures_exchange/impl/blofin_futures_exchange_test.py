import asyncio
from unittest.mock import AsyncMock, patch

import ccxt.async_support as ccxt
import pytest

from crypto_futures_bot.config.configuration_properties import ConfigurationProperties
from crypto_futures_bot.domain.enums import PositionOpenTypeEnum, PositionTypeEnum
from crypto_futures_bot.infrastructure.adapters.futures_exchange.impl.blofin_futures_exchange import (
    BloFinFuturesExchangeService,
)
from crypto_futures_bot.infrastructure.adapters.futures_exchange.vo import CreateMarketPositionOrder, Position

pytestmark = pytest.mark.asyncio


def _build_config(**overrides) -> ConfigurationProperties:
    return ConfigurationProperties(
        root_user="user",
        root_password="pass",
        telegram_bot_token="123:abc",
        database_url="sqlite+aiosqlite:///:memory:",
        blofin_api_key=overrides.get("blofin_api_key", "key"),
        blofin_api_secret=overrides.get("blofin_api_secret", "secret"),
        blofin_api_passphrase=overrides.get("blofin_api_passphrase", "passphrase"),
    )


async def should_raise_when_credentials_missing() -> None:
    config = _build_config(blofin_api_key=None)
    with pytest.raises(ValueError, match="BloFin API key"):
        BloFinFuturesExchangeService(config)


async def should_return_account_info() -> None:
    service = BloFinFuturesExchangeService(_build_config())
    account_info = await service.get_account_info()
    assert account_info.currency_code == "USDT"


async def should_load_markets_on_post_init() -> None:
    service = BloFinFuturesExchangeService(_build_config())
    with patch.object(ccxt.blofin, "load_markets", new_callable=AsyncMock) as mock_load:
        await service.post_init()
    assert mock_load.call_count == 2


async def should_return_portfolio_balance() -> None:
    service = BloFinFuturesExchangeService(_build_config())
    service._spot_client.fetch_balance = AsyncMock(return_value={"total": {"USDT": 1000.0, "BTC": 0.5}, "info": {}})
    service._spot_client.fetch_tickers = AsyncMock(return_value={"BTC/USDT": {"last": 40000.0}})
    service._futures_client.fetch_balance = AsyncMock(
        return_value={"total": {"USDT": 500.0}, "free": {"USDT": 300.0}, "used": {"USDT": 200.0}, "info": {}}
    )
    balance = await service.get_portfolio_balance()
    assert balance.spot_balance == 21000.0
    assert balance.futures_balance == 500.0


async def should_return_futures_wallet() -> None:
    service = BloFinFuturesExchangeService(_build_config())
    service._futures_client.fetch_balance = AsyncMock(
        return_value={
            "total": {"USDT": 1000.0},
            "free": {"USDT": 800.0},
            "used": {"USDT": 200.0},
            "info": {
                "data": {
                    "details": [
                        {"currency": "USDT", "equity": "1000.0", "available": "800.0", "isolatedUnrealizedPnl": "50.0"}
                    ]
                }
            },
        }
    )
    wallet = await service.get_futures_wallet()
    assert wallet.currency == "USDT"
    assert wallet.equity == 1000.0
    assert wallet.available_balance == 800.0
    assert wallet.position_margin == 200.0
    assert wallet.unrealized_pnl == 50.0
    assert wallet.cash_balance == 950.0


async def should_return_symbol_ticker_using_info_mark_price() -> None:
    service = BloFinFuturesExchangeService(_build_config())
    service._futures_client.fetch_ticker = AsyncMock(
        return_value={
            "timestamp": 1,
            "symbol": "BTC/USDT:USDT",
            "close": 100.0,
            "bid": 99.0,
            "ask": 101.0,
            "info": {"markPrice": "100.5"},
        }
    )
    ticker = await service.get_symbol_ticker("BTC/USDT:USDT")
    assert ticker.mark_price == 100.5


async def should_return_symbol_ticker_using_fetch_mark_price_fallback() -> None:
    service = BloFinFuturesExchangeService(_build_config())
    service._futures_client.fetch_ticker = AsyncMock(
        return_value={"timestamp": 1, "symbol": "BTC/USDT:USDT", "close": 100.0, "bid": 99.0, "ask": 101.0, "info": {}}
    )
    service._futures_client.fetch_mark_price = AsyncMock(
        return_value={
            "timestamp": 1,
            "symbol": "BTC/USDT:USDT",
            "close": 100.0,
            "bid": 99.0,
            "ask": 101.0,
            "markPrice": 100.5,
            "info": {"instId": "BTC-USDT", "markPrice": "100.5"},
        }
    )
    ticker = await service.get_symbol_ticker("BTC/USDT:USDT")
    assert ticker.mark_price == 100.5
    service._futures_client.fetch_mark_price.assert_called_once_with("BTC/USDT:USDT", params={"instId": "BTC-USDT"})


async def should_ignore_mark_price_from_a_different_symbol() -> None:
    service = BloFinFuturesExchangeService(_build_config())
    service._futures_client.fetch_ticker = AsyncMock(
        return_value={
            "timestamp": 1,
            "symbol": "XRP/USDT:USDT",
            "close": 1.446,
            "last": 1.446,
            "bid": 1.445,
            "ask": 1.446,
            "info": {"instId": "XRP-USDT"},
        }
    )
    service._futures_client.fetch_mark_price = AsyncMock(
        return_value={
            "timestamp": 1,
            "symbol": "BTC/USDT:USDT",
            "close": 80354.5,
            "last": 80354.5,
            "markPrice": 80354.5,
            "info": {"instId": "BTC-USDT", "markPrice": "80354.5"},
        }
    )
    ticker = await service.get_symbol_ticker("XRP/USDT:USDT")
    assert ticker.mark_price == 1.446
    service._futures_client.fetch_mark_price.assert_called_once_with("XRP/USDT:USDT", params={"instId": "XRP-USDT"})


async def should_return_symbol_tickers() -> None:
    service = BloFinFuturesExchangeService(_build_config())
    service._futures_client.fetch_tickers = AsyncMock(
        return_value={
            "BTC/USDT:USDT": {
                "timestamp": 1,
                "symbol": "BTC/USDT:USDT",
                "close": 100.0,
                "bid": 99.0,
                "ask": 101.0,
                "info": {"markPrice": "100.5"},
            }
        }
    )
    tickers = await service.get_symbol_tickers(symbols=["BTC/USDT:USDT"])
    assert len(tickers) == 1
    assert tickers[0].mark_price == 100.5


async def should_fallback_mark_price_to_last_close_when_missing_from_tickers() -> None:
    service = BloFinFuturesExchangeService(_build_config())
    service._futures_client.fetch_tickers = AsyncMock(
        return_value={
            "BTC/USDT:USDT": {
                "timestamp": 1,
                "symbol": "BTC/USDT:USDT",
                "close": 100.0,
                "last": 100.0,
                "bid": 99.0,
                "ask": 101.0,
                "info": {},
            }
        }
    )
    tickers = await service.get_symbol_tickers(symbols=["BTC/USDT:USDT"])
    assert tickers[0].mark_price == 100.0


async def should_return_crypto_currencies() -> None:
    service = BloFinFuturesExchangeService(_build_config())
    service._futures_client.markets = {"BTC/USDT:USDT": {"base": "BTC", "quote": "USDT", "active": True, "swap": True}}
    currencies = await service.get_crypto_currencies()
    assert currencies == ["BTC"]


async def should_fetch_ohlcv() -> None:
    service = BloFinFuturesExchangeService(_build_config())
    expected = [[1, 2, 3, 4, 5, 6]]
    service._futures_client.fetch_ohlcv = AsyncMock(return_value=expected)
    ohlcv = await service.fetch_ohlcv("BTC/USDT:USDT")
    assert ohlcv == expected


async def should_return_symbol_market_config() -> None:
    service = BloFinFuturesExchangeService(_build_config())
    service._futures_client.markets = {
        "BTC/USDT:USDT": {
            "base": "BTC",
            "quote": "USDT",
            "active": True,
            "swap": True,
            "symbol": "BTC/USDT:USDT",
            "contractSize": 0.001,
            "info": {"tickSize": "0.1", "lotSize": "0.001", "maxLeverage": "125"},
        }
    }
    config = await service.get_symbol_market_config("BTC")
    assert config.symbol == "BTC/USDT:USDT"
    assert config.price_precision == 1
    assert config.amount_precision == 3
    assert config.contract_size == 0.001
    assert config.max_leverage == 125


async def should_raise_for_unknown_symbol_market_config() -> None:
    service = BloFinFuturesExchangeService(_build_config())
    service._futures_client.markets = {}
    with pytest.raises(ValueError, match="Future market not found"):
        await service.get_symbol_market_config("UNKNOWN")


async def should_return_open_positions() -> None:
    service = BloFinFuturesExchangeService(_build_config())
    service._futures_client.fetch_open_orders = AsyncMock(return_value=[])
    service._futures_client.fetch_positions = AsyncMock(
        return_value=[
            {
                "symbol": "BTC/USDT:USDT",
                "side": "long",
                "marginMode": "isolated",
                "initialMargin": 100.0,
                "leverage": 10,
                "liquidationPrice": 90.0,
                "entryPrice": 100.0,
                "contracts": 1.0,
                "contractSize": 0.001,
                "info": {"positionId": "123", "instId": "BTC-USDT", "positionSide": "net"},
            }
        ]
    )
    positions = await service.get_open_positions()
    assert len(positions) == 1
    assert positions[0].position_id == "123"
    assert positions[0].position_type == PositionTypeEnum.LONG


async def should_map_isolated_position_margin_from_collateral() -> None:
    service = BloFinFuturesExchangeService(_build_config())
    service._futures_client.fetch_open_orders = AsyncMock(return_value=[])
    service._futures_client.fetch_positions = AsyncMock(
        return_value=[
            {
                "symbol": "ETH/USDT:USDT",
                "side": "long",
                "marginMode": "isolated",
                "initialMargin": None,
                "collateral": 53.06,
                "leverage": 3,
                "liquidationPrice": 1066.1,
                "entryPrice": 1591.8,
                "contracts": 1.0,
                "contractSize": 0.1,
                "info": {"positionId": "7982", "instId": "ETH-USDT", "positionSide": "net", "margin": "53.06"},
            }
        ]
    )
    positions = await service.get_open_positions()
    assert positions[0].initial_margin == 53.06


async def should_derive_isolated_margin_from_notional_when_exchange_omits_it() -> None:
    service = BloFinFuturesExchangeService(_build_config())
    service._futures_client.fetch_open_orders = AsyncMock(return_value=[])
    service._futures_client.fetch_positions = AsyncMock(
        return_value=[
            {
                "symbol": "ETH/USDT:USDT",
                "side": "long",
                "marginMode": "isolated",
                "leverage": 10,
                "liquidationPrice": 90.0,
                "entryPrice": 100.0,
                "contracts": 2.0,
                "contractSize": 0.1,
                "info": {"positionId": "7983", "instId": "ETH-USDT", "positionSide": "net"},
            }
        ]
    )
    positions = await service.get_open_positions()
    assert positions[0].initial_margin == 2.0


async def should_raise_get_position_by_id() -> None:
    service = BloFinFuturesExchangeService(_build_config())
    with pytest.raises(NotImplementedError):
        await service.get_position_by_id("123")


async def should_create_long_market_position_order() -> None:
    service = BloFinFuturesExchangeService(_build_config())
    service._futures_client.fetch_ticker = AsyncMock(
        return_value={
            "timestamp": 1,
            "symbol": "BTC/USDT:USDT",
            "close": 100.0,
            "bid": 99.0,
            "ask": 101.0,
            "info": {"markPrice": "100.0"},
        }
    )
    service._futures_client.markets = {
        "BTC/USDT:USDT": {
            "base": "BTC",
            "quote": "USDT",
            "active": True,
            "swap": True,
            "symbol": "BTC/USDT:USDT",
            "contractSize": 0.001,
            "info": {"tickSize": "0.1", "lotSize": "0.001", "maxLeverage": "125"},
        }
    }
    service._futures_client.set_leverage = AsyncMock(return_value={})
    service._futures_client.create_order = AsyncMock(return_value={"id": "order1"})

    async def _mock_open_positions() -> list:
        return [
            Position(
                position_id="pos1",
                symbol="BTC/USDT:USDT",
                initial_margin=90.0,
                leverage=10,
                liquidation_price=90.0,
                open_type=PositionOpenTypeEnum.ISOLATED,
                position_type=PositionTypeEnum.LONG,
                entry_price=101.0,
                contracts=1.0,
                contract_size=0.001,
                fee=0.0,
            )
        ]

    service.get_open_positions = AsyncMock(side_effect=_mock_open_positions)

    order = CreateMarketPositionOrder(
        symbol="BTC/USDT:USDT",
        initial_margin=100.0,
        leverage=10,
        open_type=PositionOpenTypeEnum.ISOLATED,
        position_type=PositionTypeEnum.LONG,
        notional_size=1000.0,
        stop_loss_price=90.0,
        take_profit_price=120.0,
    )
    created = await service.create_market_position_order(order)
    assert created.position_id == "pos1"
    assert created.stop_loss_price == 90.0
    assert created.take_profit_price == 120.0
    service._futures_client.create_order.assert_called_once()
    order_amount = service._futures_client.create_order.call_args.kwargs["amount"]
    # 1000 USDT notional at ~101 with contractSize 0.001 ≈ 9000+ contracts, not ~9 base BTC
    assert order_amount > 1000


async def should_create_short_market_position_order() -> None:
    service = BloFinFuturesExchangeService(_build_config())
    service._futures_client.fetch_ticker = AsyncMock(
        return_value={
            "timestamp": 1,
            "symbol": "BTC/USDT:USDT",
            "close": 100.0,
            "bid": 99.0,
            "ask": 101.0,
            "info": {"markPrice": "100.0"},
        }
    )
    service._futures_client.markets = {
        "BTC/USDT:USDT": {
            "base": "BTC",
            "quote": "USDT",
            "active": True,
            "swap": True,
            "symbol": "BTC/USDT:USDT",
            "contractSize": 0.001,
            "info": {"tickSize": "0.1", "lotSize": "0.001", "maxLeverage": "125"},
        }
    }
    service._futures_client.set_leverage = AsyncMock(return_value={})
    service._futures_client.create_order = AsyncMock(return_value={"id": "order1"})

    async def _mock_open_positions() -> list:
        return [
            Position(
                position_id="pos2",
                symbol="BTC/USDT:USDT",
                initial_margin=90.0,
                leverage=10,
                liquidation_price=110.0,
                open_type=PositionOpenTypeEnum.ISOLATED,
                position_type=PositionTypeEnum.SHORT,
                entry_price=99.0,
                contracts=1.0,
                contract_size=0.001,
                fee=0.0,
            )
        ]

    service.get_open_positions = AsyncMock(side_effect=_mock_open_positions)

    order = CreateMarketPositionOrder(
        symbol="BTC/USDT:USDT",
        initial_margin=100.0,
        leverage=10,
        open_type=PositionOpenTypeEnum.ISOLATED,
        position_type=PositionTypeEnum.SHORT,
        notional_size=1000.0,
    )
    created = await service.create_market_position_order(order)
    assert created.position_id == "pos2"
    service._futures_client.create_order.assert_called_once()
    order_amount = service._futures_client.create_order.call_args.kwargs["amount"]
    assert order_amount > 1000


async def should_raise_when_position_not_found_after_order() -> None:
    service = BloFinFuturesExchangeService(_build_config())
    service._futures_client.fetch_ticker = AsyncMock(
        return_value={
            "timestamp": 1,
            "symbol": "BTC/USDT:USDT",
            "close": 100.0,
            "bid": 99.0,
            "ask": 101.0,
            "info": {"markPrice": "100.0"},
        }
    )
    service._futures_client.markets = {
        "BTC/USDT:USDT": {
            "base": "BTC",
            "quote": "USDT",
            "active": True,
            "swap": True,
            "symbol": "BTC/USDT:USDT",
            "contractSize": 1.0,
            "info": {"tickSize": "0.1", "lotSize": "1.0", "maxLeverage": "125"},
        }
    }
    service._futures_client.set_leverage = AsyncMock(return_value={})
    service._futures_client.create_order = AsyncMock(return_value={"id": "order1"})
    service.get_open_positions = AsyncMock(return_value=[])

    order = CreateMarketPositionOrder(
        symbol="BTC/USDT:USDT",
        initial_margin=100.0,
        leverage=10,
        open_type=PositionOpenTypeEnum.ISOLATED,
        position_type=PositionTypeEnum.LONG,
        notional_size=1000.0,
    )
    with (
        pytest.raises(ValueError, match="Created position not found"),
        patch.object(asyncio, "sleep", new_callable=AsyncMock),
    ):
        await service.create_market_position_order(order)


async def should_send_contract_amount_not_base_currency_for_large_contract_size() -> None:
    service = BloFinFuturesExchangeService(_build_config())
    service._futures_client.fetch_ticker = AsyncMock(
        return_value={
            "timestamp": 1,
            "symbol": "DOGE/USDT:USDT",
            "close": 0.15,
            "bid": 0.149,
            "ask": 0.15,
            "info": {"markPrice": "0.15"},
        }
    )
    service._futures_client.markets = {
        "DOGE/USDT:USDT": {
            "base": "DOGE",
            "quote": "USDT",
            "active": True,
            "swap": True,
            "symbol": "DOGE/USDT:USDT",
            "contractSize": 1000.0,
            "info": {"tickSize": "0.00001", "lotSize": "0.1", "maxLeverage": "50"},
        }
    }
    service._futures_client.set_leverage = AsyncMock(return_value={})
    service._futures_client.create_order = AsyncMock(return_value={"id": "order1"})
    service.get_open_positions = AsyncMock(
        return_value=[
            Position(
                position_id="pos-doge",
                symbol="DOGE/USDT:USDT",
                initial_margin=30.0,
                leverage=5,
                liquidation_price=0.12,
                open_type=PositionOpenTypeEnum.ISOLATED,
                position_type=PositionTypeEnum.LONG,
                entry_price=0.15,
                contracts=1.0,
                contract_size=1000.0,
                fee=0.0,
            )
        ]
    )

    order = CreateMarketPositionOrder(
        symbol="DOGE/USDT:USDT",
        initial_margin=30.0,
        leverage=5,
        open_type=PositionOpenTypeEnum.ISOLATED,
        position_type=PositionTypeEnum.LONG,
        notional_size=150.0,
    )
    await service.create_market_position_order(order)

    order_amount = service._futures_client.create_order.call_args.kwargs["amount"]
    # 150 USDT / 0.15 / 1000 ≈ 1 contract. Sending base DOGE (~1000) would 1000x-oversize.
    assert 0.1 <= order_amount <= 2.0
    assert service._futures_client.create_order.call_args.kwargs["params"]["positionSide"] == "net"


async def should_raise_when_calculated_contract_amount_is_zero() -> None:
    service = BloFinFuturesExchangeService(_build_config())
    service._futures_client.fetch_ticker = AsyncMock(
        return_value={
            "timestamp": 1,
            "symbol": "BTC/USDT:USDT",
            "close": 100_000.0,
            "bid": 99_999.0,
            "ask": 100_000.0,
            "info": {"markPrice": "100000.0"},
        }
    )
    service._futures_client.markets = {
        "BTC/USDT:USDT": {
            "base": "BTC",
            "quote": "USDT",
            "active": True,
            "swap": True,
            "symbol": "BTC/USDT:USDT",
            "contractSize": 0.001,
            "info": {"tickSize": "0.1", "lotSize": "1.0", "maxLeverage": "125"},
        }
    }

    order = CreateMarketPositionOrder(
        symbol="BTC/USDT:USDT",
        initial_margin=0.01,
        leverage=1,
        open_type=PositionOpenTypeEnum.ISOLATED,
        position_type=PositionTypeEnum.LONG,
        notional_size=0.01,
    )
    with pytest.raises(ValueError, match="order size is 0"):
        await service.create_market_position_order(order)


async def should_return_taker_fee() -> None:
    service = BloFinFuturesExchangeService(_build_config())
    assert service.get_taker_fee() == 0.0006


async def should_map_open_position_with_tpsl_orders() -> None:
    service = BloFinFuturesExchangeService(_build_config())
    service._futures_client.fetch_open_orders = AsyncMock(
        return_value=[
            {
                "symbol": "BTC/USDT:USDT",
                "info": {"positionSide": "net", "tpTriggerPrice": "120.0"},
                "takeProfitTriggerPrice": 120.0,
            },
            {
                "symbol": "BTC/USDT:USDT",
                "info": {"positionSide": "net", "slTriggerPrice": "90.0"},
                "stopLossTriggerPrice": 90.0,
            },
        ]
    )
    service._futures_client.fetch_positions = AsyncMock(
        return_value=[
            {
                "symbol": "BTC/USDT:USDT",
                "side": "long",
                "marginMode": "cross",
                "initialMargin": 100.0,
                "leverage": 10,
                "liquidationPrice": 90.0,
                "entryPrice": 100.0,
                "contracts": 1.0,
                "contractSize": 0.001,
                "info": {"positionId": "pos3", "instId": "BTC-USDT", "positionSide": "net"},
            }
        ]
    )
    positions = await service.get_open_positions()
    assert positions[0].take_profit_price == 120.0
    assert positions[0].stop_loss_price == 90.0
    assert positions[0].open_type == PositionOpenTypeEnum.CROSS
