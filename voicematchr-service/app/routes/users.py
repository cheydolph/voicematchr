import hashlib
import json
import secrets
from typing import Annotated

import aiosqlite
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.repository.db import get_db

router = APIRouter()


class OnboardRequest(BaseModel):
    accent_background: str
    vocal_training_history: str


class OnboardResponse(BaseModel):
    token: str


@router.post("/onboard", response_model=OnboardResponse, status_code=201)
async def onboard(
    body: OnboardRequest,
    db: Annotated[aiosqlite.Connection, Depends(get_db)],
):
    raw_token = secrets.token_hex(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    demographics = json.dumps(
        {
            "accent_background": body.accent_background,
            "vocal_training_history": body.vocal_training_history,
        }
    )

    await db.execute(
        "INSERT INTO users (token_hash, demographics) VALUES (?, ?)",
        (token_hash, demographics),
    )
    await db.commit()

    return OnboardResponse(token=raw_token)
