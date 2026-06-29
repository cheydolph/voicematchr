from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.repository.db import init_db
from app.routes import prototypes, recordings, sessions


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_db()
    yield


app = FastAPI(title="VoiceMatchr", version="0.1.0", lifespan=lifespan)

app.include_router(recordings.router, prefix="/recordings", tags=["recordings"])
app.include_router(prototypes.router, prefix="/prototypes", tags=["prototypes"])
app.include_router(sessions.router, prefix="/sessions", tags=["sessions"])


@app.get("/health")
async def health():
    return {"status": "ok"}
