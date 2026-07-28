#!/usr/bin/env python3
"""
Seed the prototype voicebank through the running API.

Idempotent: voices already registered are skipped (or rejected by the backend with
409, which is treated as success). Run once after `docker compose up -d` and before
any evaluation session, so every participant is scored against identical prototype
rows.

Standard library only, so it runs on any host with Python 3 and no pip installs.

Usage:
    python3 scripts/seed_prototypes.py [--base-url http://localhost/api]
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request

# One female/male pair at neutral speed, plus one variant each, giving the
# onboarding screen a genuine choice along both timbre and pacing. Names are
# Kokoro voice identifiers.
SEED_VOICES: list[dict[str, float | str]] = [
    {"voice_name": "af_bella", "speed": 1.0},
    {"voice_name": "af_nicole", "speed": 1.0},
    {"voice_name": "am_adam", "speed": 1.0},
    {"voice_name": "am_michael", "speed": 0.9},
]

# Prototype synthesis runs the full Kokoro + embedding + extraction pipeline and a
# cold Kokoro container downloads its model first, so the first request can take
# minutes. Matches SYNTHESIS_TIMEOUT in app/services/kokoro.py.
TIMEOUT_SECONDS = 600


def fetch_existing(base_url: str) -> set[tuple[str, float]]:
    with urllib.request.urlopen(f"{base_url}/prototypes/", timeout=30) as response:
        rows = json.load(response)
    return {(row["voice_name"], row["speed"]) for row in rows}


def register(base_url: str, voice: dict[str, float | str]) -> str:
    request = urllib.request.Request(
        f"{base_url}/prototypes/",
        data=json.dumps(voice).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            row = json.load(response)
        return f"registered (id={row['id']})"
    except urllib.error.HTTPError as exc:
        if exc.code == 409:
            return "already exists (409)"
        detail = exc.read().decode(errors="replace")
        raise SystemExit(
            f"Registration failed for {voice['voice_name']}: HTTP {exc.code}: {detail}"
        ) from exc


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-url",
        default="http://localhost/api",
        help="API base, no trailing slash (default: %(default)s; "
        "use http://localhost:3939 to bypass nginx)",
    )
    args = parser.parse_args()
    base_url = args.base_url.rstrip("/")

    # The most common operator error is running this before `docker compose up -d`
    # has finished, which otherwise surfaces as a urllib traceback. Fail with the
    # actual remedy instead.
    try:
        existing = fetch_existing(base_url)
    except urllib.error.URLError as exc:
        raise SystemExit(
            f"Cannot reach {base_url}/prototypes/ ({exc.reason}). "
            "Is the stack up? Run: docker compose up -d, then retry."
        ) from exc
    for voice in SEED_VOICES:
        key = (voice["voice_name"], voice["speed"])
        if key in existing:
            print(f"{voice['voice_name']} @ {voice['speed']}: already present, skipped")
            continue
        outcome = register(base_url, voice)
        print(f"{voice['voice_name']} @ {voice['speed']}: {outcome}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
