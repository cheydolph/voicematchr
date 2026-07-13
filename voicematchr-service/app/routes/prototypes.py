from __future__ import annotations

import json
from typing import Annotated

import aiofiles
import aiofiles.os
import aiofiles.tempfile
import aiosqlite
import httpx
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel

from app.repository.db import get_db
from app.services import embedder, extractor, kokoro

router = APIRouter()

# Short, neutral utterance used only for the onboarding audition button. It is
# deliberately NOT kokoro.PROBE_PASSAGE: the probe passage is long enough to give
# openSMILE and Resemblyzer stable statistics, which is the wrong tradeoff for a
# preview a learner clicks repeatedly while choosing a target voice.
PREVIEW_TEXT = "Hello, this is a preview of my voice."

# A prototype is immutable once registered (voice_name and speed never change),
# so its preview audio is a pure function of prototype_id and is safely cacheable.
# Without this header every click of the Play button re-synthesizes through Kokoro,
# costing roughly five seconds of GPU time for a byte-identical result.
PREVIEW_CACHE_SECONDS = 3600


class PrototypeCreate(BaseModel):
    voice_name: str
    speed: float = 1.0


class PrototypeResponse(BaseModel):
    id: int
    voice_name: str
    speed: float
    f0_mean: float | None
    f0_range: float | None
    hnr: float | None
    spectral_tilt: float | None
    loudness: float | None


@router.post(
    "/",
    response_model=PrototypeResponse,
    status_code=201,
    responses={
        500: {"description": "Analysis pipeline failed for the requested file."},
        502: {
            "description": "Kokoro synthesis service failed to generate the requested voice."
        },
    },
)
async def create_prototype(
    body: PrototypeCreate,
    db: Annotated[aiosqlite.Connection, Depends(get_db)],
):
    """
    Synthesize a prototype voice via Kokoro TTS, run it through the shared
    Resemblyzer + eGeMAPSv02 pipeline, and persist the result.
    """
    try:
        wav_bytes = await kokoro.synthesize_wav(body.voice_name, body.speed)
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502, detail=f"Kokoro synthesis failed: {exc}"
        ) from exc

    tmp_path = None
    try:
        async with aiofiles.tempfile.NamedTemporaryFile(
            suffix=".wav", delete=False
        ) as tmp:
            await tmp.write(wav_bytes)
            tmp_path = tmp.name
        embedding = embedder.compute_embedding(tmp_path)
        feats = extractor.extract_features(tmp_path)
    # Broad on purpose: Resemblyzer and openSMILE are third-party pipelines whose
    # exception surface is not enumerated in their public contracts. Narrowing here
    # would let an unlisted exception type escape as a detail-less 500. The `from exc`
    # clause preserves the original traceback, which the previous bare re-raise dropped.
    except Exception as exc:
        raise HTTPException(
            status_code=500, detail=f"Analysis pipeline failed: {exc}"
        ) from exc
    finally:
        if tmp_path is not None:
            await aiofiles.os.remove(tmp_path)

    cursor = await db.execute(
        """
        INSERT INTO prototypes
            (voice_name, speed, embedding, f0_mean, f0_range, hnr,
             spectral_tilt, loudness)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            body.voice_name,
            body.speed,
            json.dumps(embedding),
            feats["f0_mean"],
            feats["f0_range"],
            feats["hnr"],
            feats["spectral_tilt"],
            feats["loudness"],
        ),
    )
    await db.commit()

    return PrototypeResponse(
        id=cursor.lastrowid,
        voice_name=body.voice_name,
        speed=body.speed,
        **feats,
    )


@router.get("/", response_model=list[PrototypeResponse])
async def list_prototypes(
    db: Annotated[aiosqlite.Connection, Depends(get_db)],
):
    cursor = await db.execute(
        "SELECT id, voice_name, speed, f0_mean, f0_range, hnr, "
        "spectral_tilt, loudness FROM prototypes ORDER BY id"
    )
    rows = await cursor.fetchall()
    return [
        PrototypeResponse(
            id=row["id"],
            voice_name=row["voice_name"],
            speed=row["speed"],
            f0_mean=row["f0_mean"],
            f0_range=row["f0_range"],
            hnr=row["hnr"],
            spectral_tilt=row["spectral_tilt"],
            loudness=row["loudness"],
        )
        for row in rows
    ]


@router.get(
    "/{prototype_id}/preview",
    response_class=Response,
    responses={
        200: {
            "content": {"audio/wav": {}},
            "description": "WAV audition of the prototype voice.",
        },
        404: {"description": "Prototype not found."},
        502: {
            "description": "Kokoro synthesis service failed to generate the requested voice."
        },
    },
)
async def preview_prototype(
    prototype_id: int,
    db: Annotated[aiosqlite.Connection, Depends(get_db)],
) -> Response:
    """Stream a short WAV audition of a registered prototype voice."""
    cursor = await db.execute(
        "SELECT voice_name, speed FROM prototypes WHERE id = ?", (prototype_id,)
    )
    row = await cursor.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Prototype not found.")

    try:
        wav_bytes = await kokoro.synthesize_wav(
            row["voice_name"], row["speed"], text=PREVIEW_TEXT
        )
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502, detail=f"Kokoro synthesis failed: {exc}"
        ) from exc

    return Response(
        content=wav_bytes,
        media_type="audio/wav",
        headers={"Cache-Control": f"public, max-age={PREVIEW_CACHE_SECONDS}"},
    )
