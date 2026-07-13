"""
Route tests for GET /sessions/ (the longitudinal-history endpoint).

These exercise the ASGI app directly through httpx.ASGITransport rather than a
live server. ASGITransport does not run FastAPI's lifespan, so init_db() is
invoked explicitly in the fixture; DB_PATH is monkeypatched to a per-test file so
no test touches the mounted /data volume.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from pathlib import Path

import aiosqlite
import pytest
import pytest_asyncio
from app.main import app
from app.repository import db as db_module
from httpx import ASGITransport, AsyncClient


@pytest_asyncio.fixture
async def client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AsyncIterator[AsyncClient]:
    monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "test.db"))
    await db_module.init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client


async def _seed_prototype() -> int:
    """Insert a prototype directly, bypassing Kokoro and the analysis pipeline."""
    async with aiosqlite.connect(db_module.DB_PATH) as conn:
        cursor = await conn.execute(
            """
            INSERT INTO prototypes
                (voice_name, speed, embedding, f0_mean, f0_range, hnr,
                 spectral_tilt, loudness)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("af_bella", 1.0, json.dumps([0.1, 0.2, 0.3]), 35.0, 0.2, 12.0, -10.0, 0.4),
        )
        await conn.commit()
        return cursor.lastrowid


async def _seed_recording(
    session_id: int, cosine_distance: float, created_at: str
) -> None:
    """
    Insert an analyzed recording directly.

    `created_at` is supplied explicitly so a test can prove that ordering follows
    the primary key and not the timestamp column.
    """
    async with aiosqlite.connect(db_module.DB_PATH) as conn:
        await conn.execute(
            """
            INSERT INTO recordings
                (session_id, wav_path, embedding, cosine_distance, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (session_id, "x/y.wav", json.dumps([0.1]), cosine_distance, created_at),
        )
        await conn.commit()


async def _onboard(client: AsyncClient) -> str:
    response = await client.post(
        "/users/onboard",
        json={
            "accent_background": "General American",
            "vocal_training_history": "none",
        },
    )
    assert response.status_code == 201
    return response.json()["token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def test_list_sessions_requires_a_token(client: AsyncClient):
    response = await client.get("/sessions/")
    assert response.status_code == 422  # Authorization header is a required dependency


async def test_list_sessions_rejects_an_unknown_token(client: AsyncClient):
    response = await client.get("/sessions/", headers=_auth("not-a-real-token"))
    assert response.status_code == 401


async def test_list_sessions_is_empty_for_a_new_user(client: AsyncClient):
    token = await _onboard(client)
    response = await client.get("/sessions/", headers=_auth(token))
    assert response.status_code == 200
    assert response.json() == []


async def test_list_sessions_returns_only_the_callers_sessions(client: AsyncClient):
    prototype_id = await _seed_prototype()

    mine = await _onboard(client)
    theirs = await _onboard(client)
    created = await client.post(
        "/sessions/", json={"prototype_id": prototype_id}, headers=_auth(mine)
    )
    assert created.status_code == 201
    my_session_id = created.json()["session_id"]

    my_view = await client.get("/sessions/", headers=_auth(mine))
    their_view = await client.get("/sessions/", headers=_auth(theirs))

    assert [s["session_id"] for s in my_view.json()] == [my_session_id]
    assert their_view.json() == []


async def test_list_sessions_returns_recordings_in_insertion_order(client: AsyncClient):
    prototype_id = await _seed_prototype()
    token = await _onboard(client)
    created = await client.post(
        "/sessions/", json={"prototype_id": prototype_id}, headers=_auth(token)
    )
    session_id = created.json()["session_id"]

    # Identical timestamps: the old ORDER BY created_at could not disambiguate these.
    await _seed_recording(session_id, 0.31, "2026-07-11 14:02:10")
    await _seed_recording(session_id, 0.24, "2026-07-11 14:02:10")
    await _seed_recording(session_id, 0.19, "2026-07-11 14:02:10")

    payload = await client.get("/sessions/", headers=_auth(token))
    recordings = payload.json()[0]["recordings"]

    assert [r["cosine_distance"] for r in recordings] == [0.31, 0.24, 0.19]
    assert [r["recording_id"] for r in recordings] == sorted(
        r["recording_id"] for r in recordings
    )
