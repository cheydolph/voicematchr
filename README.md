# VoiceMatchr

A multidimensional acoustic feedback web app for self-directed voice-performance
practice, helping you get closer to the voice of your choice!

A learner selects a synthesized target voice, submits a practice recording via
live in-app capture or file upload, and receives a speaker-embedding cosine
distance to the target. Feedback is returned as a five-dimension acoustic
comparison, template-generated coaching text targeting the largest gap, and a
longitudinal chart of distance across submissions.

## Live deployment

The application is deployed and publicly reachable at
[voicematchr.fiestaszn.com](https://voicematchr.fiestaszn.com/).
Deployment runs on a TrueNAS SCALE host as a Dockge-managed Docker Compose
stack, exposed through a Cloudflare Tunnel; see the
[stack implementation guide](z_voicematchr_stack_implementation_guide/STACK_IMPLEMENTATION_GUIDE.md)
for the full setup, verification, and operational reference.

## Architecture

| Component | Technology | Role |
| --------- | ---------- | ---- |
| `voicematchr-service` | FastAPI, aiosqlite, Resemblyzer, openSMILE eGeMAPSv02, librosa | Analysis API on port 3939: embeddings, feature extraction, scoring, coaching text |
| `frontend` | TanStack Start (React, TypeScript, Tailwind), Nitro node-server | Learner-facing application on port 3000 |
| `nginx` | nginx:alpine | Single entry point on port 80: `/` to the frontend, `/api/` to the service |
| `cloudflared` | cloudflare/cloudflared | Supervised tunnel connector publishing nginx at the public HTTPS hostname |
| Kokoro TTS | `ghcr.io/remsky/kokoro-fastapi-gpu` (separate stack, same host) | Synthesizes the target prototype voices; reached only by the backend over the shared `kokoro-net` Docker network |

The five coaching dimensions (F0 mean, F0 range, HNR, spectral tilt, loudness)
are defined once in `app/services/extractor.py` and mirrored in
`frontend/src/constants/dimensions.ts`. The scoring module
(`app/scoring/distance.py`) is pure and I/O-free.

## Quick start

Prerequisites: Docker with the Compose plugin, and a reachable Kokoro TTS
instance (any OpenAI-compatible `/v1/audio/speech` endpoint works).

```bash
cp .env.example .env      # set KOKORO_BASE_URL for your network
docker compose build
docker compose up -d
python3 scripts/seed_prototypes.py --base-url http://localhost:8080/api   # register the target voicebank
```

## Docker Commands

### 1. Stop and remove all containers, networks defined in docker-compose.yml

```bash
sudo docker compose down
```

### 2. Remove dangling images, stopped containers, unused networks, and build cache

```bash
sudo docker system prune -f
```

### 3. Rebuild all images from scratch (no cached layers)

```bash
sudo docker compose build --no-cache
```

### 4. Start all services in detached mode

```bash
sudo docker compose up -d
```

### 5. Confirm container status

```bash
sudo docker compose ps
```

### 6. Tail logs for the VoiceMatchr service specifically

```bash
sudo docker compose logs -f voicematchr-service
```

## Smoke test

`scripts/smoke_test.py` exercises the deployed application end to end: service
health, the registered voicebank, a Kokoro-backed preview synthesis, learner
onboarding, session creation, a full `/recordings/analyze` round trip on a
generated WAV, and the longitudinal history. It is standard-library only.

```bash
# Against the live deployment (default base URL):
python3 scripts/smoke_test.py

# Against a local stack, read-only checks, writing nothing to the database:
python3 scripts/smoke_test.py --base-url http://localhost:8080/api --skip-analyze
```

The write-path checks onboard a throwaway user whose demographics are marked
`smoke-test`, so smoke rows are identifiable in evaluation exports.

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
