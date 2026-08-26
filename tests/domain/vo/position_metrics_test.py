from crypto_futures_bot.domain.enums import PositionOpenTypeEnum, PositionTypeEnum
from crypto_futures_bot.domain.vo.position_metrics import PositionMetrics
from crypto_futures_bot.infrastructure.adapters.futures_exchange.vo import Position, SymbolMarketConfig, SymbolTicker


def _metrics(*, initial_margin: float, entry_price: float = 100.0, mark_price: float = 110.0) -> PositionMetrics:
    return PositionMetrics(
        position=Position(
            position_id="pos1",
            symbol="BTC/USDT:USDT",
            initial_margin=initial_margin,
            leverage=10,
            liquidation_price=90.0,
            open_type=PositionOpenTypeEnum.ISOLATED,
            position_type=PositionTypeEnum.LONG,
            entry_price=entry_price,
            contracts=10.0,
            contract_size=1.0,
            fee=0.0,
        ),
        symbol_market_config=SymbolMarketConfig(
            symbol="BTC/USDT:USDT", price_precision=2, amount_precision=0, contract_size=1.0, max_leverage=125
        ),
        ticker=SymbolTicker(
            timestamp=1, symbol="BTC/USDT:USDT", close=mark_price, bid=mark_price, ask=mark_price, mark_price=mark_price
        ),
    )


def should_return_zero_pnl_ratio_when_initial_margin_is_zero() -> None:
    assert _metrics(initial_margin=0.0).unrealised_pnl_ratio == 0.0


def should_compute_pnl_ratio_against_initial_margin() -> None:
    # PnL = (110 - 100) * 10 * 1 = 100; margin = 50 → ratio 2.0
    assert _metrics(initial_margin=50.0).unrealised_pnl_ratio == 2.0


def should_compute_unrealised_pnl_using_close_when_mark_price_is_missing() -> None:
    metrics = _metrics(initial_margin=50.0, mark_price=110.0)
    metrics.ticker = SymbolTicker(
        timestamp=1, symbol="BTC/USDT:USDT", close=110.0, bid=109.0, ask=111.0, mark_price=None
    )
    assert metrics.unrealised_pnl == 100.0
