# VoiceMatchr

A multidimensional acoustic feedback web app for self-directed voice-performance practice, helping you get closer to the voice of your choice!

A learner is able to select a synthesized target voice via live in-app recording or sample upload and receive a d speaker-embedding cosine distance to the target

The feedback results are returned as a five-dimension acoustic comparison, template-generated coaching text targeting the largest gap, and a longitudinal chart of distance across vocal submissions.

## Architecture

| Component | Technology | Role |
| --------- | ---------- | ---- |
| `voicematchr-service` | FastAPI, aiosqlite, Resemblyzer, openSMILE eGeMAPSv02, librosa | Analysis API on port 3939: embeddings, feature extraction, scoring, coaching text |
| `frontend` | TanStack Start (React, TypeScript, Tailwind), Nitro node-server | Learner-facing application on port 3000 |
| `nginx` | nginx:alpine | Single entry point on port 80: `/` to the frontend, `/api/` to the service |
| Kokoro TTS | `ghcr.io/remsky/kokoro-fastapi-gpu` (separate host/stack) | Synthesizes the target prototype voices; reached only by the backend |

The five coaching dimensions (F0 mean, F0 range, HNR, spectral tilt, loudness) are
defined once in `app/services/extractor.py` and mirrored in
`frontend/src/constants/dimensions.ts`. The scoring module
(`app/scoring/distance.py`) is pure and I/O-free.

## Quick start

Prerequisites: Docker with the Compose plugin, and a reachable Kokoro TTS instance
(any OpenAI-compatible `/v1/audio/speech` endpoint works).

```bash
cp .env.example .env      # set KOKORO_BASE_URL for your network
docker compose build
docker compose up -d
python3 scripts/seed_prototypes.py   # register the target voicebank
```

Open `http://localhost/`. Full setup, deployment, verification, and evaluation
steps are in `final_implementation_guide.md`.

## Docker Commands

### 1. Stop and remove all containers, networks defined in docker-compose.yml

sudo docker compose down

### 2. Remove dangling images, stopped containers, unused networks, and build cache

sudo docker system prune -f

### 3. Rebuild all images from scratch (no cached layers)

sudo docker compose build --no-cache

### 4. Start all services in detached mode

sudo docker compose up -d

### 5. Confirm container status

sudo docker compose ps

### 6. Tail logs for the VoiceMatchr service specifically

sudo docker compose logs -f voicematchr-service

## Tests

```bash
docker compose exec voicematchr-service pytest -q   # backend, 37 tests
cd frontend && npm run check && npx tsc --noEmit && npm run test
```

## Evaluation data

```bash
docker compose stop voicematchr-service
python3 scripts/export_results.py data/voicematchr.db > results.csv
docker compose start voicematchr-service
```

One CSV row per analyzed recording: session, target voice, submission ordinal,
cosine distance, five signed per-dimension deltas, and the coaching text served.

## License

See `LICENSE`.
