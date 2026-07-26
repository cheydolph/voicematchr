import os
from collections.abc import AsyncGenerator

import aiosqlite

DB_PATH: str = os.environ.get("DB_PATH", "/data/voicematchr.db")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token_hash TEXT NOT NULL UNIQUE,
    demographics TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS prototypes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    voice_name TEXT NOT NULL,
    speed REAL NOT NULL,
    embedding TEXT NOT NULL,
    f0_mean REAL,
    f0_range REAL,
    hnr REAL,
    spectral_tilt REAL,
    loudness REAL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users (id),
    prototype_id INTEGER NOT NULL REFERENCES prototypes (id),
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions (user_id);

CREATE TABLE IF NOT EXISTS recordings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL REFERENCES sessions (id),
    wav_path TEXT NOT NULL,
    embedding TEXT NOT NULL,
    f0_mean REAL,
    f0_range REAL,
    hnr REAL,
    spectral_tilt REAL,
    loudness REAL,
    cosine_distance REAL,
    delta_vector TEXT,
    coaching_text TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_recordings_session ON recordings (session_id);
"""

_PROTOTYPE_DEDUPE = """
UPDATE sessions
SET prototype_id = (
    SELECT MIN(p2.id)
    FROM prototypes p2
    JOIN prototypes p1 ON p1.id = sessions.prototype_id
    WHERE p2.voice_name = p1.voice_name
      AND p2.speed = p1.speed
)
WHERE prototype_id IN (SELECT id FROM prototypes)
  AND prototype_id NOT IN (
    SELECT MIN(id) FROM prototypes GROUP BY voice_name, speed
  );

DELETE FROM prototypes
WHERE id NOT IN (
    SELECT MIN(id) FROM prototypes GROUP BY voice_name, speed
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_prototypes_voice_speed
    ON prototypes (voice_name, speed);
"""


async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute("PRAGMA foreign_keys=ON")
        await db.executescript(_SCHEMA)
        await db.executescript(_PROTOTYPE_DEDUPE)


async def get_db() -> AsyncGenerator[aiosqlite.Connection, None]:
    async with aiosqlite.connect(DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        await conn.execute("PRAGMA foreign_keys=ON")
        yield conn
