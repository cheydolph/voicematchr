from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.repository.db import init_db
from app.routes import prototypes, recordings, sessions, users


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_db()
    yield


app = FastAPI(title="VoiceMatchr", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
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
