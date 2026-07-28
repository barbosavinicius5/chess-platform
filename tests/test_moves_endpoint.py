"""Testes de integração para o endpoint POST /games/{game_id}/moves.

Usa TestClient do FastAPI + SQLite in-memory async.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.chess_engine import FEN_INICIAL
from app.infrastructure.persistence.game_repository import GameRepository
from app.infrastructure.persistence.models import GameModel, MoveModel

# ── Helpers ──────────────────────────────────────────────────────────────────

PLAYER_BRANCO = str(uuid.uuid4())
PLAYER_PRETO = str(uuid.uuid4())
PLAYER_ESTRANHO = str(uuid.uuid4())


async def _criar_partida(session: AsyncSession, estado: str = "waiting", turno: str = "brancas") -> GameModel:
    repo = GameRepository(session)
    game = await repo.create_game(
        lado_jogador_branco=PLAYER_BRANCO,
        lado_jogador_preto=PLAYER_PRETO,
        fen_inicial=FEN_INICIAL,
    )
    game.estado = estado
    game.turno = turno
    await session.commit()
    return game


async def _fresh_session(test_engine) -> AsyncSession:
    """Abre uma sessão nova para verificação isolada."""
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    return factory()


# ── Cenário A: Aceite ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_endpoint_cenario_a_lance_aceito(test_client, test_session) -> None:
    game = await _criar_partida(test_session, estado="in_progress")

    response = await test_client.post(
        f"/games/{game.game_id}/moves",
        json={"san": "e4"},
        headers={"X-Player-Id": PLAYER_BRANCO},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["game_id"] == game.game_id
    assert data["status"] == "in_progress"
    assert data["lado"] == "brancas"
    assert "fen_resultante" in data
    assert "4P3" in data["fen_resultante"]


# ── Cenário B: Fora de turno ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_endpoint_cenario_b_fora_de_turno(test_client, test_session) -> None:
    game = await _criar_partida(test_session, estado="in_progress", turno="brancas")

    response = await test_client.post(
        f"/games/{game.game_id}/moves",
        json={"san": "e5"},
        headers={"X-Player-Id": PLAYER_PRETO},  # vez das brancas
    )

    assert response.status_code == 422
    data = response.json()
    razao = data.get("detail", {}).get("razao", data.get("razao", ""))
    assert "vez" in razao.lower() or "turno" in razao.lower()


# ── Cenário C: Não participante ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_endpoint_cenario_c_nao_participante(test_client, test_session) -> None:
    game = await _criar_partida(test_session, estado="in_progress")

    response = await test_client.post(
        f"/games/{game.game_id}/moves",
        json={"san": "e4"},
        headers={"X-Player-Id": PLAYER_ESTRANHO},
    )

    assert response.status_code == 403
    data = response.json()
    razao = data.get("detail", {}).get("razao", data.get("razao", ""))
    assert "participante" in razao.lower()


# ── Cenário D: Lance ilegal ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_endpoint_cenario_d_lance_ilegal(test_client, test_session) -> None:
    game = await _criar_partida(test_session, estado="in_progress")

    response = await test_client.post(
        f"/games/{game.game_id}/moves",
        json={"san": "Qe9"},  # posição inválida
        headers={"X-Player-Id": PLAYER_BRANCO},
    )

    assert response.status_code == 422
    data = response.json()
    razao = data.get("detail", {}).get("razao", data.get("razao", ""))
    assert razao  # razão não vazia


# ── Cenário E: Primeiro lance — waiting → in_progress ────────────────────────

@pytest.mark.asyncio
async def test_endpoint_cenario_e_primeiro_lance_status(test_client, test_session) -> None:
    game = await _criar_partida(test_session, estado="waiting")

    response = await test_client.post(
        f"/games/{game.game_id}/moves",
        json={"san": "Nf3"},
        headers={"X-Player-Id": PLAYER_BRANCO},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "in_progress"


# ── Cenário F: Atomicidade — recusa não altera o banco ─────────────────────

@pytest.mark.asyncio
async def test_endpoint_cenario_f_atomicidade_recusa(test_client, test_session, test_engine) -> None:
    game = await _criar_partida(test_session, estado="in_progress")
    game_id = game.game_id
    fen_original = game.fen_atual

    # Lance ilegal
    response = await test_client.post(
        f"/games/{game_id}/moves",
        json={"san": "e9"},
        headers={"X-Player-Id": PLAYER_BRANCO},
    )
    assert response.status_code == 422

    # Verificar banco com sessão nova (independente)
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    async with factory() as fresh:
        result = await fresh.execute(select(GameModel).where(GameModel.game_id == game_id))
        db_game = result.scalar_one()
        assert db_game.fen_atual == fen_original

        moves_result = await fresh.execute(select(MoveModel).where(MoveModel.game_id == game_id))
        moves = moves_result.scalars().all()
        assert len(moves) == 0


# ── Cenário G: Partida inexistente → 404 ────────────────────────────────────

@pytest.mark.asyncio
async def test_endpoint_partida_inexistente(test_client) -> None:
    response = await test_client.post(
        f"/games/{uuid.uuid4()}/moves",
        json={"san": "e4"},
        headers={"X-Player-Id": PLAYER_BRANCO},
    )
    assert response.status_code == 404
