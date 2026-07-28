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


class RecordingSummary(BaseModel):
    """One analyzed submission. `cosine_distance` is the longitudinal y-value."""

    recording_id: int
    cosine_distance: float | None
    created_at: str


class SessionSummary(BaseModel):
    session_id: int
    prototype_id: int
    recordings: list[RecordingSummary]


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


async def _recordings_for_session(
    db: aiosqlite.Connection,
    session_id: int,
) -> list[RecordingSummary]:
    """
    Return the submissions of one session, oldest first.

    Ordered by `id` rather than `created_at`: the schema stores `created_at` at
    one-second resolution (datetime('now')), so two submissions inside the same
    second sort non-deterministically. The autoincrement primary key is strictly
    monotonic in insertion order, which is the ordering the progress chart needs.
    """
    cursor = await db.execute(
        "SELECT id, cosine_distance, created_at "
        "FROM recordings WHERE session_id = ? ORDER BY id",
        (session_id,),
    )
    rows = await cursor.fetchall()
    return [
        RecordingSummary(
            recording_id=row["id"],
            cosine_distance=row["cosine_distance"],
            created_at=row["created_at"],
        )
        for row in rows
    ]


@router.get("/", response_model=list[SessionSummary])
async def list_sessions(
    user_id: Annotated[int, Depends(require_auth)],
    db: Annotated[aiosqlite.Connection, Depends(get_db)],
) -> list[SessionSummary]:
    """
    Return every session owned by the caller, each with its recording history.

    The caller is derived from the Bearer token, not from a path parameter. The
    token is already a per-user credential, so a `user_id` in the path could only
    ever be redundant (equal to the token's user) or forbidden (someone else's) --
    which is why the previous signature needed a 403 ownership check that this one
    makes structurally impossible.
    """
    cursor = await db.execute(
        "SELECT id, prototype_id FROM sessions WHERE user_id = ? ORDER BY id",
        (user_id,),
    )
    rows = await cursor.fetchall()
    return [
        SessionSummary(
            session_id=row["id"],
            prototype_id=row["prototype_id"],
            recordings=await _recordings_for_session(db, row["id"]),
        )
        for row in rows
    ]
