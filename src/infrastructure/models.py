"""SQLAlchemy ORM model for the *games* table."""

from __future__ import annotations

import uuid

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database import Base


class GameModel(Base):
    __tablename__ = "games"

    game_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    estado: Mapped[str] = mapped_column(String(20), nullable=False)
    fen: Mapped[str] = mapped_column(String(100), nullable=False)