import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.repository.db import init_db
from app.routes import prototypes, recordings, sessions, users

# CORS is required only for `npm run dev`, where the Vite server on :3000 calls the
# backend on :3939 directly (TanStack Start's SSR router intercepts /api/* before
# Vite's proxy middleware, so a dev proxy is not an option). In the composed
# deployment nginx serves both the frontend and /api/ from a single origin, so no
# preflight occurs. The variable exists so that a future non-same-origin deployment
# does not require a code change.
DEFAULT_CORS_ORIGIN = "http://localhost:3000"


def cors_allow_origins() -> list[str]:
    """Parse CORS_ALLOW_ORIGINS (comma-separated) into a list of origins."""
    raw = os.environ.get("CORS_ALLOW_ORIGINS", DEFAULT_CORS_ORIGIN)
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_db()
    yield


app = FastAPI(title="VoiceMatchr", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_allow_origins(),
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(recordings.router, prefix="/recordings", tags=["recordings"])
app.include_router(prototypes.router, prefix="/prototypes", tags=["prototypes"])
app.include_router(sessions.router, prefix="/sessions", tags=["sessions"])
app.include_router(users.router, prefix="/users", tags=["users"])


@app.get("/health")
async def health():
    return {"status": "ok"}
