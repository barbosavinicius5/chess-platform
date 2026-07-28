"""Validação de lances: SAN → Move, regras legais, xeque próprio, roque, en passant, promoção."""

from __future__ import annotations

from src.domain.chess.board import sq_col, sq_row
from src.domain.chess.models import Board, Color, Move, Piece, PieceType, Square
from src.domain.chess.pieces import (
    all_pseudo_moves,
    is_in_check,
    is_square_attacked,
    pseudo_moves_for_piece,
)
from src.domain.chess.san_parser import SANParseError, parse_san

# ---------------------------------------------------------------------------
# Aplicação de lances ao tabuleiro
# ---------------------------------------------------------------------------


def apply_move(board: Board, move: Move) -> Board:
    """Aplica o lance ao tabuleiro e retorna um novo Board com o estado atualizado."""
    new_board = board.copy()
    color = board.active_color
    opponent: Color = "b" if color == "w" else "w"

    piece = new_board.get(move.from_sq)
    assert piece is not None, f"Nenhuma peça em {move.from_sq}"

    # Resetar en passant (será reatribuído se avanço duplo)
    new_board.en_passant_square = None

    # Halfmove clock: resetar se captura ou lance de peão
    target = new_board.get(move.to_sq)
    is_capture = target is not None
    is_pawn = piece.piece_type == "P"

    if is_capture or is_pawn:
        new_board.halfmove_clock = 0
    else:
        new_board.halfmove_clock += 1

    if move.move_type == "roque":
        _apply_castle(new_board, move)
    elif move.move_type == "en_passant":
        _apply_en_passant(new_board, move, piece, color)
    elif move.move_type == "promocao":
        _apply_promotion(new_board, move, piece)
    else:
        # Lance normal
        new_board.set(move.to_sq, piece)
        new_board.set(move.from_sq, None)

        # En passant square: peão avança duas casas
        if piece.piece_type == "P":
            from_row = sq_row(move.from_sq)
            to_row = sq_row(move.to_sq)
            if abs(to_row - from_row) == 2:
                ep_row = (from_row + to_row) // 2
                ep_col = sq_col(move.from_sq)
                new_board.en_passant_square = ep_row * 8 + ep_col

    # Atualizar direitos de roque
    _update_castling_rights(new_board, move, color)

    # Alternar cor
    new_board.active_color = opponent

    # Incrementar fullmove se pretas acabaram de jogar
    if color == "b":
        new_board.fullmove_number += 1

    return new_board


def _apply_castle(board: Board, move: Move) -> None:
    """Aplica roque ao tabuleiro (rei e torre)."""
    king_from = move.from_sq
    king_to = move.to_sq
    king = board.get(king_from)

    board.set(king_to, king)
    board.set(king_from, None)

    rank = sq_row(king_from)
    if sq_col(king_to) == 6:  # roque curto
        rook_from = rank * 8 + 7
        rook_to = rank * 8 + 5
    else:  # roque longo
        rook_from = rank * 8 + 0
        rook_to = rank * 8 + 3

    rook = board.get(rook_from)
    board.set(rook_to, rook)
    board.set(rook_from, None)


def _apply_en_passant(board: Board, move: Move, piece: Piece, color: Color) -> None:
    """Aplica captura en passant."""
    board.set(move.to_sq, piece)
    board.set(move.from_sq, None)
    # Peão capturado está na mesma linha do peão atacante, na coluna de destino
    captured_sq = sq_row(move.from_sq) * 8 + sq_col(move.to_sq)
    board.set(captured_sq, None)


def _apply_promotion(board: Board, move: Move, piece: Piece) -> None:
    """Aplica promoção de peão."""
    assert move.promotion is not None
    promoted_piece = Piece(move.promotion, piece.color)
    board.set(move.to_sq, promoted_piece)
    board.set(move.from_sq, None)


def _update_castling_rights(board: Board, move: Move, color: Color) -> None:
    """Atualiza direitos de roque após um lance."""
    rights = board.castling_rights
    if rights == "-":
        return

    rank_1 = 0
    rank_8 = 7

    # Se o rei se moveu
    piece = board.get(move.to_sq)
    if piece is not None and piece.piece_type == "K":
        if color == "w":
            rights = rights.replace("K", "").replace("Q", "")
        else:
            rights = rights.replace("k", "").replace("q", "")

    # Se a torre se moveu ou foi capturada
    _rook_squares: dict[str, int] = {
        "K": rank_1 * 8 + 7,  # h1
        "Q": rank_1 * 8 + 0,  # a1
        "k": rank_8 * 8 + 7,  # h8
        "q": rank_8 * 8 + 0,  # a8
    }
    for right, sq in _rook_squares.items():
        if right in rights:
            if move.from_sq == sq or move.to_sq == sq:
                rights = rights.replace(right, "")

    board.castling_rights = rights if rights else "-"


# ---------------------------------------------------------------------------
# Geração de lances legais
# ---------------------------------------------------------------------------


def get_all_legal_moves(board: Board, color: Color) -> list[Move]:
    """Retorna todos os lances legais (não deixam o próprio rei em xeque)."""
    pseudo = all_pseudo_moves(board, color)
    legal: list[Move] = []
    for move in pseudo:
        new_board = apply_move(board, move)
        if not is_in_check(new_board, color):
            legal.append(move)

    # Adicionar roque
    castles = _generate_castle_moves(board, color)
    legal.extend(castles)

    return legal


# ---------------------------------------------------------------------------
# Geração de lances de roque
# ---------------------------------------------------------------------------


def _generate_castle_moves(board: Board, color: Color) -> list[Move]:
    """Gera lances de roque válidos."""
    moves: list[Move] = []
    rights = board.castling_rights

    if color == "w":
        rank = 0
        short_right, long_right = "K", "Q"
    else:
        rank = 7
        short_right, long_right = "k", "q"

    king_sq = rank * 8 + 4
    opponent: Color = "b" if color == "w" else "w"

    # Rei deve estar na posição inicial
    king_piece = board.get(king_sq)
    if king_piece is None or king_piece.piece_type != "K" or king_piece.color != color:
        return moves

    # Rei não pode estar em xeque
    if is_in_check(board, color):
        return moves

    # Roque curto
    if short_right in rights:
        rook_sq = rank * 8 + 7
        rook = board.get(rook_sq)
        if rook is not None and rook.piece_type == "R" and rook.color == color:
            f_sq = rank * 8 + 5
            g_sq = rank * 8 + 6
            if board.get(f_sq) is None and board.get(g_sq) is None:
                if not is_square_attacked(board, f_sq, opponent) and not is_square_attacked(board, g_sq, opponent):
                    moves.append(Move(king_sq, g_sq, move_type="roque"))

    # Roque longo
    if long_right in rights:
        rook_sq = rank * 8 + 0
        rook = board.get(rook_sq)
        if rook is not None and rook.piece_type == "R" and rook.color == color:
            b_sq = rank * 8 + 1
            c_sq = rank * 8 + 2
            d_sq = rank * 8 + 3
            if board.get(b_sq) is None and board.get(c_sq) is None and board.get(d_sq) is None:
                if not is_square_attacked(board, d_sq, opponent) and not is_square_attacked(board, c_sq, opponent):
                    moves.append(Move(king_sq, c_sq, move_type="roque"))

    return moves


# ---------------------------------------------------------------------------
# Resolução SAN → Move
# ---------------------------------------------------------------------------


def resolve_san_to_move(board: Board, san: str) -> Move | str:
    """
    Tenta resolver um SAN para um Move legal.
    Retorna o Move se legal, ou uma string de razão se ilegal.
    """
    try:
        parsed = parse_san(san)
    except SANParseError as e:
        return str(e)

    color = board.active_color

    # Roque
    if parsed["is_castle"]:
        return _resolve_castle(board, parsed, color)

    dest_sq: Square = parsed["dest_sq"]  # type: ignore[assignment]
    piece_type: PieceType = parsed["piece"]  # type: ignore[assignment]
    from_file: int | None = parsed["from_file"]  # type: ignore[assignment]
    from_rank: int | None = parsed["from_rank"]  # type: ignore[assignment]
    promotion: PieceType | None = parsed["promotion"]  # type: ignore[assignment]

    # Validação de promoção para peões
    if piece_type == "P":
        dest_row = sq_row(dest_sq)
        promo_row = 7 if color == "w" else 0
        if dest_row == promo_row and promotion is None:
            return "Promoção obrigatória: especifique a peça (ex: e8=Q)"
        if dest_row == promo_row and promotion not in ("Q", "R", "B", "N"):
            return f"Peça de promoção inválida: {promotion!r}"
        if dest_row != promo_row and promotion is not None:
            return "Promoção só é possível ao alcançar a última fileira"

    # Encontrar candidatos
    candidates: list[Move] = []
    for sq in range(64):
        p = board.get(sq)
        if p is None or p.piece_type != piece_type or p.color != color:
            continue

        if from_file is not None and sq_col(sq) != from_file:
            continue
        if from_rank is not None and sq_row(sq) != from_rank:
            continue

        pseudo = pseudo_moves_for_piece(board, sq, p)
        for m in pseudo:
            if m.to_sq != dest_sq:
                continue
            if promotion is not None and m.promotion != promotion:
                continue
            if promotion is None and m.move_type == "promocao":
                continue
            candidates.append(m)

    if not candidates:
        return _no_candidate_reason(piece_type, dest_sq)

    # Filtrar por legalidade
    legal_candidates: list[Move] = []
    for m in candidates:
        new_board = apply_move(board, m)
        if not is_in_check(new_board, color):
            legal_candidates.append(m)

    if not legal_candidates:
        return "Lance deixa o rei em xeque"

    if len(legal_candidates) > 1:
        return f"Lance ambíguo {san!r}: {len(legal_candidates)} peças podem realizar este lance"

    return legal_candidates[0]


def _resolve_castle(board: Board, parsed: dict[str, object], color: Color) -> Move | str:
    """Resolve lance de roque."""
    castle_side = parsed["castle_side"]
    castles = _generate_castle_moves(board, color)

    for m in castles:
        king_col_after = sq_col(m.to_sq)
        if castle_side == "K" and king_col_after == 6:
            return m
        if castle_side == "Q" and king_col_after == 2:
            return m

    # Determinar razão
    rights = board.castling_rights
    color_short = "K" if color == "w" else "k"
    color_long = "Q" if color == "w" else "q"
    right_char = color_short if castle_side == "K" else color_long

    if right_char not in rights:
        return "Direito de roque perdido"

    if is_in_check(board, color):
        return "Não é possível fazer roque com o rei em xeque"

    rank = 0 if color == "w" else 7
    if castle_side == "K":
        f_sq = rank * 8 + 5
        g_sq = rank * 8 + 6
        if board.get(f_sq) is not None or board.get(g_sq) is not None:
            return "Caminho do roque está bloqueado"
        return "Rei passaria por ou terminaria em casa atacada"
    else:
        b_sq = rank * 8 + 1
        c_sq = rank * 8 + 2
        d_sq = rank * 8 + 3
        if board.get(b_sq) is not None or board.get(c_sq) is not None or board.get(d_sq) is not None:
            return "Caminho do roque está bloqueado"
        return "Rei passaria por ou terminaria em casa atacada"


def _no_candidate_reason(piece_type: PieceType, dest_sq: Square) -> str:
    """Gera uma razão clara quando não há candidatos para o lance."""
    dest_name = f"{chr(ord('a') + sq_col(dest_sq))}{sq_row(dest_sq) + 1}"
    piece_name = {
        "P": "Peão",
        "N": "Cavalo",
        "B": "Bispo",
        "R": "Torre",
        "Q": "Dama",
        "K": "Rei",
    }[piece_type]
    return f"{piece_name} não pode mover para {dest_name}"
