"""create games table

Revision ID: 0001
Revises:
Create Date: 2024-07-28 00:00:00.000000

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "games",
        sa.Column("game_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("estado", sa.String(length=20), nullable=False),
        sa.Column("fen", sa.String(length=100), nullable=False),
        sa.PrimaryKeyConstraint("game_id"),
    )


def downgrade() -> None:
    op.drop_table("games")