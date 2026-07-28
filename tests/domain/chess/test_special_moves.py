"""Testes de lances especiais: roque, en passant, promoção."""

from __future__ import annotations

from src.domain.chess.engine import validate_move


class TestCastling:
    """Testes de roque."""

    # --- Roque curto brancas ---

    def test_white_castle_short(self) -> None:
        fen = "r1bqk2r/pppp1ppp/2n2n2/2b1p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4"
        result = validate_move(fen, "O-O")
        assert result["legal"] is True
        assert result["tipo_lance"] == "roque"
        assert result["fen_resultante"] == "r1bqk2r/pppp1ppp/2n2n2/2b1p3/2B1P3/5N2/PPPP1PPP/RNBQ1RK1 b kq - 5 4"

    def test_white_castle_long(self) -> None:
        fen = "r3kbnr/ppp1pppp/2nq4/3p4/3P4/2NQ4/PPP1PPPP/R3KBNR w KQkq - 4 5"
        result = validate_move(fen, "O-O-O")
        assert result["legal"] is True
        assert result["tipo_lance"] == "roque"
        # Rei deve ficar em c1, torre em d1
        assert "2KR" in result["fen_resultante"] or "2K" in result["fen_resultante"]

    def test_black_castle_short(self) -> None:
        fen = "r1bqk2r/pppp1ppp/2n2n2/2b1p3/2B1P3/5N2/PPPP1PPP/RNBQ1RK1 b kq - 5 4"
        result = validate_move(fen, "O-O")
        assert result["legal"] is True
        assert result["tipo_lance"] == "roque"

    def test_castle_right_lost_king_moved(self) -> None:
        # Rei se moveu — direito de roque perdido
        fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w - - 0 1"
        result = validate_move(fen, "O-O")
        assert result["legal"] is False

    def test_castle_blocked_piece_between(self) -> None:
        # Bispo ainda entre rei e torre
        fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        result = validate_move(fen, "O-O")
        assert result["legal"] is False

    def test_castle_king_in_check(self) -> None:
        # Rei branco em xeque — não pode fazer roque
        fen = "4r3/8/8/8/8/8/8/R3K2R w KQ - 0 1"
        result = validate_move(fen, "O-O")
        assert result["legal"] is False

    def test_castle_passing_attacked_square(self) -> None:
        # Torre preta em f8 ataca f1 — rei não pode passar por lá no roque curto
        fen = "5r2/8/8/8/8/8/8/R3K2R w KQ - 0 1"
        result = validate_move(fen, "O-O")
        assert result["legal"] is False

    def test_castle_destination_attacked(self) -> None:
        # Torre preta em g8 ataca g1 — rei não pode terminar em g1
        fen = "6r1/8/8/8/8/8/8/R3K2R w KQ - 0 1"
        result = validate_move(fen, "O-O")
        assert result["legal"] is False

    def test_castle_long_blocked(self) -> None:
        # Cavalo em b1 bloqueia roque longo
        fen = "r3kbnr/ppp1pppp/2nq4/3p4/3P4/2NQ4/PPP1PPPP/RN2KBNR w KQkq - 0 1"
        result = validate_move(fen, "O-O-O")
        assert result["legal"] is False


class TestEnPassant:
    """Testes de en passant."""

    def test_en_passant_white(self) -> None:
        # Peão branco em e5, peão preto acaba de ir d7→d5 (en passant = d6)
        fen = "rnbqkbnr/ppp1pppp/8/3pP3/8/8/PPPP1PPP/RNBQKBNR w KQkq d6 0 3"
        result = validate_move(fen, "exd6")
        assert result["legal"] is True
        assert result["tipo_lance"] == "en_passant"
        # Peão preto em d5 deve ter sido removido
        fen_result = result["fen_resultante"]
        # Na FEN resultante, d5 deve estar vazia e d6 deve ter peão branco
        from src.domain.chess.board import name_to_sq, parse_fen

        board_after = parse_fen(fen_result)
        d5 = name_to_sq("d5")
        d6 = name_to_sq("d6")
        assert board_after.get(d5) is None
        assert board_after.get(d6) is not None
        assert board_after.get(d6).piece_type == "P"  # type: ignore[union-attr]
        assert board_after.get(d6).color == "w"  # type: ignore[union-attr]

    def test_en_passant_black(self) -> None:
        # Peão preto em d4, peão branco acaba de ir c2→c4 (en passant = c3)
        fen = "rnbqkbnr/pp1ppppp/8/8/2pP4/8/PP1PPPPP/RNBQKBNR b KQkq c3 0 3"
        result = validate_move(fen, "cxd3")
        # d3 não é a casa de en passant — c3 é. Teste correto: dxc3
        assert result["legal"] is False  # dxc3 seria o correto

    def test_en_passant_black_correct(self) -> None:
        fen = "rnbqkbnr/pp2pppp/8/8/2Pp4/8/PP2PPPP/RNBQKBNR b KQkq c3 0 3"
        result = validate_move(fen, "dxc3")
        assert result["legal"] is True
        assert result["tipo_lance"] == "en_passant"

    def test_no_en_passant_outside_window(self) -> None:
        # Sem casa de en passant na FEN — a captura não pode ser feita
        fen = "rnbqkbnr/ppp1pppp/8/3pP3/8/8/PPPP1PPP/RNBQKBNR w KQkq - 0 3"
        result = validate_move(fen, "exd6")
        assert result["legal"] is False

    def test_en_passant_removes_captured_pawn(self) -> None:
        fen = "rnbqkbnr/ppp1pppp/8/3pP3/8/8/PPPP1PPP/RNBQKBNR w KQkq d6 0 3"
        result = validate_move(fen, "exd6")
        assert result["legal"] is True
        fen_after = result["fen_resultante"]
        from src.domain.chess.board import name_to_sq, parse_fen

        board = parse_fen(fen_after)
        assert board.get(name_to_sq("d5")) is None  # peão preto removido
        assert board.get(name_to_sq("e5")) is None  # peão branco saiu
        assert board.get(name_to_sq("d6")) is not None  # peão branco chegou


class TestPromotion:
    """Testes de promoção de peão."""

    def test_promotion_to_queen(self) -> None:
        fen = "8/4P3/8/8/8/8/8/4K3 w - - 0 1"
        result = validate_move(fen, "e8=Q")
        assert result["legal"] is True
        assert result["tipo_lance"] == "promocao"
        from src.domain.chess.board import name_to_sq, parse_fen
        from src.domain.chess.models import Piece

        board = parse_fen(result["fen_resultante"])
        assert board.get(name_to_sq("e8")) == Piece("Q", "w")

    def test_promotion_to_knight(self) -> None:
        fen = "8/4P3/8/8/8/8/8/4K3 w - - 0 1"
        result = validate_move(fen, "e8=N")
        assert result["legal"] is True
        from src.domain.chess.board import name_to_sq, parse_fen
        from src.domain.chess.models import Piece

        board = parse_fen(result["fen_resultante"])
        assert board.get(name_to_sq("e8")) == Piece("N", "w")

    def test_promotion_to_rook(self) -> None:
        fen = "8/4P3/8/8/8/8/8/4K3 w - - 0 1"
        result = validate_move(fen, "e8=R")
        assert result["legal"] is True

    def test_promotion_to_bishop(self) -> None:
        fen = "8/4P3/8/8/8/8/8/4K3 w - - 0 1"
        result = validate_move(fen, "e8=B")
        assert result["legal"] is True

    def test_promotion_missing_piece(self) -> None:
        fen = "8/4P3/8/8/8/8/8/4K3 w - - 0 1"
        result = validate_move(fen, "e8")
        assert result["legal"] is False
        assert "Promoção obrigatória" in result["razao"]

    def test_promotion_capture(self) -> None:
        # Peão branco em d7, torre preta em e8
        fen = "4r3/3P4/8/8/8/8/8/4K3 w - - 0 1"
        result = validate_move(fen, "dxe8=Q")
        assert result["legal"] is True
        assert result["tipo_lance"] == "promocao"
        from src.domain.chess.board import name_to_sq, parse_fen
        from src.domain.chess.models import Piece

        board = parse_fen(result["fen_resultante"])
        assert board.get(name_to_sq("e8")) == Piece("Q", "w")

    def test_promotion_black(self) -> None:
        fen = "4K3/8/8/8/8/8/4p3/8 b - - 0 1"
        result = validate_move(fen, "e1=Q")
        assert result["legal"] is True
        from src.domain.chess.board import name_to_sq, parse_fen
        from src.domain.chess.models import Piece

        board = parse_fen(result["fen_resultante"])
        assert board.get(name_to_sq("e1")) == Piece("Q", "b")

    def test_promotion_not_on_last_rank(self) -> None:
        fen = "8/8/4P3/8/8/8/8/4K3 w - - 0 1"
        result = validate_move(fen, "e7=Q")
        assert result["legal"] is False
