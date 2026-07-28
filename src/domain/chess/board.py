"""Representação do tabuleiro 8x8 e parsing/geração de FEN."""

from __future__ import annotations

from src.domain.chess.models import Board, Color, Piece, PieceType, Square

# ---------------------------------------------------------------------------
# Mapeamento de símbolos FEN
# ---------------------------------------------------------------------------

_FEN_SYMBOL: dict[str, tuple[PieceType, Color]] = {
    "K": ("K", "w"),
    "Q": ("Q", "w"),
    "R": ("R", "w"),
    "B": ("B", "w"),
    "N": ("N", "w"),
    "P": ("P", "w"),
    "k": ("K", "b"),
    "q": ("Q", "b"),
    "r": ("R", "b"),
    "b": ("B", "b"),
    "n": ("N", "b"),
    "p": ("P", "b"),
}

_PIECE_TO_FEN: dict[tuple[PieceType, Color], str] = {v: k for k, v in _FEN_SYMBOL.items()}


# ---------------------------------------------------------------------------
# Conversões de coordenadas
# ---------------------------------------------------------------------------


def sq_to_name(sq: Square) -> str:
    """Converte índice 0-63 para nome de casa (ex.: 0 → 'a1')."""
    col = sq % 8
    row = sq // 8
    return f"{chr(ord('a') + col)}{row + 1}"


def name_to_sq(name: str) -> Square:
    """Converte nome de casa para índice 0-63 (ex.: 'e4' → 28)."""
    col = ord(name[0]) - ord("a")
    row = int(name[1]) - 1
    return row * 8 + col


def sq_col(sq: Square) -> int:
    return sq % 8


def sq_row(sq: Square) -> int:
    return sq // 8


# ---------------------------------------------------------------------------
# Parsing de FEN
# ---------------------------------------------------------------------------


def parse_fen(fen: str) -> Board:
    """Converte string FEN em Board. Levanta ValueError em FEN inválido."""
    parts = fen.strip().split()
    if len(parts) != 6:
        raise ValueError(f"FEN inválido (esperados 6 campos, recebido {len(parts)}): {fen!r}")

    pos_part, side_part, castling_part, ep_part, half_part, full_part = parts

    # --- posição ---
    squares: list[Piece | None] = [None] * 64
    rows = pos_part.split("/")
    if len(rows) != 8:
        raise ValueError(f"FEN: posição deve ter 8 fileiras, recebido {len(rows)}")

    for rank_idx, row_str in enumerate(reversed(rows)):  # row 0 = rank 1 (a1..h1)
        col = 0
        for ch in row_str:
            if ch.isdigit():
                col += int(ch)
            elif ch in _FEN_SYMBOL:
                piece_type, color = _FEN_SYMBOL[ch]
                sq = rank_idx * 8 + col
                squares[sq] = Piece(piece_type, color)
                col += 1
            else:
                raise ValueError(f"FEN: caractere inválido na posição: {ch!r}")
        if col != 8:
            raise ValueError(f"FEN: fileira {rank_idx + 1} tem {col} colunas (esperado 8)")

    # --- lado a jogar ---
    if side_part not in ("w", "b"):
        raise ValueError(f"FEN: lado inválido {side_part!r}")
    active_color: Color = side_part  # type: ignore[assignment]

    # --- direitos de roque ---
    if not _valid_castling(castling_part):
        raise ValueError(f"FEN: direitos de roque inválidos {castling_part!r}")
    castling_rights = castling_part

    # --- en passant ---
    en_passant_square: Square | None = None
    if ep_part != "-":
        if len(ep_part) != 2 or ep_part[0] not in "abcdefgh" or ep_part[1] not in "36":
            raise ValueError(f"FEN: casa en passant inválida {ep_part!r}")
        en_passant_square = name_to_sq(ep_part)

    # --- contadores ---
    try:
        halfmove_clock = int(half_part)
        fullmove_number = int(full_part)
    except ValueError as exc:
        raise ValueError(f"FEN: contadores inválidos {half_part!r} {full_part!r}") from exc

    return Board(
        squares=squares,
        active_color=active_color,
        castling_rights=castling_rights,
        en_passant_square=en_passant_square,
        halfmove_clock=halfmove_clock,
        fullmove_number=fullmove_number,
    )


def _valid_castling(s: str) -> bool:
    if s == "-":
        return True
    allowed = set("KQkq")
    return all(c in allowed for c in s) and len(s) == len(set(s))


# ---------------------------------------------------------------------------
# Geração de FEN
# ---------------------------------------------------------------------------


def board_to_fen(board: Board) -> str:
    """Converte Board em string FEN."""
    # --- posição ---
    rows: list[str] = []
    for rank in range(7, -1, -1):  # rank 8 first
        empty = 0
        row_str = ""
        for col in range(8):
            sq = rank * 8 + col
            piece = board.squares[sq]
            if piece is None:
                empty += 1
            else:
                if empty:
                    row_str += str(empty)
                    empty = 0
                row_str += _PIECE_TO_FEN[(piece.piece_type, piece.color)]
        if empty:
            row_str += str(empty)
        rows.append(row_str)
    pos_part = "/".join(rows)

    # --- lado ---
    side_part = board.active_color

    # --- direitos de roque ---
    castling_part = board.castling_rights if board.castling_rights else "-"

    # --- en passant ---
    ep_part = sq_to_name(board.en_passant_square) if board.en_passant_square is not None else "-"

    return f"{pos_part} {side_part} {castling_part} {ep_part} {board.halfmove_clock} {board.fullmove_number}"
