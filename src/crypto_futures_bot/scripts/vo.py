from dataclasses import dataclass

import pandas as pd

from crypto_futures_bot.domain.vo import SignalParametrizationItem


@dataclass(frozen=True, kw_only=True)
class BacktestingResult:
    signal_parametrization_item: SignalParametrizationItem
    stats: pd.Series
