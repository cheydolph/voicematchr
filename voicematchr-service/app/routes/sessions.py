from typing import Annotated

import aiosqlite
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.repository.db import get_db
from app.routes.deps import require_auth

router = APIRouter()


class SessionCreate(BaseModel):
    prototype_id: int


class SessionCreateResponse(BaseModel):
    session_id: int


@router.post(
    "/",
    response_model=SessionCreateResponse,
    status_code=201,
    responses={
        404: {"description": "Prototype not found."},
    },
)
async def create_session(
    body: SessionCreate,
    user_id: Annotated[int, Depends(require_auth)],
    db: Annotated[aiosqlite.Connection, Depends(get_db)],
):
    cursor = await db.execute(
        "SELECT id FROM prototypes WHERE id = ?", (body.prototype_id,)
    )
    if await cursor.fetchone() is None:
        raise HTTPException(status_code=404, detail="Prototype not found.")

    cursor = await db.execute(
        "INSERT INTO sessions (user_id, prototype_id) VALUES (?, ?)",
        (user_id, body.prototype_id),
    )
    await db.commit()
    return SessionCreateResponse(session_id=cursor.lastrowid)


@router.get(
    "/{user_id}",
    responses={
        403: {"description": "Cannot view another user's sessions."},
    },
)
async def list_sessions(
    user_id: int,
    auth_user_id: Annotated[int, Depends(require_auth)],
    db: Annotated[aiosqlite.Connection, Depends(get_db)],
):
    if user_id != auth_user_id:
        raise HTTPException(
            status_code=403, detail="Cannot view another user's sessions."
        )

    cursor = await db.execute(
        "SELECT id, prototype_id FROM sessions WHERE user_id = ? ORDER BY id",
        (user_id,),
    )
    sessions = await cursor.fetchall()

    result = []
    for session in sessions:
        cursor = await db.execute(
            "SELECT id AS recording_id, cosine_distance, created_at "
            "FROM recordings WHERE session_id = ? ORDER BY created_at",
            (session["id"],),
        )
        recordings = await cursor.fetchall()
        result.append(
            {
                "session_id": session["id"],
                "prototype_id": session["prototype_id"],
                "recordings": [dict(r) for r in recordings],
            }
        )
    return result
