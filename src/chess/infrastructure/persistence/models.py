"""SQLAlchemy 2.0 async ORM models.

These are the persistence representations of the domain entities.
The domain models (domain/models.py) are kept separate and never
import anything from this module.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def _utcnow() -> datetime:
    return datetime.now(UTC)


class GameORM(Base):
    __tablename__ = "games"

    game_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    white_player_id: Mapped[str] = mapped_column(String(128), nullable=False)
    black_player_id: Mapped[str] = mapped_column(String(128), nullable=False)
    fen: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        Enum("waiting", "ongoing", "finished", name="game_status"),
        nullable=False,
        default="waiting",
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    moves: Mapped[list["MoveORM"]] = relationship("MoveORM", back_populates="game", order_by="MoveORM.created_at")


class MoveORM(Base):
    __tablename__ = "moves"

    move_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    game_id: Mapped[str] = mapped_column(String(36), ForeignKey("games.game_id"), nullable=False)
    player_id: Mapped[str] = mapped_column(String(128), nullable=False)
    uci: Mapped[str] = mapped_column(String(10), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    game: Mapped[GameORM] = relationship("GameORM", back_populates="moves")