from dataclasses import dataclass


@dataclass(frozen=True, kw_only=True)
class AccountInfo:
    currency_code: str
