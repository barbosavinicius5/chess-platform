"""Testes de xeque e xeque próprio."""

from __future__ import annotations

from src.domain.chess.board import parse_fen
from src.domain.chess.engine import validate_move
from src.domain.chess.pieces import is_in_check


class TestSelfCheck:
    """Testes de lances que deixam o próprio rei em xeque."""

    def test_move_leaves_king_in_check(self) -> None:
        # Torre branca em d2, torre preta em d8 — mover torre de d2 expõe o rei em d1 a xeque
        fen = "3r4/8/8/8/8/8/3R4/3K4 w - - 0 1"
        result = validate_move(fen, "Ra2")
        assert result["legal"] is False
        assert result["razao"] == "Lance deixa o rei em xeque"

    def test_pinned_piece_cannot_move(self) -> None:
        # Bispo branco em e2 está preso (pin) — torre preta ataca rei em e1 via e2
        fen = "4r3/8/8/8/8/8/4B3/4K3 w - - 0 1"
        result = validate_move(fen, "Bd3")
        assert result["legal"] is False

    def test_legal_move_in_check_blocking(self) -> None:
        # Rei branco em e1 em xeque por torre preta em e8 — torre branca em d1 bloqueia
        fen = "4r3/8/8/8/8/8/8/3R1K2 w - - 0 1"
        result = validate_move(fen, "Re1")
        assert result["legal"] is True

    def test_escape_from_check(self) -> None:
        # Rei em xeque — deve fugir
        fen = "4r3/8/8/8/8/8/8/4K3 w - - 0 1"
        assert is_in_check(parse_fen(fen), "w")
        result = validate_move(fen, "Kd1")
        assert result["legal"] is True

    def test_cannot_castle_into_check(self) -> None:
        # Rei termina em xeque após roque
        fen = "6r1/8/8/8/8/8/8/R3K2R w KQ - 0 1"
        result = validate_move(fen, "O-O")
        assert result["legal"] is False

    def test_en_passant_leaves_king_in_check(self) -> None:
        # En passant que deixa o rei em xeque — posição especial
        # Rei branco em e1, Torre preta em a5, peão branco em e5, peão preto em d5
        # Se exd6 en passant, rei fica exposto na fileira 5
        fen = "8/8/8/r2pP2K/8/8/8/8 w - d6 0 1"
        result = validate_move(fen, "exd6")
        assert result["legal"] is False

    def test_promotion_leaves_king_in_check(self) -> None:
        # Peão em d7 captura torre em e8 com promoção — lance é legal
        fen = "4r3/3P4/8/8/8/8/8/4K3 w - - 0 1"
        result = validate_move(fen, "dxe8=Q")
        assert result["legal"] is True
        assert result["tipo_lance"] == "promocao"

    def test_check_notation_in_san(self) -> None:
        # Lance que resulta em xeque deve ter '+' no SAN normalizado
        # Dama branca dá xeque ao rei preto
        fen2 = "4k3/8/8/8/8/8/8/3QK3 w - - 0 1"
        result = validate_move(fen2, "Qd8+")
        # Qd8 é check se rei preto está em e8
        assert result["legal"] is True
        assert result["san_normalizado"] == "Qd8+"

    def test_checkmate_notation(self) -> None:
        # Posição de mate do pastor (Scholar's mate)
        fen = "r1bqkb1r/pppp1Qpp/2n2n2/4p3/2B1P3/8/PPPP1PPP/RNB1K1NR b KQkq - 0 4"
        # Pretas estão em xeque-mate — não podem fazer nenhum lance
        from src.domain.chess.move_validator import get_all_legal_moves

        board = parse_fen(fen)
        legal = get_all_legal_moves(board, "b")
        assert len(legal) == 0

    def test_check_white(self) -> None:
        fen = "4r3/8/8/8/8/8/8/4K3 w - - 0 1"
        board = parse_fen(fen)
        assert is_in_check(board, "w")

    def test_no_check(self) -> None:
        fen = "8/8/8/8/8/8/8/4K3 w - - 0 1"
        board = parse_fen(fen)
        assert not is_in_check(board, "w")
