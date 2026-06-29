from __future__ import annotations

import json
import os
import tempfile

import aiosqlite
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.repository.db import get_db
from app.services import embedder, extractor, kokoro

router = APIRouter()


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


@router.post("/", response_model=PrototypeResponse, status_code=201)
async def create_prototype(
    body: PrototypeCreate,
    db: aiosqlite.Connection = Depends(get_db),
):
    """
    Synthesize a prototype voice via Kokoro TTS, run it through the shared
    Resemblyzer + eGeMAPSv02 pipeline, and persist the result.
    """
    try:
        wav_bytes = await kokoro.synthesize_wav(body.voice_name, body.speed)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Kokoro synthesis failed: {exc}")

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(wav_bytes)
            tmp_path = tmp.name
        embedding = embedder.compute_embedding(tmp_path)
        feats = extractor.extract_features(tmp_path)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Analysis pipeline failed: {exc}")
    finally:
        if tmp_path is not None:
            os.unlink(tmp_path)

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
async def list_prototypes(db: aiosqlite.Connection = Depends(get_db)):
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
