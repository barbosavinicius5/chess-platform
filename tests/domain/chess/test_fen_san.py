"""Testes de parsing de FEN e SAN."""

from __future__ import annotations

import pytest

from src.domain.chess.board import board_to_fen, name_to_sq, parse_fen, sq_to_name
from src.domain.chess.models import Piece
from src.domain.chess.san_parser import SANParseError, parse_san


class TestFenParsing:
    """Testes de parsing de FEN."""

    def test_initial_position(self) -> None:
        fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        board = parse_fen(fen)
        assert board.active_color == "w"
        assert board.castling_rights == "KQkq"
        assert board.en_passant_square is None
        assert board.halfmove_clock == 0
        assert board.fullmove_number == 1

    def test_initial_position_pieces(self) -> None:
        fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        board = parse_fen(fen)
        # Peão branco em e2 (índice 12)
        e2 = name_to_sq("e2")
        assert board.get(e2) == Piece("P", "w")
        # Torre preta em a8
        a8 = name_to_sq("a8")
        assert board.get(a8) == Piece("R", "b")
        # Rei branco em e1
        e1 = name_to_sq("e1")
        assert board.get(e1) == Piece("K", "w")
        # Rei preto em e8
        e8 = name_to_sq("e8")
        assert board.get(e8) == Piece("K", "b")

    def test_en_passant_square(self) -> None:
        fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"
        board = parse_fen(fen)
        assert board.en_passant_square == name_to_sq("e3")

    def test_partial_castling_rights(self) -> None:
        fen = "r1bqk2r/pppp1ppp/2n2n2/2b1p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4"
        board = parse_fen(fen)
        assert board.castling_rights == "KQkq"

    def test_no_castling_rights(self) -> None:
        fen = "8/8/8/8/8/8/8/4K3 w - - 0 1"
        board = parse_fen(fen)
        assert board.castling_rights == "-"

    def test_black_to_move(self) -> None:
        fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"
        board = parse_fen(fen)
        assert board.active_color == "b"

    def test_invalid_fen_wrong_fields(self) -> None:
        with pytest.raises(ValueError, match="6 campos"):
            parse_fen("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq -")

    def test_invalid_fen_bad_rank(self) -> None:
        with pytest.raises(ValueError):
            parse_fen("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP w KQkq - 0 1")

    def test_invalid_fen_bad_side(self) -> None:
        with pytest.raises(ValueError, match="lado"):
            parse_fen("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR x KQkq - 0 1")


class TestFenGeneration:
    """Testes de geração de FEN."""

    def test_roundtrip_initial(self) -> None:
        fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        board = parse_fen(fen)
        assert board_to_fen(board) == fen

    def test_roundtrip_after_e4(self) -> None:
        fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"
        board = parse_fen(fen)
        assert board_to_fen(board) == fen

    def test_roundtrip_complex(self) -> None:
        fen = "r1bqk2r/pppp1ppp/2n2n2/2b1p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4"
        board = parse_fen(fen)
        assert board_to_fen(board) == fen


class TestCoordinates:
    """Testes de conversão de coordenadas."""

    def test_a1_is_zero(self) -> None:
        assert name_to_sq("a1") == 0

    def test_h8_is_63(self) -> None:
        assert name_to_sq("h8") == 63

    def test_e4(self) -> None:
        assert name_to_sq("e4") == 28

    def test_sq_to_name_roundtrip(self) -> None:
        for sq in range(64):
            assert name_to_sq(sq_to_name(sq)) == sq


class TestSanParsing:
    """Testes de parsing de SAN."""

    def test_pawn_advance(self) -> None:
        result = parse_san("e4")
        assert result["piece"] == "P"
        assert result["is_castle"] is False
        assert result["dest_sq"] == name_to_sq("e4")

    def test_pawn_capture(self) -> None:
        result = parse_san("exd5")
        assert result["piece"] == "P"
        assert result["is_capture"] is True
        assert result["from_file"] == 4  # e = col 4
        assert result["dest_sq"] == name_to_sq("d5")

    def test_knight_move(self) -> None:
        result = parse_san("Nf3")
        assert result["piece"] == "N"
        assert result["dest_sq"] == name_to_sq("f3")

    def test_castle_short(self) -> None:
        result = parse_san("O-O")
        assert result["is_castle"] is True
        assert result["castle_side"] == "K"

    def test_castle_long(self) -> None:
        result = parse_san("O-O-O")
        assert result["is_castle"] is True
        assert result["castle_side"] == "Q"

    def test_promotion(self) -> None:
        result = parse_san("e8=Q")
        assert result["piece"] == "P"
        assert result["promotion"] == "Q"
        assert result["dest_sq"] == name_to_sq("e8")

    def test_capture_promotion(self) -> None:
        result = parse_san("exd8=N")
        assert result["is_capture"] is True
        assert result["promotion"] == "N"

    def test_check_annotation(self) -> None:
        result = parse_san("Nf3+")
        assert result["check"] == "+"

    def test_checkmate_annotation(self) -> None:
        result = parse_san("Qh5#")
        assert result["check"] == "#"

    def test_disambiguation_file(self) -> None:
        result = parse_san("Nbd2")
        assert result["piece"] == "N"
        assert result["from_file"] == 1  # b = col 1

    def test_disambiguation_rank(self) -> None:
        result = parse_san("R1a3")
        assert result["piece"] == "R"
        assert result["from_rank"] == 0  # rank 1 = index 0

    def test_invalid_san(self) -> None:
        with pytest.raises(SANParseError):
            parse_san("invalid!")

    def test_castle_with_check(self) -> None:
        result = parse_san("O-O+")
        assert result["is_castle"] is True
        assert result["castle_side"] == "K"
