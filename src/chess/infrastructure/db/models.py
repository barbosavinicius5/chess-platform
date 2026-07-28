from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class GameModel(Base):
    __tablename__ = "games"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    status: Mapped[str] = mapped_column(String, nullable=False)
    white_player_id: Mapped[str] = mapped_column(String, nullable=False)
    black_player_id: Mapped[str | None] = mapped_column(String, nullable=True)
    fen: Mapped[str] = mapped_column(String, nullable=False)
    turn: Mapped[str] = mapped_column(String, nullable=False)

    moves: Mapped[list[MoveModel]] = relationship(
        "MoveModel",
        back_populates="game",
        order_by="MoveModel.order",
        lazy="selectin",
    )


class MoveModel(Base):
    __tablename__ = "moves"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    game_id: Mapped[str] = mapped_column(String, ForeignKey("games.id"), nullable=False)
    san: Mapped[str] = mapped_column(String, nullable=False)
    order: Mapped[int] = mapped_column(Integer, nullable=False)

    game: Mapped[GameModel] = relationship("GameModel", back_populates="moves")