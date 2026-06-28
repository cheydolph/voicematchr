# VoiceMatchr — Week 6 Implementation Guide

**Tasks 1–5 | Estimated: 18.5 hours | Deadline: 06/28/2026**

Tasks 6 (Weekly Status Check 1) and 7 (Peer Review) are not covered here; they require no implementation steps.

---

## Architectural Clarification Before Starting

The task list references a `/embed` endpoint (Task 2) and a `/features` endpoint (Task 3) as separate HTTP routes. The finalized proposal architecture eliminated both as public routes and consolidated them into the single `POST /recordings/analyze` endpoint, which calls the Resemblyzer and openSMILE adapters internally through the services layer.

The practical consequence for Week 6 is that Tasks 2 and 3 produce `services/embedder.py` and `services/extractor.py` as services-layer adapters — Python modules with functions that are unit-tested directly — rather than two separate HTTP handlers. The `POST /recordings/analyze` route that calls both is wired up in Week 7 when the scoring module (Task 9) is also in place. By end of Week 6, the services layer should be fully tested in isolation; the HTTP boundary is added on top of it in Week 7.

---

## Task 1 — Repository Initialization and Docker Compose Skeleton

**Estimate: 3.0 hours**

### Step 1.1 — Initialize the repository

```bash
mkdir voicematchr && cd voicematchr
git init
git checkout -b main
```

Create `.gitignore` immediately before touching any other files:

```
# Python
__pycache__/
*.pyc
*.pyo
.venv/
*.egg-info/

# Data (never commit audio or the SQLite database)
data/
*.db
*.wav

# Environment
.env

# Node (Week 7)
node_modules/
frontend/dist/
```

### Step 1.2 — Create the project directory tree

Create all directories and empty `__init__.py` files in a single pass:

```bash
mkdir -p backend/app/{routes,scoring,services,repository,coaching}
mkdir -p backend/tests
mkdir -p data/recordings
touch backend/app/__init__.py
touch backend/app/routes/__init__.py
touch backend/app/scoring/__init__.py
touch backend/app/services/__init__.py
touch backend/app/repository/__init__.py
touch backend/app/coaching/__init__.py
touch backend/tests/__init__.py
touch frontend/.gitkeep
```

The final structure:

```
voicematchr/
├── docker-compose.yml
├── .env
├── .gitignore
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py
│       ├── routes/
│       │   ├── recordings.py
│       │   ├── prototypes.py
│       │   └── sessions.py
│       ├── scoring/
│       │   └── distance.py          (Week 7)
│       ├── services/
│       │   ├── embedder.py          (Task 2)
│       │   ├── extractor.py         (Task 3)
│       │   └── kokoro.py            (Task 4)
│       ├── repository/
│       │   └── db.py
│       └── coaching/
│           ├── templates.py         (Task 5)
│           └── taxonomy.py          (Task 5)
├── backend/tests/
│   ├── conftest.py
│   ├── test_embedder.py
│   └── test_extractor.py
└── data/
    └── recordings/
```

### Step 1.3 — Write the backend Dockerfile

The image needs `libsndfile1` and `ffmpeg` for audio I/O (Resemblyzer and openSMILE both use libsndfile internally).

`backend/Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libsndfile1 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

### Step 1.4 — Write requirements.txt

```
fastapi==0.111.0
uvicorn[standard]==0.30.0
resemblyzer==0.1.1.dev0
opensmile==2.5.0
httpx==0.27.0
aiosqlite==0.20.0
python-multipart==0.0.9
numpy==1.26.4
scipy==1.13.0
pytest==8.2.2
pytest-asyncio==0.23.7
```

If `resemblyzer` cannot be pinned to that version from PyPI, install directly from the repo in requirements.txt:

```
git+https://github.com/resemble-ai/resemblyzer.git
```

### Step 1.5 — Write the environment file

`.env`:

```
KOKORO_BASE_URL=http://host-gateway:8880
DATABASE_URL=sqlite+aiosqlite:////data/voicematchr.db
RECORDINGS_DIR=/data/recordings
```

This file is gitignored. The `KOKORO_BASE_URL` value uses the `host-gateway` alias that Docker Compose resolves to the host machine's IP, allowing the VoiceMatchr backend container to reach the separately-managed Kokoro stack on port 8880 without knowing the host's IP address.

### Step 1.6 — Write docker-compose.yml

```yaml
version: "3.9"

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - KOKORO_BASE_URL=${KOKORO_BASE_URL}
      - DATABASE_URL=${DATABASE_URL}
      - RECORDINGS_DIR=${RECORDINGS_DIR}
    volumes:
      - ./data:/data
      - ./backend/app:/app/app    # hot-reload during development
    extra_hosts:
      - "host-gateway:host-gateway"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 10s
      timeout: 5s
      retries: 3

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./frontend/dist:/usr/share/nginx/html:ro
      - ./nginx.conf:/etc/nginx/conf.d/default.conf:ro
    depends_on:
      - backend
```

The `nginx` service will be useful in Week 7 once the React build exists. For now it will return a 403 on the root since `frontend/dist` is empty, which is expected.

### Step 1.7 — Write a minimal nginx.conf

`nginx.conf`:

```nginx
server {
    listen 80;

    location /api/ {
        proxy_pass http://backend:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location / {
        root /usr/share/nginx/html;
        index index.html;
        try_files $uri $uri/ /index.html;
    }
}
```

### Step 1.8 — Write the FastAPI application entry point

`backend/app/main.py`:

```python
import os
from fastapi import FastAPI
from app.routes import recordings, prototypes, sessions
from app.repository.db import init_db

app = FastAPI(title="VoiceMatchr", version="0.1.0")

app.include_router(recordings.router, prefix="/recordings", tags=["recordings"])
app.include_router(prototypes.router, prefix="/prototypes", tags=["prototypes"])
app.include_router(sessions.router, prefix="/sessions", tags=["sessions"])


@app.on_event("startup")
async def startup():
    await init_db()


@app.get("/health")
async def health():
    return {"status": "ok"}
```

Create stub route files so the import does not fail on startup:

`backend/app/routes/recordings.py`:

```python
from fastapi import APIRouter
router = APIRouter()
```

`backend/app/routes/prototypes.py`:

```python
from fastapi import APIRouter
router = APIRouter()
```

`backend/app/routes/sessions.py`:

```python
from fastapi import APIRouter
router = APIRouter()
```

### Step 1.9 — Write the SQLite schema

The full schema is written now because prototype storage (Task 4) requires it. Write it once rather than piecemeal.

`backend/app/repository/db.py`:

```python
import os
import aiosqlite

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite+aiosqlite:////data/voicematchr.db")
# aiosqlite uses a plain path; strip the driver prefix.
DB_PATH = DATABASE_URL.replace("sqlite+aiosqlite://", "")

SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS users (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    token_hash  TEXT    NOT NULL UNIQUE,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS prototypes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    voice_name  TEXT    NOT NULL,
    speed       REAL    NOT NULL,
    embedding   TEXT    NOT NULL,   -- JSON float array, 256 dims
    f0_mean     REAL,
    f0_range    REAL,
    hnr         REAL,
    spectral_tilt REAL,
    loudness    REAL,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS sessions (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      INTEGER NOT NULL REFERENCES users(id),
    prototype_id INTEGER NOT NULL REFERENCES prototypes(id),
    created_at   TEXT    NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);

CREATE TABLE IF NOT EXISTS recordings (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id       INTEGER NOT NULL REFERENCES sessions(id),
    wav_path         TEXT    NOT NULL,
    embedding        TEXT    NOT NULL,   -- JSON float array, 256 dims
    f0_mean          REAL,
    f0_range         REAL,
    hnr              REAL,
    spectral_tilt    REAL,
    loudness         REAL,
    cosine_distance  REAL,
    delta_vector     TEXT,   -- JSON object keyed by dimension name
    coaching_text    TEXT,
    created_at       TEXT    NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_recordings_session ON recordings(session_id);
"""


async def get_db() -> aiosqlite.Connection:
    conn = await aiosqlite.connect(DB_PATH)
    conn.row_factory = aiosqlite.Row
    await conn.execute("PRAGMA foreign_keys=ON")
    return conn


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(SCHEMA)
        await db.commit()
```

### Step 1.10 — Verify the skeleton

```bash
docker compose build
docker compose up -d
curl http://localhost:8000/health
# Expected: {"status":"ok"}
docker compose logs backend
```

Confirm no import errors appear in the logs. The health check endpoint should respond before moving on.

---

## Task 2 — Resemblyzer Services Adapter

**Estimate: 4.0 hours**

The task list calls this "implement /embed endpoint." In the finalized architecture this is the Resemblyzer adapter in the services layer: a module with a single public function that the `POST /recordings/analyze` route (Week 7) and the `POST /prototypes` route (Task 4) will both call. Unit tests target the function directly.

### Step 2.1 — Understand what Resemblyzer provides

Resemblyzer wraps a GE2E-trained LSTM speaker encoder. `preprocess_wav` resamples audio to 16 kHz and trims leading and trailing silence. `embed_utterance` runs the encoder over overlapping 1.6-second windows and mean-pools the frame-level embeddings into a single 256-dimensional L2-normalized vector. Cosine similarity between two such vectors is the voice-similarity scalar that drives the convergence metric.

### Step 2.2 — Write services/embedder.py

`backend/app/services/embedder.py`:

```python
from __future__ import annotations

import threading
from pathlib import Path

import numpy as np
from resemblyzer import VoiceEncoder, preprocess_wav

# Module-level singleton. VoiceEncoder downloads a ~17 MB checkpoint on first
# instantiation; the lock ensures only one thread initializes it if the server
# starts multiple workers.
_lock = threading.Lock()
_encoder: VoiceEncoder | None = None


def _get_encoder() -> VoiceEncoder:
    global _encoder
    if _encoder is None:
        with _lock:
            if _encoder is None:
                _encoder = VoiceEncoder()
    return _encoder


def compute_embedding(wav_path: str | Path) -> list[float]:
    """
    Compute a 256-dimensional L2-normalized speaker embedding for the WAV file
    at `wav_path` using the Resemblyzer GE2E encoder.

    The returned list is JSON-serializable (Python floats, not numpy floats).
    Raises FileNotFoundError if the path does not exist.
    Raises ValueError if the audio is too short to embed (< ~1.6 seconds after
    silence trimming).
    """
    path = Path(wav_path)
    if not path.exists():
        raise FileNotFoundError(f"WAV not found: {path}")

    wav = preprocess_wav(path)

    if len(wav) < 16_000:
        raise ValueError(
            f"Audio too short after preprocessing ({len(wav)} samples). "
            "Minimum is approximately 1.6 seconds of speech after silence trimming."
        )

    encoder = _get_encoder()
    embedding: np.ndarray = encoder.embed_utterance(wav)
    return embedding.tolist()
```

### Step 2.3 — Write unit tests for the embedder

The tests need a real short WAV file. Generate one with `scipy` so the test suite has no external dependencies.

`backend/tests/conftest.py`:

```python
import numpy as np
import pytest
import wave
from pathlib import Path


@pytest.fixture(scope="session")
def tmp_wav(tmp_path_factory) -> Path:
    """
    Write a 3-second 16 kHz mono WAV file containing a 440 Hz sine tone.
    This is long enough for Resemblyzer to embed and for openSMILE to process.
    """
    tmp = tmp_path_factory.mktemp("audio")
    path = tmp / "probe.wav"
    sample_rate = 16_000
    duration = 3.0
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    signal = (np.sin(2 * np.pi * 440 * t) * 32767).astype(np.int16)
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(signal.tobytes())
    return path
```

`backend/tests/test_embedder.py`:

```python
import numpy as np
import pytest
from pathlib import Path
from app.services.embedder import compute_embedding


def test_embedding_shape(tmp_wav):
    emb = compute_embedding(tmp_wav)
    assert len(emb) == 256, f"Expected 256 dims, got {len(emb)}"


def test_embedding_type(tmp_wav):
    emb = compute_embedding(tmp_wav)
    assert all(isinstance(v, float) for v in emb), "All values must be Python floats"


def test_embedding_normalized(tmp_wav):
    emb = compute_embedding(tmp_wav)
    norm = np.linalg.norm(emb)
    assert abs(norm - 1.0) < 1e-5, f"Embedding not unit-normalized: norm={norm}"


def test_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        compute_embedding("/nonexistent/path/to/audio.wav")


def test_deterministic(tmp_wav):
    emb1 = compute_embedding(tmp_wav)
    emb2 = compute_embedding(tmp_wav)
    assert emb1 == emb2, "Same file must produce the same embedding"
```

### Step 2.4 — Run the tests

Run inside the container to ensure the Docker environment matches production:

```bash
docker compose exec backend pytest tests/test_embedder.py -v
```

All five tests must pass before moving to Task 3. If `resemblyzer` fails to download the checkpoint (network restriction inside the container), download it on the host first and mount it:

```bash
python -c "from resemblyzer import VoiceEncoder; VoiceEncoder()"
# This writes the checkpoint to ~/.cache/torch/resemblyzer/
```

Then add a volume mount in `docker-compose.yml`:

```yaml
volumes:
  - ~/.cache/torch:/root/.cache/torch:ro
```

---

## Task 3 — openSMILE GeMAPS Services Adapter

**Estimate: 3.5 hours**

### Step 3.1 — Understand what openSMILE eGeMAPS provides

The `opensmile` Python package wraps the C++ openSMILE binary. With `FeatureSet.eGeMAPSv02` and `FeatureLevel.Functionals`, it extracts a single row of summary statistics (means, standard deviations, percentiles) over the full utterance. The five features this project uses and their eGeMAPSv02 column names are:

| Dimension | eGeMAPSv02 column | Interpretation |
|---|---|---|
| `f0_mean` | `F0semitoneFrom27.5Hz_sma3nz_amean` | Mean pitch in semitones above 27.5 Hz |
| `f0_range` | `F0semitoneFrom27.5Hz_sma3nz_stddevNorm` | Normalized std dev of pitch (proxy for intonation range) |
| `hnr` | `HNRdBACF_sma3nz_amean` | Mean harmonics-to-noise ratio in dB |
| `spectral_tilt` | `alphaRatioV_sma3nz_amean` | Alpha ratio: energy < 1 kHz vs > 1 kHz (vocal brightness) |
| `loudness` | `loudness_sma3_amean` | Mean equivalent sound level |

On first run, print `smile.feature_names` to verify these column names match the installed package version before hardcoding them.

### Step 3.2 — Write services/extractor.py

`backend/app/services/extractor.py`:

```python
from __future__ import annotations

import threading
from pathlib import Path

import opensmile

# The five acoustic dimensions used by the radar chart, coaching text templates,
# and per-dimension delta ranking. Order is fixed; do not reorder without
# updating templates.py and the DB schema.
DIMENSIONS: list[str] = [
    "f0_mean",
    "f0_range",
    "hnr",
    "spectral_tilt",
    "loudness",
]

# Mapping from project dimension name to eGeMAPSv02 functional column name.
_COLUMN_MAP: dict[str, str] = {
    "f0_mean":       "F0semitoneFrom27.5Hz_sma3nz_amean",
    "f0_range":      "F0semitoneFrom27.5Hz_sma3nz_stddevNorm",
    "hnr":           "HNRdBACF_sma3nz_amean",
    "spectral_tilt": "alphaRatioV_sma3nz_amean",
    "loudness":      "loudness_sma3_amean",
}

_lock = threading.Lock()
_smile: opensmile.Smile | None = None


def _get_smile() -> opensmile.Smile:
    global _smile
    if _smile is None:
        with _lock:
            if _smile is None:
                _smile = opensmile.Smile(
                    feature_set=opensmile.FeatureSet.eGeMAPSv02,
                    feature_level=opensmile.FeatureLevel.Functionals,
                )
    return _smile


def extract_features(wav_path: str | Path) -> dict[str, float]:
    """
    Extract the five coaching dimensions from `wav_path` using eGeMAPSv02
    functionals.

    Returns a dict keyed by DIMENSIONS with Python float values.
    Raises FileNotFoundError if the path does not exist.
    Raises RuntimeError if any expected column is absent from the openSMILE
    output (column name mismatch across package versions).
    """
    path = Path(wav_path)
    if not path.exists():
        raise FileNotFoundError(f"WAV not found: {path}")

    smile = _get_smile()
    result = smile.process_file(str(path))
    row = result.iloc[0]

    missing = [col for col in _COLUMN_MAP.values() if col not in row.index]
    if missing:
        raise RuntimeError(
            f"Expected eGeMAPSv02 columns not found in openSMILE output: {missing}. "
            f"Available columns: {row.index.tolist()}"
        )

    return {dim: float(row[col]) for dim, col in _COLUMN_MAP.items()}


def feature_vector(wav_path: str | Path) -> list[float]:
    """
    Return extracted features as an ordered list matching DIMENSIONS.
    Suitable for JSON serialization and delta computation.
    """
    feats = extract_features(wav_path)
    return [feats[d] for d in DIMENSIONS]
```

### Step 3.3 — Write unit tests for the extractor

`backend/tests/test_extractor.py`:

```python
import pytest
from app.services.extractor import extract_features, feature_vector, DIMENSIONS


def test_returns_all_dimensions(tmp_wav):
    feats = extract_features(tmp_wav)
    assert set(feats.keys()) == set(DIMENSIONS), (
        f"Missing dimensions: {set(DIMENSIONS) - set(feats.keys())}"
    )


def test_all_values_are_float(tmp_wav):
    feats = extract_features(tmp_wav)
    for dim, val in feats.items():
        assert isinstance(val, float), f"Dimension {dim} returned {type(val)}, expected float"


def test_feature_vector_length(tmp_wav):
    vec = feature_vector(tmp_wav)
    assert len(vec) == len(DIMENSIONS)


def test_feature_vector_order(tmp_wav):
    feats = extract_features(tmp_wav)
    vec = feature_vector(tmp_wav)
    for i, dim in enumerate(DIMENSIONS):
        assert vec[i] == feats[dim], f"Ordering mismatch at index {i} ({dim})"


def test_missing_file_raises(tmp_wav):
    with pytest.raises(FileNotFoundError):
        extract_features("/nonexistent/audio.wav")


def test_f0_mean_nonnegative(tmp_wav):
    # F0 in semitones from 27.5 Hz is always >= 0 for voiced audio.
    feats = extract_features(tmp_wav)
    assert feats["f0_mean"] >= 0.0
```

### Step 3.4 — Run the tests

```bash
docker compose exec backend pytest tests/test_extractor.py -v
```

If the column name check in the `RuntimeError` branch fires, print available columns and update `_COLUMN_MAP` accordingly:

```bash
docker compose exec backend python -c "
import opensmile
s = opensmile.Smile(
    feature_set=opensmile.FeatureSet.eGeMAPSv02,
    feature_level=opensmile.FeatureLevel.Functionals,
)
print(s.feature_names)
"
```

Locate the F0, HNR, alpha ratio, and loudness column names in the printed list and update `_COLUMN_MAP` if they differ from the values in Step 3.2.

---

## Task 4 — Kokoro TTS External Stack and Prototype Registration

**Estimate: 4.0 hours**

### Step 4.1 — Confirm the Kokoro TTS stack is running

The Kokoro TTS stack (`ghcr.io/remsky/kokoro-fastapi-gpu`) is managed independently and is not defined in VoiceMatchr's `docker-compose.yml`. Verify it is reachable before writing any application code:

```bash
# From the host machine
curl -s http://localhost:8880/v1/voices | python3 -m json.tool | head -30
```

If that returns a JSON voices list, the stack is running. If not:

```bash
# In your separately-managed Kokoro directory
docker compose up -d
# Wait ~30 seconds for model load, then re-curl
```

To confirm VoiceMatchr's backend container can reach Kokoro via `host-gateway`:

```bash
docker compose exec backend curl -s http://host-gateway:8880/v1/voices | head -5
```

You should see the same voices JSON. If `host-gateway` resolves but the connection is refused, verify the Kokoro container is publishing port 8880 to the host.

### Step 4.2 — Write services/kokoro.py

`backend/app/services/kokoro.py`:

```python
from __future__ import annotations

import os
import httpx

KOKORO_BASE_URL: str = os.environ.get("KOKORO_BASE_URL", "http://host-gateway:8880")

# A short standardized probe passage used for all prototype synthesis.
# It covers a range of phonetic environments to produce a representative
# voice sample. Keep it constant across all prototypes so acoustic feature
# comparisons are passage-controlled.
PROBE_PASSAGE: str = (
    "The quick brown fox jumps over the lazy dog. "
    "She sells seashells by the seashore. "
    "How much wood would a woodchuck chuck if a woodchuck could chuck wood?"
)


async def synthesize_wav(
    voice: str,
    speed: float,
    text: str = PROBE_PASSAGE,
) -> bytes:
    """
    Post to the external Kokoro FastAPI service and return raw WAV bytes.

    Args:
        voice: One of the 54 Kokoro v1.0 voice names (e.g. 'af_bella',
               'am_adam'). Voice-mixing syntax ('voice1+voice2') is also
               accepted for intermediate acoustic profiles.
        speed: Speaking-rate multiplier. Typical range 0.7–1.3.
        text:  Passage to synthesize. Defaults to PROBE_PASSAGE.

    Raises:
        httpx.HTTPStatusError: If Kokoro returns a non-2xx status.
        httpx.ConnectError: If the Kokoro service is unreachable.
    """
    payload = {
        "model": "kokoro",
        "voice": voice,
        "input": text,
        "speed": speed,
        "response_format": "wav",
    }
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{KOKORO_BASE_URL}/v1/audio/speech",
            json=payload,
        )
        response.raise_for_status()
        return response.content
```

The 120-second timeout accommodates cold-start synthesis on the first request after GPU warmup. Subsequent requests will be faster.

### Step 4.3 — Write routes/prototypes.py

This implements `POST /prototypes` (prototype registration) and `GET /prototypes` (prototype listing) per the proposal. `POST /prototypes` routes through the shared services-layer pipeline — the same `embedder.compute_embedding` and `extractor.extract_features` functions used for learner recordings.

`backend/app/routes/prototypes.py`:

```python
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.repository.db import get_db
from app.services import embedder, extractor, kokoro

router = APIRouter()


class PrototypeCreate(BaseModel):
    voice_name: str
    speed: float = 1.0


class PrototypeResponse(BaseModel):
    id: int
    voice_name: str
    speed: float
    f0_mean: float | None
    f0_range: float | None
    hnr: float | None
    spectral_tilt: float | None
    loudness: float | None


@router.post("/", response_model=PrototypeResponse, status_code=201)
async def create_prototype(body: PrototypeCreate):
    """
    Synthesize a prototype voice using the Kokoro TTS service, compute its
    Resemblyzer embedding and eGeMAPSv02 feature vector through the shared
    services-layer pipeline, and persist the result.
    """
    # 1. Synthesize WAV from Kokoro.
    try:
        wav_bytes = await kokoro.synthesize_wav(body.voice_name, body.speed)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Kokoro synthesis failed: {exc}")

    # 2. Write to a temp file so both embedder and extractor can read it.
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(wav_bytes)
        tmp_path = tmp.name

    try:
        embedding = embedder.compute_embedding(tmp_path)
        feats = extractor.extract_features(tmp_path)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {exc}")
    finally:
        os.unlink(tmp_path)

    # 3. Persist.
    async with await get_db() as db:
        cursor = await db.execute(
            """
            INSERT INTO prototypes
                (voice_name, speed, embedding, f0_mean, f0_range, hnr,
                 spectral_tilt, loudness)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                body.voice_name,
                body.speed,
                json.dumps(embedding),
                feats["f0_mean"],
                feats["f0_range"],
                feats["hnr"],
                feats["spectral_tilt"],
                feats["loudness"],
            ),
        )
        await db.commit()
        prototype_id = cursor.lastrowid

    return PrototypeResponse(
        id=prototype_id,
        voice_name=body.voice_name,
        speed=body.speed,
        **feats,
    )


@router.get("/", response_model=list[PrototypeResponse])
async def list_prototypes():
    async with await get_db() as db:
        cursor = await db.execute(
            "SELECT id, voice_name, speed, f0_mean, f0_range, hnr, "
            "spectral_tilt, loudness FROM prototypes ORDER BY id"
        )
        rows = await cursor.fetchall()
    return [PrototypeResponse(**dict(row)) for row in rows]
```

Update `main.py` to replace the stub import with this real implementation (it already imports from `app.routes.prototypes`, so no change to `main.py` is needed — the stub router in `prototypes.py` is simply replaced by the full file above).

### Step 4.4 — Register the first voicebank prototype set

Restart the backend after writing the new prototypes route:

```bash
docker compose restart backend
```

The proposal specifies "three to five pre-registered Kokoro prototype voices" for the onboarding flow. Register an initial set covering distinct acoustic profiles:

```bash
# Prototype 1: measured lower-register voice
curl -X POST http://localhost:8000/prototypes/ \
  -H "Content-Type: application/json" \
  -d '{"voice_name": "am_adam", "speed": 0.9}'

# Prototype 2: brighter higher-register voice
curl -X POST http://localhost:8000/prototypes/ \
  -H "Content-Type: application/json" \
  -d '{"voice_name": "af_bella", "speed": 1.0}'

# Prototype 3: midpoint option via voice mixing
curl -X POST http://localhost:8000/prototypes/ \
  -H "Content-Type: application/json" \
  -d '{"voice_name": "am_adam+af_bella", "speed": 1.0}'

# Prototype 4: faster energetic variant
curl -X POST http://localhost:8000/prototypes/ \
  -H "Content-Type: application/json" \
  -d '{"voice_name": "af_nicole", "speed": 1.1}'

# Prototype 5: slower deliberate variant
curl -X POST http://localhost:8000/prototypes/ \
  -H "Content-Type: application/json" \
  -d '{"voice_name": "am_michael", "speed": 0.85}'
```

Each call will take 10–60 seconds on first execution (GPU warmup + Resemblyzer model load). Subsequent calls are faster.

### Step 4.5 — Verify stored embeddings

```bash
curl http://localhost:8000/prototypes/
```

Confirm all five prototypes are returned with non-null values for all five acoustic dimensions. If any dimension is `null`, the extractor column mapping needs to be corrected per Step 3.4.

---

## Task 5 — Coaching Text Taxonomy and Template Bank

**Estimate: 4.0 hours**

### Step 5.1 — Document the taxonomy

Before writing any code, record the four-dimension taxonomy structure that every template must instantiate. This document is the specification against which templates are reviewed.

`backend/app/coaching/taxonomy.py`:

```python
"""
Coaching text taxonomy for VoiceMatchr.

Every coaching paragraph produced by the template generator must instantiate
all four dimensions of this taxonomy simultaneously. A template that satisfies
only two or three dimensions is incomplete and must be revised.

DIMENSION 1 — Specificity  (Kluger & DeNisi, 1996)
    The opening sentence names the acoustic parameter being addressed and
    quantifies the current gap. It does not evaluate overall quality or
    rate the learner's performance globally.
    BAD:  "Good effort, but your voice needs work."
    GOOD: "Your average pitch on this attempt sits 3.2 semitones above the target."

DIMENSION 2 — Behavioral Directiveness  (Hattie & Timperley, 2007 — feed-forward)
    The template contains an imperative specifying exactly what the learner
    should change on the next recording. It does not describe what was wrong;
    it prescribes what to do differently.
    BAD:  "Your pitch was too high."
    GOOD: "On your next recording, bring your voice down by relaxing the muscles
           at the base of your tongue."

DIMENSION 3 — Physiological Grounding  (Molloy, 2021)
    The behavioral directive is paired with a kinesthetic or body-sensation
    cue. Abstract acoustic parameter language ("increase spectral tilt") is
    translated into a sensation the learner can reproduce without a spectrogram.
    BAD:  "Increase your alpha ratio by adjusting resonance placement."
    GOOD: "Let resonance move forward in your mouth — think of the sound sitting
           just behind your front teeth."

DIMENSION 4 — Autonomy-Supportive Register  (Carpentier & Mageau, 2016)
    The closing sentence or phrase preserves learner agency. It invites the
    learner to try and observe, rather than demanding compliance or implying
    failure. Modal verbs ("might," "could," "see whether") and observation
    invitations ("notice whether," "see if you can") are preferred over
    commands ("you must," "make sure you").
    BAD:  "Make sure you do this on the next attempt."
    GOOD: "Try the passage again and notice whether the tone becomes cleaner."
"""

# Canonical dimension registry. The scoring module uses this list to rank
# per-dimension deltas; the template selector indexes into TEMPLATES by these keys.
DIMENSIONS: list[str] = [
    "f0_mean",
    "f0_range",
    "hnr",
    "spectral_tilt",
    "loudness",
]

DIMENSION_LABELS: dict[str, str] = {
    "f0_mean":       "Average Pitch",
    "f0_range":      "Pitch Variation",
    "hnr":           "Voice Clarity",
    "spectral_tilt": "Vocal Brightness",
    "loudness":      "Loudness",
}
```

### Step 5.2 — Write the template bank

Each dimension has two templates: `"above"` (learner value exceeds prototype value) and `"below"` (learner value falls short). Each template is a Python format string accepting a `{delta}` positional value (the absolute magnitude of the gap in the relevant unit).

Every template is reviewed against all four taxonomy dimensions before it is accepted. The acceptance checklist for each template:

- Sentence 1 names the dimension and states the delta numerically. (Specificity)
- At least one imperative sentence beginning with "On your next recording" or "Try." (Behavioral directiveness)
- At least one phrase anchoring the instruction to a body sensation or spatial image. (Physiological grounding)
- The final sentence uses a modal or invitation construction. (Autonomy-supportive register)

`backend/app/coaching/templates.py`:

```python
"""
Dimension-specific template bank for the VoiceMatchr coaching text generator.

Each key is a dimension name from taxonomy.DIMENSIONS. Each value is a dict
with keys "above" and "below" mapping to format strings that accept a single
keyword argument `delta` (float, absolute gap magnitude in dimension-specific
units).

Template authoring rules:
  - Do not add bolding, markdown, or HTML. Output is plain prose.
  - Keep each template to three to five sentences.
  - Every template must pass the four-dimension taxonomy checklist in taxonomy.py
    before being committed.
  - Do not hedge ("might be," "possibly"). State the measurement as a fact.
"""

from __future__ import annotations

TEMPLATES: dict[str, dict[str, str]] = {

    "f0_mean": {
        "above": (
            "Your average pitch on this attempt sits about {delta:.1f} semitones above the target. "
            "On your next recording, bring your voice down by relaxing the muscles at the base of "
            "your tongue and letting your larynx settle lower in your throat — imagine the sound "
            "originating in your chest rather than behind your eyes. "
            "Try the passage again and see whether you can sustain that lower center without "
            "letting the pitch rise at the ends of phrases."
        ),
        "below": (
            "Your average pitch on this attempt sits about {delta:.1f} semitones below the target. "
            "On your next recording, let your voice lift by thinking of the sound arcing forward "
            "and upward — place it behind your front teeth rather than in your throat. "
            "Read the passage again and allow yourself to reach for the upper end of your "
            "comfortable range on stressed syllables, and notice whether the center settles higher."
        ),
    },

    "f0_range": {
        "above": (
            "Your pitch variation on this attempt is wider than the target by about "
            "{delta:.2f} normalized units. "
            "On your next recording, narrow your intonation arc: let most syllables land at a "
            "similar level and reserve pitch movement for only the most semantically important words. "
            "Think of your voice as a line that stays level except at deliberate peaks, "
            "and see if you can reduce the overall sweep while keeping the delivery from sounding flat."
        ),
        "below": (
            "Your pitch variation on this attempt fell about {delta:.2f} normalized units short "
            "of the target. "
            "On your next recording, widen the arc of your intonation — imagine your voice lifting "
            "into the room as each phrase rises and landing with weight on the final stressed syllable. "
            "Try reading the passage again and let the ends of sentences land higher or lower than "
            "feels entirely natural, and notice whether the overall arc becomes more expressive."
        ),
    },

    "hnr": {
        "above": (
            "Your voice on this attempt is cleaner than the target, with an HNR gap "
            "of about {delta:.1f} dB. "
            "On your next recording, allow a small amount of breath to mix into the tone — "
            "think of letting your breath and voice travel the same channel without holding "
            "the air back, as though the tone is being carried outward on a slow exhale. "
            "A slight relaxation of your glottal closure on sustained vowels may help you "
            "match the prototype's texture; try the passage and see whether the voice feels "
            "slightly more open."
        ),
        "below": (
            "Your voice on this attempt is breathier than the target, with an HNR gap "
            "of about {delta:.1f} dB. "
            "On your next recording, bring the edges of your vocal folds into firmer contact "
            "by thinking of the sound as having a narrow, focused core — imagine projecting "
            "toward a specific point across the room and keeping the tone tightly aimed at that point. "
            "Try the passage again and notice whether the voice feels cleaner and more "
            "forward-placed when you maintain that imagined target."
        ),
    },

    "spectral_tilt": {
        "above": (
            "The brightness of your voice on this attempt is above the target by about "
            "{delta:.2f} alpha-ratio units. "
            "On your next recording, warm the tone by directing resonance toward the back of "
            "your mouth — let the sound feel fuller behind your upper molars rather than in "
            "front of your lips, and allow your lips to close slightly on rounded vowels. "
            "Try the passage again with a slightly more relaxed, back-placed resonance and "
            "see whether the tone becomes warmer without losing its projection."
        ),
        "below": (
            "The brightness of your voice on this attempt is below the target by about "
            "{delta:.2f} alpha-ratio units. "
            "On your next recording, brighten the tone by letting resonance move forward in "
            "your mouth — think of the sound sitting just behind your front teeth, or of "
            "projecting to a point above the listener's eye level. "
            "Try the passage again with a slightly more open upper-resonance space and "
            "notice whether the sound becomes cleaner and more forward-placed."
        ),
    },

    "loudness": {
        "above": (
            "Your overall loudness on this attempt is about {delta:.2f} units above the target. "
            "On your next recording, reduce your projection slightly — think of directing the "
            "sound toward a listener two or three feet away rather than across a large room, "
            "and let your breath support the tone without pushing from behind it. "
            "Try the passage at a conversational level and see whether the volume settles "
            "closer to the target while the tone stays clear."
        ),
        "below": (
            "Your overall loudness on this attempt is about {delta:.2f} units below the target. "
            "On your next recording, increase your projection by imagining you are speaking to "
            "someone just past the back of the room — feel your breath expand outward from your "
            "lower ribcage rather than from your chest or throat. "
            "Try the passage again with that expanded breath support and notice whether the "
            "volume increases without added tension in your neck or jaw."
        ),
    },
}


def select_template(dimension: str, direction: str, delta: float) -> str:
    """
    Return a rendered coaching paragraph for `dimension`.

    Args:
        dimension: One of taxonomy.DIMENSIONS.
        direction: "above" if learner value > prototype value, else "below".
        delta: Absolute magnitude of the gap (prototype value - learner value
               if below, or learner value - prototype value if above).

    Raises:
        KeyError: If `dimension` or `direction` is not in TEMPLATES.
    """
    template = TEMPLATES[dimension][direction]
    return template.format(delta=delta)
```

### Step 5.3 — Write a smoke test for the template bank

This is not a unit test of business logic but a structural check that every required key is present and every template renders without error.

Add to `backend/tests/test_extractor.py` or create `backend/tests/test_templates.py`:

```python
from app.coaching.templates import TEMPLATES, select_template
from app.coaching.taxonomy import DIMENSIONS


def test_all_dimensions_present():
    for dim in DIMENSIONS:
        assert dim in TEMPLATES, f"Missing template for dimension: {dim}"


def test_both_directions_present():
    for dim in DIMENSIONS:
        assert "above" in TEMPLATES[dim], f"Missing 'above' template for {dim}"
        assert "below" in TEMPLATES[dim], f"Missing 'below' template for {dim}"


def test_templates_render_without_error():
    for dim in DIMENSIONS:
        for direction in ("above", "below"):
            rendered = select_template(dim, direction, delta=1.23)
            assert isinstance(rendered, str)
            assert len(rendered) > 20, f"Template too short: {dim}/{direction}"


def test_delta_substituted():
    rendered = select_template("f0_mean", "above", delta=3.7)
    assert "3.7" in rendered, "delta value not found in rendered template"
```

```bash
docker compose exec backend pytest tests/test_templates.py -v
```

---

## End-of-Week Verification Checklist

Before submitting the status check, confirm each item:

**Task 1**
- `docker compose up -d` starts without errors
- `curl http://localhost:8000/health` returns `{"status":"ok"}`
- SQLite database file is created at `data/voicematchr.db` on startup
- All four tables (`users`, `prototypes`, `sessions`, `recordings`) exist: `sqlite3 data/voicematchr.db ".tables"`

**Task 2**
- All five embedder tests pass: `pytest tests/test_embedder.py -v`
- Embeddings are 256-dimensional and unit-normalized

**Task 3**
- All six extractor tests pass: `pytest tests/test_extractor.py -v`
- Column names verified against the installed openSMILE version; `_COLUMN_MAP` updated if needed

**Task 4**
- `curl http://host-gateway:8880/v1/voices` is reachable from inside the backend container
- `GET http://localhost:8000/prototypes/` returns five records with non-null values for all five acoustic dimensions
- All five prototype embeddings are 256-dimensional (check one: `sqlite3 data/voicematchr.db "SELECT length(embedding) FROM prototypes LIMIT 1"` — the JSON string will be long; verify the parsed array has 256 elements)

**Task 5**
- All template smoke tests pass: `pytest tests/test_templates.py -v`
- Each of the ten templates (five dimensions × two directions) passes the four-dimension taxonomy checklist manually: specificity, behavioral directiveness, physiological grounding, autonomy-supportive register

**All tasks combined**
- Full test suite passes: `pytest tests/ -v`
- Git commit with a meaningful message covering all five task completions

---

## What Week 7 Builds On Top of This

The services layer is intentionally complete by end of Week 6. Week 7 (Tasks 8–11) adds: the React frontend audio recorder, the `scoring/distance.py` module for cosine distance and per-dimension delta ranking, the `POST /recordings/analyze` route that wires `embedder`, `extractor`, `scoring`, and the coaching text generator into a single endpoint, and the prototype selection onboarding screen. The Intermediate Milestone 1 video is also recorded and submitted in Week 7. Nothing in Week 7 requires reopening or modifying any of the files written this week.
