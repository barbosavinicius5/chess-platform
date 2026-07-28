"""Motor de regras de xadrez — Camada Domain.

Envolve a biblioteca python-chess e expõe uma interface pura (sem I/O).
"""
from __future__ import annotations

import chess
import chess.engine


def validar_lance(fen: str, san: str) -> tuple[bool, str | None, str | None]:
    """Valida um lance SAN sobre um FEN e retorna o estado resultante.

    Args:
        fen: Posição atual em FEN.
        san: Lance em Standard Algebraic Notation (ex.: "e4", "Nf3", "O-O").

    Returns:
        (aceito, fen_resultante, razao_recusa)
        - Se aceito=True:  fen_resultante é o novo FEN; razao_recusa é None.
        - Se aceito=False: fen_resultante é None; razao_recusa descreve o erro.
    """
    try:
        board = chess.Board(fen)
    except ValueError as exc:
        return False, None, f"FEN inválido: {exc}"

    try:
        move = board.parse_san(san)
    except chess.InvalidMoveError:
        return False, None, f"Lance ilegal: {san!r} não é um lance válido na posição atual"
    except chess.AmbiguousMoveError:
        return False, None, f"Lance ambíguo: {san!r} corresponde a mais de um lance"
    except chess.IllegalMoveError:
        return False, None, f"Lance ilegal: {san!r} não é permitido na posição atual"

    if move not in board.legal_moves:
        return False, None, f"Lance ilegal: {san!r} não é um lance legal na posição atual"

    board.push(move)
    return True, board.fen(), None


def turno_atual(fen: str) -> str:
    """Retorna 'brancas' ou 'pretas' com base no FEN."""
    try:
        board = chess.Board(fen)
        return "brancas" if board.turn == chess.WHITE else "pretas"
    except ValueError:
        return "brancas"


FEN_INICIAL = chess.Board().fen()
