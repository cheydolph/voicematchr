"""
Route tests for GET /prototypes/{id}/preview.

Kokoro is not reachable from the test container, so kokoro.synthesize_wav is
monkeypatched at the module the route actually imports (app.services.kokoro).
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from pathlib import Path

import aiosqlite
import httpx
import pytest
import pytest_asyncio
from app.main import app
from app.repository import db as db_module
from app.routes import prototypes as prototypes_route
from app.services import kokoro
from httpx import ASGITransport, AsyncClient

FAKE_WAV = b"RIFF\x00\x00\x00\x00WAVEfmt "


@pytest_asyncio.fixture
async def client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AsyncIterator[AsyncClient]:
    monkeypatch.setattr(db_module, "DB_PATH", str(tmp_path / "test.db"))
    await db_module.init_db()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client


async def _seed_prototype(voice_name: str = "af_bella", speed: float = 1.0) -> int:
    async with aiosqlite.connect(db_module.DB_PATH) as conn:
        cursor = await conn.execute(
            """
            INSERT INTO prototypes
                (voice_name, speed, embedding, f0_mean, f0_range, hnr,
                 spectral_tilt, loudness)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (voice_name, speed, json.dumps([0.1, 0.2]), 35.0, 0.2, 12.0, -10.0, 0.4),
        )
        await conn.commit()
        return cursor.lastrowid


async def test_preview_returns_wav_audio(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    calls: list[tuple[str, float, str]] = []

    async def fake_synthesize(voice: str, speed: float, text: str = "") -> bytes:
        calls.append((voice, speed, text))
        return FAKE_WAV

    monkeypatch.setattr(kokoro, "synthesize_wav", fake_synthesize)
    prototype_id = await _seed_prototype(voice_name="am_adam", speed=1.15)

    response = await client.get(f"/prototypes/{prototype_id}/preview")

    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/wav"
    assert response.content == FAKE_WAV
    # The registered voice and speed, not defaults, are what get synthesized.
    assert calls == [("am_adam", 1.15, prototypes_route.PREVIEW_TEXT)]


async def test_preview_sets_a_cache_header(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    async def fake_synthesize(voice: str, speed: float, text: str = "") -> bytes:
        return FAKE_WAV

    monkeypatch.setattr(kokoro, "synthesize_wav", fake_synthesize)
    prototype_id = await _seed_prototype()

    response = await client.get(f"/prototypes/{prototype_id}/preview")

    assert response.status_code == 200
    assert "max-age" in response.headers["cache-control"]


async def test_preview_of_an_unknown_prototype_is_404(client: AsyncClient):
    response = await client.get("/prototypes/9999/preview")
    assert response.status_code == 404
    assert response.json()["detail"] == "Prototype not found."


async def test_preview_returns_502_when_kokoro_is_unreachable(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    async def failing_synthesize(voice: str, speed: float, text: str = "") -> bytes:
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(kokoro, "synthesize_wav", failing_synthesize)
    prototype_id = await _seed_prototype()

    response = await client.get(f"/prototypes/{prototype_id}/preview")

    # Before this change an unreachable Kokoro surfaced as an unhandled
    # httpx.ConnectError, which the ASGI stack turns into a bare 500.
    assert response.status_code == 502
    assert "Kokoro synthesis failed" in response.json()["detail"]
