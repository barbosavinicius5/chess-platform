"""Testes de movimento por peça."""

from __future__ import annotations

from src.domain.chess.board import name_to_sq, parse_fen
from src.domain.chess.engine import validate_move
from src.domain.chess.pieces import (
    is_in_check,
    is_square_attacked,
)

INITIAL_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"


class TestPawnMoves:
    """Testes do peão."""

    def test_pawn_single_advance(self) -> None:
        result = validate_move(INITIAL_FEN, "e4")
        assert result["legal"] is True

    def test_pawn_double_advance_initial(self) -> None:
        result = validate_move(INITIAL_FEN, "e4")
        assert result["legal"] is True

    def test_pawn_single_advance_non_initial(self) -> None:
        fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"
        # Pretas avançam d6
        result = validate_move(fen, "d6")
        assert result["legal"] is True

    def test_pawn_cannot_advance_backward(self) -> None:
        # e3 é avanço simples válido (de e2), não é recuo
        result = validate_move(INITIAL_FEN, "e3")
        assert result["legal"] is True

    def test_pawn_double_advance_not_from_start(self) -> None:
        # Peão em e4 não pode avançar duas casas para e6
        fen = "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2"
        result = validate_move(fen, "e6")
        # e6 está ocupado por peão preto — não pode mover
        assert result["legal"] is False

    def test_pawn_capture_diagonal(self) -> None:
        # Peão branco em e4, peão preto em d5
        fen = "rnbqkbnr/ppp1pppp/8/3p4/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2"
        result = validate_move(fen, "exd5")
        assert result["legal"] is True
        assert result["tipo_lance"] == "normal"

    def test_pawn_cannot_capture_forward(self) -> None:
        # Peão branco em e4, peão preto em e5 — não pode capturar para frente
        fen = "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2"
        result = validate_move(fen, "e5")
        assert result["legal"] is False

    def test_pawn_cannot_move_if_blocked(self) -> None:
        # Peão em e4 bloqueado por peão preto em e5
        fen = "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2"
        result = validate_move(fen, "e5")
        assert result["legal"] is False

    def test_pawn_double_blocked_by_intermediate(self) -> None:
        # Peça em e3 bloqueia avanço duplo de e2
        fen = "rnbqkbnr/pppppppp/8/8/8/4N3/PPPPPPPP/RNBQKB1R w KQkq - 0 1"
        result = validate_move(fen, "e4")
        assert result["legal"] is False


class TestKnightMoves:
    """Testes do cavalo."""

    def test_knight_initial_nf3(self) -> None:
        result = validate_move(INITIAL_FEN, "Nf3")
        assert result["legal"] is True

    def test_knight_initial_nc3(self) -> None:
        result = validate_move(INITIAL_FEN, "Nc3")
        assert result["legal"] is True

    def test_knight_l_shape(self) -> None:
        # Cavalo em e4 pode ir para d6, f6, c3, g3, etc.
        fen = "8/8/8/8/4N3/8/8/4K3 w - - 0 1"
        result = validate_move(fen, "Nd6")
        assert result["legal"] is True

    def test_knight_does_not_need_clear_path(self) -> None:
        # Cavalo salta sobre peças
        result = validate_move(INITIAL_FEN, "Nf3")
        assert result["legal"] is True

    def test_knight_cannot_move_to_own_piece(self) -> None:
        # Cavalo não pode capturar peça própria
        fen = "8/8/8/8/8/8/5P2/4K2N w - - 0 1"
        # Cavalo em h1 tentando ir para f2 (ocupado por peão branco)
        result = validate_move(fen, "Nf2")
        assert result["legal"] is False

    def test_knight_invalid_move(self) -> None:
        fen = "8/8/8/8/4N3/8/8/4K3 w - - 0 1"
        result = validate_move(fen, "Ne5")
        assert result["legal"] is False


class TestBishopMoves:
    """Testes do bispo."""

    def test_bishop_diagonal(self) -> None:
        fen = "8/8/8/8/8/8/8/2B1K3 w - - 0 1"
        result = validate_move(fen, "Bh6")
        assert result["legal"] is True

    def test_bishop_blocked_by_own_piece(self) -> None:
        # Bispo em c1 bloqueado pelo peão em d2 na posição inicial
        result = validate_move(INITIAL_FEN, "Bb2")
        assert result["legal"] is False

    def test_bishop_cannot_move_straight(self) -> None:
        fen = "8/8/8/8/8/8/8/2B1K3 w - - 0 1"
        result = validate_move(fen, "Bc2")
        # c2 não está em diagonal de c1
        assert result["legal"] is False

    def test_bishop_capture(self) -> None:
        # Bispo em c1, peão preto em f4 — f4 está na diagonal de c1 (col+3, row+3)
        fen = "8/8/8/8/5p2/8/8/2B1K3 w - - 0 1"
        result = validate_move(fen, "Bxf4")
        assert result["legal"] is True  # f4 está na diagonal de c1
        # Bispo em c1, peão preto em e4 — e4 não está na diagonal de c1
        fen2 = "8/8/8/8/4p3/8/8/2B1K3 w - - 0 1"
        result2 = validate_move(fen2, "Bxe4")
        assert result2["legal"] is False  # e4 não está em diagonal de c1


class TestRookMoves:
    """Testes da torre."""

    def test_rook_horizontal(self) -> None:
        fen = "8/8/8/8/R7/8/8/4K3 w - - 0 1"
        result = validate_move(fen, "Rh4")
        assert result["legal"] is True

    def test_rook_vertical(self) -> None:
        fen = "8/8/8/8/R7/8/8/4K3 w - - 0 1"
        result = validate_move(fen, "Ra8")
        assert result["legal"] is True

    def test_rook_blocked_intermediate(self) -> None:
        fen = "8/8/8/8/R1P5/8/8/4K3 w - - 0 1"
        result = validate_move(fen, "Rh4")
        assert result["legal"] is False

    def test_rook_cannot_move_diagonal(self) -> None:
        fen = "8/8/8/8/R7/8/8/4K3 w - - 0 1"
        result = validate_move(fen, "Rb5")
        assert result["legal"] is False

    def test_rook_capture(self) -> None:
        fen = "8/8/8/8/R4p2/8/8/4K3 w - - 0 1"
        result = validate_move(fen, "Rxf4")
        assert result["legal"] is True


class TestQueenMoves:
    """Testes da dama."""

    def test_queen_diagonal(self) -> None:
        fen = "8/8/8/8/8/8/8/3QK3 w - - 0 1"
        result = validate_move(fen, "Qh5")
        assert result["legal"] is True

    def test_queen_straight(self) -> None:
        fen = "8/8/8/8/8/8/8/3QK3 w - - 0 1"
        result = validate_move(fen, "Qd8")
        assert result["legal"] is True

    def test_queen_blocked(self) -> None:
        fen = "8/8/8/8/8/8/3P4/3QK3 w - - 0 1"
        result = validate_move(fen, "Qd8")
        assert result["legal"] is False


class TestKingMoves:
    """Testes do rei."""

    def test_king_one_step(self) -> None:
        fen = "8/8/8/8/8/8/8/4K3 w - - 0 1"
        result = validate_move(fen, "Kd1")
        assert result["legal"] is True

    def test_king_cannot_move_two_steps(self) -> None:
        fen = "8/8/8/8/8/8/8/4K3 w - - 0 1"
        result = validate_move(fen, "Kc1")
        assert result["legal"] is False

    def test_king_cannot_move_to_attacked_square(self) -> None:
        # Torre preta em f8 ataca toda a coluna f — f1 está atacada
        fen = "5r2/8/8/8/8/8/8/4K3 w - - 0 1"
        result = validate_move(fen, "Kf1")
        assert result["legal"] is False


class TestAttackDetection:
    """Testes de detecção de ataques."""

    def test_rook_attacks_squares(self) -> None:
        fen = "8/8/8/8/R7/8/8/4K3 w - - 0 1"
        board = parse_fen(fen)
        assert is_square_attacked(board, name_to_sq("a8"), "w")
        assert is_square_attacked(board, name_to_sq("h4"), "w")
        assert not is_square_attacked(board, name_to_sq("b5"), "w")

    def test_pawn_attacks(self) -> None:
        fen = "8/8/8/8/8/8/4P3/4K3 w - - 0 1"
        board = parse_fen(fen)
        assert is_square_attacked(board, name_to_sq("d3"), "w")
        assert is_square_attacked(board, name_to_sq("f3"), "w")
        assert not is_square_attacked(board, name_to_sq("e3"), "w")

    def test_is_in_check(self) -> None:
        # Rei branco em e1, torre preta em e8 — xeque
        fen = "4r3/8/8/8/8/8/8/4K3 w - - 0 1"
        board = parse_fen(fen)
        assert is_in_check(board, "w")

    def test_not_in_check(self) -> None:
        fen = "8/8/8/8/8/8/8/4K3 w - - 0 1"
        board = parse_fen(fen)
        assert not is_in_check(board, "w")
