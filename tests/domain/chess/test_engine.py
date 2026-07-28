"""Testes de integração do engine — tabela completa de casos."""

from __future__ import annotations

import pytest

from src.domain.chess.engine import validate_move

# ---------------------------------------------------------------------------
# Tabela de lances legais
# ---------------------------------------------------------------------------

LEGAL_MOVES: list[tuple[str, str, str, str]] = [
    # (fen, san, fen_resultante_esperado, tipo_esperado)
    # --- Posição inicial — peão e4 ---
    (
        "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        "e4",
        "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1",
        "normal",
    ),
    # --- Peão preto d5 ---
    (
        "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1",
        "d5",
        "rnbqkbnr/ppp1pppp/8/3p4/4P3/8/PPPP1PPP/RNBQKBNR w KQkq d6 0 2",
        "normal",
    ),
    # --- Cavalo branco f3 ---
    (
        "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        "Nf3",
        "rnbqkbnr/pppppppp/8/8/8/5N2/PPPPPPPP/RNBQKB1R b KQkq - 1 1",
        "normal",
    ),
    # --- Roque curto brancas ---
    (
        "r1bqk2r/pppp1ppp/2n2n2/2b1p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4",
        "O-O",
        "r1bqk2r/pppp1ppp/2n2n2/2b1p3/2B1P3/5N2/PPPP1PPP/RNBQ1RK1 b kq - 5 4",
        "roque",
    ),
    # --- En passant brancas ---
    (
        "rnbqkbnr/ppp1pppp/8/3pP3/8/8/PPPP1PPP/RNBQKBNR w KQkq d6 0 3",
        "exd6",
        "rnbqkbnr/ppp1pppp/3P4/8/8/8/PPPP1PPP/RNBQKBNR b KQkq - 0 3",
        "en_passant",
    ),
    # --- Promoção brancas para dama ---
    (
        "8/4P3/8/8/8/8/8/4K3 w - - 0 1",
        "e8=Q",
        "4Q3/8/8/8/8/8/8/4K3 b - - 0 1",
        "promocao",
    ),
    # --- Promoção para cavalo ---
    (
        "8/4P3/8/8/8/8/8/4K3 w - - 0 1",
        "e8=N",
        "4N3/8/8/8/8/8/8/4K3 b - - 0 1",
        "promocao",
    ),
    # --- Torre movendo horizontal ---
    (
        "8/8/8/8/R7/8/8/4K3 w - - 0 1",
        "Rh4",
        "8/8/8/8/7R/8/8/4K3 b - - 1 1",
        "normal",
    ),
    # --- Bispo movendo diagonal (c1→h6) ---
    (
        "8/8/8/8/8/8/8/2B1K3 w - - 0 1",
        "Bh6",
        "8/8/7B/8/8/8/8/4K3 b - - 1 1",
        "normal",
    ),
    # --- Dama movendo ---
    (
        "8/8/8/8/8/8/8/3QK3 w - - 0 1",
        "Qd8",
        "3Q4/8/8/8/8/8/8/4K3 b - - 1 1",
        "normal",
    ),
    # --- Rei movendo ---
    (
        "8/8/8/8/8/8/8/4K3 w - - 0 1",
        "Kd1",
        "8/8/8/8/8/8/8/3K4 b - - 1 1",
        "normal",
    ),
    # --- Roque longo brancas ---
    (
        "r3kbnr/ppp1pppp/2nq4/3p4/3P4/2NQ4/PPP1PPPP/R3KBNR w KQkq - 4 5",
        "O-O-O",
        "r3kbnr/ppp1pppp/2nq4/3p4/3P4/2NQ4/PPP1PPPP/2KR1BNR b kq - 5 5",
        "roque",
    ),
    # --- En passant pretas ---
    (
        "rnbqkbnr/pp3ppp/8/4p3/2Pp4/8/PP2PPPP/RNBQKBNR b KQkq c3 0 3",
        "dxc3",
        "rnbqkbnr/pp3ppp/8/4p3/8/2p5/PP2PPPP/RNBQKBNR w KQkq - 0 4",
        "en_passant",
    ),
]

# ---------------------------------------------------------------------------
# Tabela de lances ilegais
# ---------------------------------------------------------------------------

ILLEGAL_MOVES: list[tuple[str, str, str]] = [
    # (fen, san, razao_parcial)
    # Torre movendo em diagonal
    (
        "8/8/8/8/R7/8/8/4K3 w - - 0 1",
        "Rb5",
        "Torre",
    ),
    # Peão movendo para casa bloqueada
    (
        "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2",
        "e5",
        "Peão",
    ),
    # Roque com rei em xeque
    (
        "4r3/8/8/8/8/8/8/R3K2R w KQ - 0 1",
        "O-O",
        "xeque",
    ),
    # Lance que deixa o rei em xeque (peça presa)
    (
        "3r4/8/8/8/8/8/3R4/3K4 w - - 0 1",
        "Ra2",
        "xeque",
    ),
    # En passant fora da janela
    (
        "rnbqkbnr/ppp1pppp/8/3pP3/8/8/PPPP1PPP/RNBQKBNR w KQkq - 0 3",
        "exd6",
        "Peão",
    ),
    # Promoção sem especificar peça
    (
        "8/4P3/8/8/8/8/8/4K3 w - - 0 1",
        "e8",
        "Promoção obrigatória",
    ),
    # Bispo não pode mover em linha reta
    (
        "8/8/8/8/8/8/8/2B1K3 w - - 0 1",
        "Bc2",
        "Bispo",
    ),
    # Cavalo movendo de forma inválida
    (
        "8/8/8/8/4N3/8/8/4K3 w - - 0 1",
        "Ne5",
        "Cavalo",
    ),
    # Roque com direito perdido
    (
        "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w - - 0 1",
        "O-O",
        "perdido",
    ),
    # Roque bloqueado por peça entre rei e torre
    (
        "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        "O-O",
        "bloqueado",
    ),
]


class TestLegalMoves:
    """Testa lances legais da tabela."""

    @pytest.mark.parametrize("fen,san,fen_esperado,tipo_esperado", LEGAL_MOVES)
    def test_legal_move(self, fen: str, san: str, fen_esperado: str, tipo_esperado: str) -> None:
        result = validate_move(fen, san)
        assert result["legal"] is True, f"Esperado legal, obtido: {result}"
        assert result["tipo_lance"] == tipo_esperado, (
            f"Tipo esperado {tipo_esperado!r}, obtido {result['tipo_lance']!r}"
        )
        assert result["fen_resultante"] == fen_esperado, (
            f"FEN esperado:\n  {fen_esperado}\nFEN obtido:\n  {result['fen_resultante']}"
        )

    @pytest.mark.parametrize("fen,san,fen_esperado,tipo_esperado", LEGAL_MOVES)
    def test_san_normalizado_present(self, fen: str, san: str, fen_esperado: str, tipo_esperado: str) -> None:
        result = validate_move(fen, san)
        if result["legal"]:
            assert isinstance(result["san_normalizado"], str)
            assert len(result["san_normalizado"]) > 0


class TestIllegalMoves:
    """Testa lances ilegais da tabela."""

    @pytest.mark.parametrize("fen,san,razao_parcial", ILLEGAL_MOVES)
    def test_illegal_move(self, fen: str, san: str, razao_parcial: str) -> None:
        result = validate_move(fen, san)
        assert result["legal"] is False, f"Esperado ilegal para {san!r}, obtido: {result}"
        razao = result.get("razao", "")
        assert razao_parcial.lower() in str(razao).lower(), (
            f"Razão esperada contendo {razao_parcial!r}, obtido: {razao!r}"
        )


class TestReturnStructure:
    """Testa a estrutura do retorno."""

    def test_legal_result_keys(self) -> None:
        result = validate_move("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", "e4")
        assert result["legal"] is True
        assert "san_normalizado" in result
        assert "fen_resultante" in result
        assert "lado" in result
        assert "tipo_lance" in result

    def test_illegal_result_keys(self) -> None:
        result = validate_move("8/8/8/8/R7/8/8/4K3 w - - 0 1", "Rb5")
        assert result["legal"] is False
        assert "razao" in result

    def test_lado_brancas(self) -> None:
        result = validate_move("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", "e4")
        assert result["lado"] == "brancas"

    def test_lado_pretas(self) -> None:
        result = validate_move("rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1", "d5")
        assert result["lado"] == "pretas"

    def test_invalid_fen(self) -> None:
        result = validate_move("invalid_fen", "e4")
        assert result["legal"] is False
        assert "FEN" in result["razao"]

    def test_invalid_san(self) -> None:
        result = validate_move("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", "xyz!")
        assert result["legal"] is False


class TestCounters:
    """Testa atualização de contadores de FEN."""

    def test_halfmove_clock_increments_non_pawn(self) -> None:
        fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        result = validate_move(fen, "Nf3")
        from src.domain.chess.board import parse_fen

        board = parse_fen(result["fen_resultante"])
        assert board.halfmove_clock == 1

    def test_halfmove_clock_resets_on_pawn(self) -> None:
        fen = "rnbqkbnr/pppppppp/8/8/8/5N2/PPPPPPPP/RNBQKB1R b KQkq - 1 1"
        result = validate_move(fen, "e5")
        from src.domain.chess.board import parse_fen

        board = parse_fen(result["fen_resultante"])
        assert board.halfmove_clock == 0

    def test_fullmove_increments_after_black(self) -> None:
        fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"
        result = validate_move(fen, "e5")
        from src.domain.chess.board import parse_fen

        board = parse_fen(result["fen_resultante"])
        assert board.fullmove_number == 2

    def test_fullmove_does_not_increment_after_white(self) -> None:
        fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        result = validate_move(fen, "e4")
        from src.domain.chess.board import parse_fen

        board = parse_fen(result["fen_resultante"])
        assert board.fullmove_number == 1

    def test_en_passant_cleared_after_non_pawn_double(self) -> None:
        fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"
        result = validate_move(fen, "Nc6")
        from src.domain.chess.board import parse_fen

        board = parse_fen(result["fen_resultante"])
        assert board.en_passant_square is None


class TestDisambiguation:
    """Testa desambiguação de SAN."""

    def test_two_rooks_different_column(self) -> None:
        # Torre de h1 vai para h4 — sem ambiguidade com torre de a1
        fen = "8/8/8/8/8/8/8/R3K2R w KQ - 0 1"
        result = validate_move(fen, "Rh4")
        assert result["legal"] is True

    def test_knight_with_file_disambiguation(self) -> None:
        # Dois cavalos que podem ir ao mesmo destino — desambiguar por coluna
        fen = "8/8/8/8/8/8/8/N3K2N w - - 0 1"
        result = validate_move(fen, "Nac2")
        assert result["legal"] is True

    def test_ambiguous_knights(self) -> None:
        # Dois cavalos em d5 e d3 que podem ir a f4 — deve ser ambíguo sem desambiguação
        fen = "8/8/8/3N4/8/3N4/8/4K3 w - - 0 1"
        result = validate_move(fen, "Nf4")
        assert result["legal"] is False
        assert "ambíguo" in str(result.get("razao", ""))

    def test_san_with_disambiguation_file(self) -> None:
        # Verificar que SAN gerado inclui desambiguação
        fen = "8/8/8/3N4/8/3N4/8/4K3 w - - 0 1"
        result = validate_move(fen, "Nd4f5")  # inválido mas verifica fluxo
        assert result["legal"] is False

    def test_rook_san_with_disambiguation(self) -> None:
        # Duas torres, Tower de a1 vai a a4 — desambiguação por coluna
        fen2 = "8/8/8/8/8/8/8/R6R w - - 0 1"
        result = validate_move(fen2, "Raa4")  # Torre de a1 vai a a4
        assert result["legal"] is True


class TestCastlingRightsUpdate:
    """Testa atualização de direitos de roque."""

    def test_castling_rights_removed_after_king_moves(self) -> None:
        fen = "r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1"
        result = validate_move(fen, "Kf1")
        assert result["legal"] is True
        from src.domain.chess.board import parse_fen

        board = parse_fen(result["fen_resultante"])
        assert "K" not in board.castling_rights
        assert "Q" not in board.castling_rights

    def test_castling_rights_removed_after_rook_moves(self) -> None:
        fen = "r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1"
        result = validate_move(fen, "Ra2")
        assert result["legal"] is True
        from src.domain.chess.board import parse_fen

        board = parse_fen(result["fen_resultante"])
        assert "Q" not in board.castling_rights
        assert "K" in board.castling_rights

    def test_black_castling_rights_preserved(self) -> None:
        fen = "r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1"
        result = validate_move(fen, "Ra2")
        assert result["legal"] is True
        from src.domain.chess.board import parse_fen

        board = parse_fen(result["fen_resultante"])
        assert "k" in board.castling_rights
        assert "q" in board.castling_rights
