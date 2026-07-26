"""
Tests for the prototype uniqueness migration in repository/db.py and the 409
duplicate-registration path in routes/prototypes.py.

The migration runs inside init_db(), so these tests seed a dirty pre-migration
state directly, run init_db() again (as a redeploy would), and assert the repaired
state. The analysis pipeline is monkeypatched for the 409 test since duplicate
detection happens at the INSERT, after synthesis.
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
from app.services import embedder, extractor, kokoro
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


async def _insert_prototype_raw(voice_name: str, speed: float) -> int:
    """Insert bypassing the API and, when the index is absent, the uniqueness rule."""
    async with aiosqlite.connect(db_module.DB_PATH) as conn:
        cursor = await conn.execute(
            """
            INSERT INTO prototypes
                (voice_name, speed, embedding, f0_mean, f0_range, hnr,
                 spectral_tilt, loudness)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (voice_name, speed, json.dumps([0.1]), 35.0, 0.2, 12.0, -10.0, 0.4),
        )
        await conn.commit()
        return cursor.lastrowid


async def test_migration_removes_duplicates_and_remaps_sessions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "migrate.db"))
    await db_module.init_db()

    async with aiosqlite.connect(db_module.DB_PATH) as conn:
        # Simulate the historical dirty state: drop the index so duplicates can
        # exist, insert them, and point a session at the later duplicate.
        await conn.execute("DROP INDEX idx_prototypes_voice_speed")
        for _ in range(3):
            await conn.execute(
                "INSERT INTO prototypes (voice_name, speed, embedding) "
                "VALUES ('af_bella', 1.0, '[]')"
            )
        await conn.execute("INSERT INTO users (token_hash) VALUES ('deadbeef')")
        await conn.execute(
            "INSERT INTO sessions (user_id, prototype_id) "
            "SELECT 1, MAX(id) FROM prototypes"
        )
        await conn.commit()

    # A redeploy re-runs init_db(); the migration must repair the state.
    await db_module.init_db()

    async with aiosqlite.connect(db_module.DB_PATH) as conn:
        cursor = await conn.execute(
            "SELECT COUNT(*), MIN(id) FROM prototypes "
            "WHERE voice_name = 'af_bella' AND speed = 1.0"
        )
        count, surviving_id = await cursor.fetchone()
        cursor = await conn.execute("SELECT prototype_id FROM sessions")
        (session_prototype_id,) = await cursor.fetchone()

    assert count == 1
    assert session_prototype_id == surviving_id


async def test_migration_is_idempotent_on_clean_data(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "idempotent.db"))
    await db_module.init_db()
    await _insert_prototype_raw("am_adam", 1.0)

    await db_module.init_db()  # second startup must not alter clean data

    async with aiosqlite.connect(db_module.DB_PATH) as conn:
        cursor = await conn.execute("SELECT COUNT(*) FROM prototypes")
        (count,) = await cursor.fetchone()
    assert count == 1


async def test_unique_index_blocks_direct_duplicate_insert(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "unique.db"))
    await db_module.init_db()
    await _insert_prototype_raw("af_nicole", 1.0)

    with pytest.raises(aiosqlite.IntegrityError):
        await _insert_prototype_raw("af_nicole", 1.0)


async def test_create_prototype_duplicate_returns_409(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    async def fake_synthesize(voice: str, speed: float, text: str = "") -> bytes:
        return b"RIFFxxxxWAVE"

    monkeypatch.setattr(kokoro, "synthesize_wav", fake_synthesize)
    monkeypatch.setattr(embedder, "compute_embedding", lambda path: [0.1, 0.2])
    monkeypatch.setattr(
        extractor,
        "extract_features",
        lambda path: {
            "f0_mean": 35.0,
            "f0_range": 0.2,
            "hnr": 12.0,
            "spectral_tilt": -10.0,
            "loudness": 0.4,
        },
    )

    first = await client.post(
        "/prototypes/", json={"voice_name": "am_adam", "speed": 1.0}
    )
    duplicate = await client.post(
        "/prototypes/", json={"voice_name": "am_adam", "speed": 1.0}
    )

    assert first.status_code == 201
    assert duplicate.status_code == 409
    assert "already exists" in duplicate.json()["detail"]


async def test_migration_survives_an_orphaned_session(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """
    Regression test for the startup-crash path: a session whose prototype row no
    longer exists must be left alone, not remapped to NULL (which would violate
    NOT NULL and abort every subsequent boot).
    """
    monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "orphan.db"))
    await db_module.init_db()

    async with aiosqlite.connect(db_module.DB_PATH) as conn:
        # Foreign keys are off by default on a raw connection, so an orphan can be
        # created here the same way historical unenforced writes could have.
        await conn.execute("INSERT INTO users (token_hash) VALUES ('cafe')")
        await conn.execute(
            "INSERT INTO sessions (user_id, prototype_id) VALUES (1, 9999)"
        )
        await conn.commit()

    await db_module.init_db()  # must not raise

    async with aiosqlite.connect(db_module.DB_PATH) as conn:
        cursor = await conn.execute("SELECT prototype_id FROM sessions")
        (prototype_id,) = await cursor.fetchone()
    assert prototype_id == 9999
