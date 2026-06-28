import os
from typing import AsyncGenerator

import aiosqlite

DB_PATH: str = os.environ.get("DB_PATH", "/data/voicematchr.db")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    token_hash  TEXT    NOT NULL UNIQUE,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS prototypes (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    voice_name    TEXT    NOT NULL,
    speed         REAL    NOT NULL,
    embedding     TEXT    NOT NULL,
    f0_mean       REAL,
    f0_range      REAL,
    hnr           REAL,
    spectral_tilt REAL,
    loudness      REAL,
    created_at    TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS sessions (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      INTEGER NOT NULL REFERENCES users(id),
    prototype_id INTEGER NOT NULL REFERENCES prototypes(id),
    created_at   TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);

CREATE TABLE IF NOT EXISTS recordings (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      INTEGER NOT NULL REFERENCES sessions(id),
    wav_path        TEXT    NOT NULL,
    embedding       TEXT    NOT NULL,
    f0_mean         REAL,
    f0_range        REAL,
    hnr             REAL,
    spectral_tilt   REAL,
    loudness        REAL,
    cosine_distance REAL,
    delta_vector    TEXT,
    coaching_text   TEXT,
    created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_recordings_session ON recordings(session_id);
"""


async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA foreign_keys=ON")
        await db.executescript(_SCHEMA)


async def get_db() -> AsyncGenerator[aiosqlite.Connection, None]:
    async with aiosqlite.connect(DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        await conn.execute("PRAGMA foreign_keys=ON")
        yield conn
