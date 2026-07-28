"""Regras de movimento de cada tipo de peça."""

from __future__ import annotations

from collections.abc import Callable

from src.domain.chess.board import sq_col, sq_row
from src.domain.chess.models import Board, Color, Move, Piece, PieceType, Square

_PROMO_PIECES: tuple[PieceType, ...] = ("Q", "R", "B", "N")

# ---------------------------------------------------------------------------
# Helpers de geometria
# ---------------------------------------------------------------------------


def _ray_squares(from_sq: Square, dr: int, dc: int) -> list[Square]:
    """Retorna lista de casas em uma direção (dr=delta row, dc=delta col), parando na borda."""
    squares: list[Square] = []
    r, c = sq_row(from_sq), sq_col(from_sq)
    while True:
        r += dr
        c += dc
        if not (0 <= r <= 7 and 0 <= c <= 7):
            break
        squares.append(r * 8 + c)
    return squares


def _sliding_moves(board: Board, from_sq: Square, directions: list[tuple[int, int]], color: Color) -> list[Move]:
    """Gera movimentos de peça deslizante (torre, bispo, dama)."""
    moves: list[Move] = []
    for dr, dc in directions:
        for sq in _ray_squares(from_sq, dr, dc):
            target = board.get(sq)
            if target is None:
                moves.append(Move(from_sq, sq))
            elif target.color != color:
                moves.append(Move(from_sq, sq))  # captura
                break
            else:
                break  # bloqueada por peça própria
    return moves


# ---------------------------------------------------------------------------
# Geração de pseudolances por tipo de peça
# ---------------------------------------------------------------------------


def pawn_pseudo_moves(board: Board, from_sq: Square, color: Color) -> list[Move]:
    """Pseudolances do peão (sem verificar xeque próprio)."""
    moves: list[Move] = []
    direction = 1 if color == "w" else -1
    start_row = 1 if color == "w" else 6
    promo_row = 7 if color == "w" else 0
    r, c = sq_row(from_sq), sq_col(from_sq)

    # Avanço simples
    nr = r + direction
    if 0 <= nr <= 7:
        fwd_sq = nr * 8 + c
        if board.get(fwd_sq) is None:
            if nr == promo_row:
                for pt in _PROMO_PIECES:
                    moves.append(Move(from_sq, fwd_sq, promotion=pt, move_type="promocao"))
            else:
                moves.append(Move(from_sq, fwd_sq))

            # Avanço duplo inicial
            if r == start_row:
                nr2 = r + 2 * direction
                fwd2_sq = nr2 * 8 + c
                if board.get(fwd2_sq) is None:
                    moves.append(Move(from_sq, fwd2_sq))

    # Capturas diagonais
    for dc in (-1, 1):
        nc = c + dc
        nr = r + direction
        if not (0 <= nr <= 7 and 0 <= nc <= 7):
            continue
        diag_sq = nr * 8 + nc
        target = board.get(diag_sq)
        if target is not None and target.color != color:
            if nr == promo_row:
                for pt in _PROMO_PIECES:
                    moves.append(Move(from_sq, diag_sq, promotion=pt, move_type="promocao"))
            else:
                moves.append(Move(from_sq, diag_sq))
        # En passant
        elif diag_sq == board.en_passant_square and board.en_passant_square is not None:
            moves.append(Move(from_sq, diag_sq, move_type="en_passant"))

    return moves


def knight_pseudo_moves(board: Board, from_sq: Square, color: Color) -> list[Move]:
    """Pseudolances do cavalo."""
    moves: list[Move] = []
    r, c = sq_row(from_sq), sq_col(from_sq)
    offsets = [(-2, -1), (-2, 1), (-1, -2), (-1, 2), (1, -2), (1, 2), (2, -1), (2, 1)]
    for dr, dc in offsets:
        nr, nc = r + dr, c + dc
        if 0 <= nr <= 7 and 0 <= nc <= 7:
            sq = nr * 8 + nc
            target = board.get(sq)
            if target is None or target.color != color:
                moves.append(Move(from_sq, sq))
    return moves


def bishop_pseudo_moves(board: Board, from_sq: Square, color: Color) -> list[Move]:
    """Pseudolances do bispo."""
    directions = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
    return _sliding_moves(board, from_sq, directions, color)


def rook_pseudo_moves(board: Board, from_sq: Square, color: Color) -> list[Move]:
    """Pseudolances da torre."""
    directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    return _sliding_moves(board, from_sq, directions, color)


def queen_pseudo_moves(board: Board, from_sq: Square, color: Color) -> list[Move]:
    """Pseudolances da dama."""
    directions = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
    return _sliding_moves(board, from_sq, directions, color)


def king_pseudo_moves(board: Board, from_sq: Square, color: Color) -> list[Move]:
    """Pseudolances do rei (sem roque)."""
    moves: list[Move] = []
    r, c = sq_row(from_sq), sq_col(from_sq)
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0:
                continue
            nr, nc = r + dr, c + dc
            if 0 <= nr <= 7 and 0 <= nc <= 7:
                sq = nr * 8 + nc
                target = board.get(sq)
                if target is None or target.color != color:
                    moves.append(Move(from_sq, sq))
    return moves


# ---------------------------------------------------------------------------
# Dispatcher principal
# ---------------------------------------------------------------------------


_PieceMoveGen = Callable[[Board, Square, Color], list[Move]]

_PIECE_MOVE_FN: dict[str, _PieceMoveGen] = {
    "P": pawn_pseudo_moves,
    "N": knight_pseudo_moves,
    "B": bishop_pseudo_moves,
    "R": rook_pseudo_moves,
    "Q": queen_pseudo_moves,
    "K": king_pseudo_moves,
}


def pseudo_moves_for_piece(board: Board, from_sq: Square, piece: Piece) -> list[Move]:
    """Retorna todos os pseudolances de uma peça (sem verificar xeque próprio)."""
    gen = _PIECE_MOVE_FN[piece.piece_type]
    return gen(board, from_sq, piece.color)


def all_pseudo_moves(board: Board, color: Color) -> list[Move]:
    """Todos os pseudolances de uma cor."""
    moves: list[Move] = []
    for sq in range(64):
        piece = board.get(sq)
        if piece is not None and piece.color == color:
            moves.extend(pseudo_moves_for_piece(board, sq, piece))
    return moves


# ---------------------------------------------------------------------------
# Verificação de ataque (para detecção de xeque)
# ---------------------------------------------------------------------------


def is_square_attacked(board: Board, sq: Square, by_color: Color) -> bool:
    """Retorna True se a casa sq está atacada por by_color."""
    r, c = sq_row(sq), sq_col(sq)

    # Peões: peão branco ataca de baixo para cima, logo um peão branco em (r-1, c±1) ataca sq
    pawn_dir = -1 if by_color == "w" else 1
    pawn_attack_row = r + pawn_dir
    if 0 <= pawn_attack_row <= 7:
        for dc in (-1, 1):
            nc = c + dc
            if 0 <= nc <= 7:
                attacker_sq = pawn_attack_row * 8 + nc
                piece = board.get(attacker_sq)
                if piece is not None and piece.piece_type == "P" and piece.color == by_color:
                    return True

    # Cavalos
    for dr, dc in [(-2, -1), (-2, 1), (-1, -2), (-1, 2), (1, -2), (1, 2), (2, -1), (2, 1)]:
        nr, nc = r + dr, c + dc
        if 0 <= nr <= 7 and 0 <= nc <= 7:
            piece = board.get(nr * 8 + nc)
            if piece is not None and piece.piece_type == "N" and piece.color == by_color:
                return True

    # Torre e dama em linhas retas
    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        for tsq in _ray_squares(sq, dr, dc):
            piece = board.get(tsq)
            if piece is not None:
                if piece.color == by_color and piece.piece_type in ("R", "Q"):
                    return True
                break

    # Bispo e dama em diagonais
    for dr, dc in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
        for tsq in _ray_squares(sq, dr, dc):
            piece = board.get(tsq)
            if piece is not None:
                if piece.color == by_color and piece.piece_type in ("B", "Q"):
                    return True
                break

    # Rei
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0:
                continue
            nr, nc = r + dr, c + dc
            if 0 <= nr <= 7 and 0 <= nc <= 7:
                piece = board.get(nr * 8 + nc)
                if piece is not None and piece.piece_type == "K" and piece.color == by_color:
                    return True

    return False


def find_king(board: Board, color: Color) -> Square | None:
    """Encontra a casa do rei da cor dada."""
    for sq in range(64):
        piece = board.get(sq)
        if piece is not None and piece.piece_type == "K" and piece.color == color:
            return sq
    return None


def is_in_check(board: Board, color: Color) -> bool:
    """Retorna True se o rei da cor está em xeque."""
    king_sq = find_king(board, color)
    if king_sq is None:
        return False
    opponent: Color = "b" if color == "w" else "w"
    return is_square_attacked(board, king_sq, opponent)
