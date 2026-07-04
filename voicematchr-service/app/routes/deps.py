from __future__ import annotations

import hashlib
from typing import Annotated

import aiosqlite
from fastapi import Depends, Header, HTTPException

from app.repository.db import get_db


async def require_auth(
    authorization: Annotated[str, Header(...)],
    db: Annotated[aiosqlite.Connection, Depends(get_db)],
) -> int:
    """Validate a Bearer token and return the associated user_id. Raises 401 on failure."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    raw = authorization.removeprefix("Bearer ")
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    cursor = await db.execute(
        "SELECT id FROM users WHERE token_hash = ?", (token_hash,)
    )
    row = await cursor.fetchone()
    if row is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    return row["id"]
