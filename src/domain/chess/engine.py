"""Motor de regras de xadrez — ponto de entrada público."""

from __future__ import annotations

from src.domain.chess.board import board_to_fen, parse_fen
from src.domain.chess.models import MoveResult, illegal_result, legal_result
from src.domain.chess.move_validator import apply_move, get_all_legal_moves, resolve_san_to_move
from src.domain.chess.san_parser import generate_san


def validate_move(fen: str, san: str) -> MoveResult:
    """
    Valida um lance SAN contra uma posição FEN.

    Args:
        fen: Posição atual em formato FEN.
        san: Lance em formato SAN (ex: 'e4', 'Nf3', 'O-O', 'e8=Q').

    Returns:
        Dict com 'legal': True e detalhes do lance, ou 'legal': False e razão.
    """
    # 1. Parse FEN
    try:
        board = parse_fen(fen)
    except ValueError as e:
        return illegal_result(f"FEN inválido: {e}")

    # 2. Resolver SAN → Move (com validação de legalidade)
    color = board.active_color
    result = resolve_san_to_move(board, san)

    if isinstance(result, str):
        return illegal_result(result)

    move = result

    # 3. Obter todos os lances legais (para geração de SAN com desambiguação)
    legal_moves = get_all_legal_moves(board, color)

    # 4. Aplicar o lance e gerar o FEN resultante
    board_after = apply_move(board, move)
    fen_resultante = board_to_fen(board_after)

    # 5. Gerar SAN normalizado
    san_normalizado = generate_san(board, move, legal_moves, board_after, color)

    # 6. Determinar lado e tipo
    lado = "brancas" if color == "w" else "pretas"
    tipo_lance = move.move_type

    return legal_result(
        san_normalizado=san_normalizado,
        fen_resultante=fen_resultante,
        lado=lado,
        tipo_lance=tipo_lance,
    )
