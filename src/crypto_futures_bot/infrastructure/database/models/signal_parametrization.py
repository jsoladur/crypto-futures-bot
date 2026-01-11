from uuid import uuid4

from sqlalchemy import UUID, Boolean, Column, Float, String, UniqueConstraint

from crypto_futures_bot.infrastructure.database.models.base import Persistable


class SignalParametrization(Persistable):
    __tablename__ = "signal_parametrization"
    __table_args__ = (UniqueConstraint("crypto_currency", name="uq_signal_parametrization"),)

    id: UUID = Column(UUID(as_uuid=True), primary_key=True, nullable=False, default=uuid4)

    crypto_currency: str = Column(String, nullable=False)
    atr_sl_mult: float = Column(Float, nullable=False)
    atr_tp_mult: float = Column(Float, nullable=False)
    long_entry_oversold_threshold: float = Column(Float, nullable=False)
    short_entry_overbought_threshold: float = Column(Float, nullable=False)
    double_confirm_trend: bool = Column(Boolean, nullable=True, default=True)
