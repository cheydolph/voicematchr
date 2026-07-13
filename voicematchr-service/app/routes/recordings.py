from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Annotated

import aiosqlite
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from app.coaching import templates as coaching_templates
from app.repository.db import get_db
from app.routes.deps import require_auth
from app.scoring import distance as scoring
from app.services import embedder, extractor

router = APIRouter()

RECORDINGS_DIR = os.environ.get("RECORDINGS_DIR", "/data/recordings")


class AnalyzeResponse(BaseModel):
    recording_id: int
    cosine_distance: float
    cosine_similarity: float
    coaching_dimension: str
    coaching_direction: str
    coaching_text: str
    delta_vector: dict[str, float]
    features: dict[str, float]


def _wav_path(token_hash_prefix: str) -> Path:
    subdir = Path(RECORDINGS_DIR) / token_hash_prefix
    subdir.mkdir(parents=True, exist_ok=True)
    return subdir / f"{uuid.uuid4()}.wav"


@router.post(
    "/analyze",
    response_model=AnalyzeResponse,
    responses={
        404: {"description": "Not found."},
        422: {"description": "Unprocessable entity"},
        502: {
            "description": "Kokoro synthesis service failed to generate the requested voice."
        },
    },
)
async def analyze(
    file: Annotated[UploadFile, File(...)],
    session_id: Annotated[int, Form(...)],
    user_id: Annotated[int, Depends(require_auth)],
    db: Annotated[aiosqlite.Connection, Depends(get_db)],
):
    cursor = await db.execute(
        "SELECT prototype_id FROM sessions WHERE id = ? AND user_id = ?",
        (session_id, user_id),
    )
    session_row = await cursor.fetchone()
    if session_row is None:
        raise HTTPException(status_code=404, detail="Session not found for this user.")
    prototype_id = session_row["prototype_id"]

    cursor = await db.execute(
        "SELECT embedding, f0_mean, f0_range, hnr, spectral_tilt, loudness "
        "FROM prototypes WHERE id = ?",
        (prototype_id,),
    )
    prototype_row = await cursor.fetchone()
    if prototype_row is None:
        raise HTTPException(status_code=404, detail="Prototype not found.")

    prototype_embedding = json.loads(prototype_row["embedding"])
    prototype_features = {
        "f0_mean": prototype_row["f0_mean"],
        "f0_range": prototype_row["f0_range"],
        "hnr": prototype_row["hnr"],
        "spectral_tilt": prototype_row["spectral_tilt"],
        "loudness": prototype_row["loudness"],
    }

    cursor = await db.execute("SELECT token_hash FROM users WHERE id = ?", (user_id,))
    user_row = await cursor.fetchone()
    token_hash_prefix = user_row["token_hash"][:16]

    dest_path = _wav_path(token_hash_prefix)
    contents = await file.read()
    dest_path.write_bytes(contents)

    try:
        learner_embedding = embedder.compute_embedding(dest_path)
        learner_features = extractor.extract_features(dest_path)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    cos_distance = scoring.cosine_distance(learner_embedding, prototype_embedding)
    cos_similarity = 1.0 - cos_distance
    deltas = scoring.compute_signed_deltas(learner_features, prototype_features)
    dimension, abs_delta, direction = scoring.select_coaching_target(deltas)
    coaching_text = coaching_templates.select_template(dimension, direction, abs_delta)

    relative_path = str(dest_path.relative_to(RECORDINGS_DIR))
    cursor = await db.execute(
        """
        INSERT INTO recordings
            (session_id, wav_path, embedding, f0_mean, f0_range, hnr,
             spectral_tilt, loudness, cosine_distance, delta_vector, coaching_text)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            session_id,
            relative_path,
            json.dumps(learner_embedding),
            learner_features["f0_mean"],
            learner_features["f0_range"],
            learner_features["hnr"],
            learner_features["spectral_tilt"],
            learner_features["loudness"],
            cos_distance,
            json.dumps(deltas),
            coaching_text,
        ),
    )
    await db.commit()

    return AnalyzeResponse(
        recording_id=cursor.lastrowid,
        cosine_distance=cos_distance,
        cosine_similarity=cos_similarity,
        coaching_dimension=dimension,
        coaching_direction=direction,
        coaching_text=coaching_text,
        delta_vector=deltas,
        features=learner_features,
    )
