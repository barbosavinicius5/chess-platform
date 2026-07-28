"""Parsing de SAN (Standard Algebraic Notation) e geração de SAN normalizado."""

from __future__ import annotations

import re

from src.domain.chess.board import name_to_sq, sq_col, sq_row
from src.domain.chess.models import Board, Color, Move, Piece, PieceType, Square

# ---------------------------------------------------------------------------
# Regex para SAN
# ---------------------------------------------------------------------------

# Roque
_RE_CASTLE = re.compile(r"^(O-O-O|O-O)[+#]?$")

# SAN de peão ou peça
_RE_MOVE = re.compile(
    r"^(?P<piece>[KQRBN])?"
    r"(?P<from_file>[a-h])?"
    r"(?P<from_rank>[1-8])?"
    r"(?P<capture>x)?"
    r"(?P<dest_file>[a-h])"
    r"(?P<dest_rank>[1-8])"
    r"(?:=(?P<promo>[QRBN]))?"
    r"(?P<check>[+#])?$"
)


class SANParseError(ValueError):
    """Erro ao interpretar SAN."""


def parse_san(san: str) -> dict[str, object]:
    """
    Interpreta um lance SAN e retorna um dicionário com os campos extraídos.

    Returns:
        Dict com: is_castle, castle_side, piece, from_file, from_rank,
                  is_capture, dest_sq, promotion, check
    """
    san = san.strip()

    # Roque
    m = _RE_CASTLE.match(san)
    if m:
        side = "Q" if san.startswith("O-O-O") else "K"
        last = san[-1]
        return {
            "is_castle": True,
            "castle_side": side,
            "piece": "K",
            "from_file": None,
            "from_rank": None,
            "is_capture": False,
            "dest_sq": -1,
            "promotion": None,
            "check": last if last in ("+", "#") else None,
        }

    m2 = _RE_MOVE.match(san)
    if not m2:
        raise SANParseError(f"SAN inválido: {san!r}")

    piece_str = m2.group("piece")
    piece: PieceType = piece_str if piece_str else "P"  # type: ignore[assignment]

    from_file_str = m2.group("from_file")
    from_rank_str = m2.group("from_rank")
    from_file: int | None = (ord(from_file_str) - ord("a")) if from_file_str else None
    from_rank: int | None = (int(from_rank_str) - 1) if from_rank_str else None

    is_capture = m2.group("capture") == "x"

    dest_sq = name_to_sq(m2.group("dest_file") + m2.group("dest_rank"))

    promo_str = m2.group("promo")
    promotion: PieceType | None = promo_str if promo_str else None  # type: ignore[assignment]

    check_str = m2.group("check")

    return {
        "is_castle": False,
        "castle_side": None,
        "piece": piece,
        "from_file": from_file,
        "from_rank": from_rank,
        "is_capture": is_capture,
        "dest_sq": dest_sq,
        "promotion": promotion,
        "check": check_str,
    }


# ---------------------------------------------------------------------------
# Geração de SAN normalizado
# ---------------------------------------------------------------------------


def generate_san(
    board_before: Board,
    move: Move,
    legal_moves: list[Move],
    board_after: Board,
    color: Color,
) -> str:
    """Gera o SAN canônico de um lance já validado."""
    from src.domain.chess.pieces import is_in_check  # local import para evitar ciclo

    # Roque
    if move.move_type == "roque":
        king_col_after = sq_col(move.to_sq)
        if king_col_after == 6:
            base = "O-O"
        else:
            base = "O-O-O"
        opponent: Color = "b" if color == "w" else "w"
        if is_in_check(board_after, opponent):
            from src.domain.chess.move_validator import get_all_legal_moves  # noqa: PLC0415

            opp_moves = get_all_legal_moves(board_after, opponent)
            base += "#" if not opp_moves else "+"
        return base

    piece = board_before.get(move.from_sq)
    assert piece is not None

    piece_letter: str = "" if piece.piece_type == "P" else piece.piece_type

    # Desambiguação
    disambig = _disambiguation(board_before, move, legal_moves, piece)

    # Captura
    target = board_before.get(move.to_sq)
    is_capture = target is not None or move.move_type == "en_passant"
    capture_str = "x" if is_capture else ""

    # Para peão capturando: incluir coluna de origem
    if piece.piece_type == "P" and is_capture:
        from_col_letter = chr(ord("a") + sq_col(move.from_sq))
        piece_letter = from_col_letter
        disambig = ""

    dest = _sq_to_san_name(move.to_sq)

    promo_str = f"={move.promotion}" if move.promotion else ""

    # Xeque/mate
    opponent2: Color = "b" if color == "w" else "w"
    check_str = ""
    if is_in_check(board_after, opponent2):
        from src.domain.chess.move_validator import get_all_legal_moves  # noqa: PLC0415

        opp_moves = get_all_legal_moves(board_after, opponent2)
        check_str = "#" if not opp_moves else "+"

    return f"{piece_letter}{disambig}{capture_str}{dest}{promo_str}{check_str}"


def _sq_to_san_name(sq: Square) -> str:
    col = sq % 8
    row = sq // 8
    return f"{chr(ord('a') + col)}{row + 1}"


def _disambiguation(board: Board, move: Move, legal_moves: list[Move], piece: Piece) -> str:
    """Retorna string de desambiguação (ex: 'b', '1', 'b1') ou '' se desnecessário."""
    candidates = [
        m for m in legal_moves if m.to_sq == move.to_sq and m.from_sq != move.from_sq and board.get(m.from_sq) == piece
    ]
    if not candidates:
        return ""

    from_col = sq_col(move.from_sq)
    from_row = sq_row(move.from_sq)

    col_unique = all(sq_col(m.from_sq) != from_col for m in candidates)
    if col_unique:
        return chr(ord("a") + from_col)

    row_unique = all(sq_row(m.from_sq) != from_row for m in candidates)
    if row_unique:
        return str(from_row + 1)

    return f"{chr(ord('a') + from_col)}{from_row + 1}"
