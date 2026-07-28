"""Modelos SQLAlchemy 2.0 para a chess-platform."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class GameModel(Base):
    __tablename__ = "games"

    game_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="waiting")
    fen_atual: Mapped[str] = mapped_column(Text, nullable=False)
    turno: Mapped[str] = mapped_column(String(10), nullable=False, default="brancas")
    lado_jogador_branco: Mapped[str] = mapped_column(String(36), nullable=False)
    lado_jogador_preto: Mapped[str] = mapped_column(String(36), nullable=False)
    historico_lances: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    condicao_fim: Mapped[str | None] = mapped_column(String(50), nullable=True)

    moves: Mapped[list[MoveModel]] = relationship("MoveModel", back_populates="game", cascade="all, delete-orphan")


class MoveModel(Base):
    __tablename__ = "moves"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    game_id: Mapped[str] = mapped_column(String(36), ForeignKey("games.game_id"), nullable=False)
    san: Mapped[str] = mapped_column(String(20), nullable=False)
    fen_resultante: Mapped[str] = mapped_column(Text, nullable=False)
    jogador: Mapped[str] = mapped_column(String(36), nullable=False)
    numero_lance: Mapped[int] = mapped_column(Integer, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    game: Mapped[GameModel] = relationship("GameModel", back_populates="moves")
