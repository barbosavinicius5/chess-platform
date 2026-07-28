from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from chess.domain.game import INITIAL_FEN
from tests.conftest import create_game


# ── Cenário A — Partida in_progress com lances ──────────────────────────────
async def test_get_game_in_progress_with_moves(db_session: AsyncSession, client: AsyncClient) -> None:
    non_initial_fen = "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq e6 0 2"
    game = await create_game(
        db_session,
        status="in_progress",
        white_player_id=str(uuid.uuid4()),
        black_player_id=str(uuid.uuid4()),
        fen=non_initial_fen,
        turn="pretas",
        moves=[("e4", 1), ("e5", 2)],
    )

    response = await client.get(
        f"/games/{game.id}",
        headers={"X-Player-Id": game.white_player_id},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["game_id"] == game.id
    assert data["status"] == "in_progress"
    assert data["fen"] != INITIAL_FEN
    assert data["fen"] == non_initial_fen
    assert data["moves"] == ["e4", "e5"]
    assert "turn" in data


# ── Cenário B — Partida waiting sem lances ───────────────────────────────────
async def test_get_game_waiting_no_moves(db_session: AsyncSession, client: AsyncClient) -> None:
    white_player_id = str(uuid.uuid4())
    game = await create_game(
        db_session,
        status="waiting",
        white_player_id=white_player_id,
        black_player_id=None,
        fen=INITIAL_FEN,
        turn="brancas",
        moves=[],
    )

    response = await client.get(
        f"/games/{game.id}",
        headers={"X-Player-Id": white_player_id},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["game_id"] == game.id
    assert data["status"] == "waiting"
    assert data["fen"] == INITIAL_FEN
    assert data["turn"] == "brancas"
    assert data["moves"] == []


# ── Cenário C — Partida inexistente ─────────────────────────────────────────
async def test_get_game_not_found(client: AsyncClient) -> None:
    response = await client.get(
        "/games/nonexistent-id",
        headers={"X-Player-Id": str(uuid.uuid4())},
    )

    assert response.status_code == 404
    data = response.json()
    assert data["detail"] == "Partida não encontrada"
    # Sem dados parciais
    assert "fen" not in data
    assert "status" not in data
    assert "moves" not in data


# ── Cenário D — Não-participante ─────────────────────────────────────────────
async def test_get_game_forbidden_for_non_participant(db_session: AsyncSession, client: AsyncClient) -> None:
    game = await create_game(
        db_session,
        status="in_progress",
        white_player_id=str(uuid.uuid4()),
        black_player_id=str(uuid.uuid4()),
    )

    response = await client.get(
        f"/games/{game.id}",
        headers={"X-Player-Id": "outro-player-id"},
    )

    assert response.status_code == 403
    data = response.json()
    assert data["detail"] == "Acesso não permitido"


# ── Cenário E — Reconexão/auditoria (múltiplos lances) ───────────────────────
async def test_get_game_multiple_moves_in_order(db_session: AsyncSession, client: AsyncClient) -> None:
    white_player_id = str(uuid.uuid4())
    black_player_id = str(uuid.uuid4())
    fen_5_moves = "r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4"

    game = await create_game(
        db_session,
        status="in_progress",
        white_player_id=white_player_id,
        black_player_id=black_player_id,
        fen=fen_5_moves,
        turn="brancas",
        # inseridos fora de ordem para garantir que o sort funcione
        moves=[("Nf3", 3), ("e4", 1), ("Nc6", 4), ("e5", 2), ("Bc4", 5)],
    )

    response = await client.get(
        f"/games/{game.id}",
        headers={"X-Player-Id": white_player_id},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["moves"]) == 5
    assert data["moves"] == ["e4", "e5", "Nf3", "Nc6", "Bc4"]
    assert "fen" in data
    assert "turn" in data