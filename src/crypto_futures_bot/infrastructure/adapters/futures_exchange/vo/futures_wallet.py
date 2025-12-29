from dataclasses import dataclass


@dataclass(frozen=True, kw_only=True)
class FuturesWallet:
    currency: str
    # Total Wallet Amount (Cash + Unrealized PnL)
    equity: float
    # Total Amount Locked in Positions
    position_margin: float
    # Funds Available for New Positions/Orders
    available_balance: float
    # Hard cash balance (without floating PnL)
    cash_balance: float
    # Floating Profit/Loss
    unrealized_pnl: float
