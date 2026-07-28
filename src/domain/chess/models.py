"""Modelos de dados do domínio de xadrez."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

# ---------------------------------------------------------------------------
# Tipos primitivos
# ---------------------------------------------------------------------------

type Color = Literal["w", "b"]
type PieceType = Literal["K", "Q", "R", "B", "N", "P"]
type Square = int  # 0-63, row-major: a1=0, b1=1, ..., h8=63
type MoveType = Literal["normal", "roque", "en_passant", "promocao"]

PIECE_TYPES: tuple[str, ...] = ("K", "Q", "R", "B", "N", "P")
PROMOTABLE: tuple[str, ...] = ("Q", "R", "B", "N")


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Piece:
    """Peça de xadrez."""

    piece_type: PieceType
    color: Color

    def __str__(self) -> str:
        symbol = self.piece_type if self.color == "w" else self.piece_type.lower()
        return symbol

    @property
    def is_white(self) -> bool:
        return self.color == "w"


@dataclass
class Board:
    """Representa o tabuleiro 8x8."""

    squares: list[Piece | None] = field(default_factory=lambda: [None] * 64)
    active_color: Color = "w"
    castling_rights: str = "KQkq"
    en_passant_square: Square | None = None  # square index or None
    halfmove_clock: int = 0
    fullmove_number: int = 1

    def get(self, sq: Square) -> Piece | None:
        return self.squares[sq]

    def set(self, sq: Square, piece: Piece | None) -> None:
        self.squares[sq] = piece

    def copy(self) -> Board:
        return Board(
            squares=self.squares.copy(),
            active_color=self.active_color,
            castling_rights=self.castling_rights,
            en_passant_square=self.en_passant_square,
            halfmove_clock=self.halfmove_clock,
            fullmove_number=self.fullmove_number,
        )


@dataclass(frozen=True)
class Move:
    """Representa um lance de xadrez já decodificado."""

    from_sq: Square
    to_sq: Square
    promotion: PieceType | None = None
    move_type: MoveType = "normal"


# ---------------------------------------------------------------------------
# Resultados do engine
# ---------------------------------------------------------------------------

LegalResult = dict[str, object]
IllegalResult = dict[str, object]
MoveResult = LegalResult | IllegalResult


def legal_result(
    san_normalizado: str,
    fen_resultante: str,
    lado: str,
    tipo_lance: MoveType,
) -> MoveResult:
    return {
        "legal": True,
        "san_normalizado": san_normalizado,
        "fen_resultante": fen_resultante,
        "lado": lado,
        "tipo_lance": tipo_lance,
    }


def illegal_result(razao: str) -> MoveResult:
    return {"legal": False, "razao": razao}
