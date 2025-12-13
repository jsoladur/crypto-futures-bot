from abc import ABCMeta
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import DeclarativeMeta, as_declarative, declarative_base, declared_attr


class _DeclarativeABCMeta(DeclarativeMeta, ABCMeta):
    pass


@as_declarative()
class Persistable(declarative_base(metaclass=_DeclarativeABCMeta)):
    __abstract__ = True
    __name__: str

    _created_at = Column("created_at", DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
    last_updated_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )

    @declared_attr
    def __tablename__(cls) -> str:
        return cls.__name__.lower()

    @hybrid_property
    def created_at(self) -> datetime:
        return self._created_at

    @created_at.setter
    def created_at(self, _: datetime) -> None:
        raise AttributeError("can't set attribute 'created_at'")
