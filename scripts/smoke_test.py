#!/usr/bin/env python3
"""
End-to-end smoke test for a deployed VoiceMatchr instance.

Exercises the public API surface a learner traverses, in dependency order:

1. GET  /health                        -- service liveness
2. GET  /prototypes/                   -- the registered voicebank ("available voices")
3. GET  /prototypes/{id}/preview       -- Kokoro synthesis path, end to end
4. POST /users/onboard                 -- token issuance
5. POST /sessions/                     -- session creation against a prototype
6. POST /recordings/analyze            -- full analysis pipeline on a generated WAV
7. GET  /sessions/                     -- longitudinal history reflects step 6

Steps 4-7 write rows to the live database. The onboarded user is marked with
demographics of "smoke-test" in both fields, so smoke rows are identifiable and
excludable when filtering evaluation exports. Pass --skip-analyze to run only
the read-only checks (steps 1-3).

Standard library only, matching seed_prototypes.py and export_results.py, so it
runs on any host with Python 3 and no pip installs.

Usage:
    python3 scripts/smoke_test.py [--base-url https://voicematchr.fiestaszn.com/api]
                                  [--skip-analyze] [--kokoro-url http://kokoro-proxy:8881]

Exit status is 0 only if every requested check passes.
"""

from __future__ import annotations

import argparse
import io
import json
import math
import random
import struct
import sys
import urllib.error
import urllib.request
import uuid
import wave
from typing import Any

DEFAULT_BASE_URL = "https://voicematchr.fiestaszn.com/api"

# The analyze pipeline runs Resemblyzer and openSMILE on the upload; a cold
# service can take tens of seconds. Matches the 600s ceilings in nginx.conf.
TIMEOUT_SECONDS = 600

# WAV parameters mirror voicematchr-service/tests/conftest.py: a 4-second,
# 16 kHz mono sawtooth at 200 Hz plus low-level noise. The 400+ Hz sawtooth
# harmonics are what webrtcvad and the F0 extractor need to see voiced frames.
WAV_SECONDS = 4
WAV_RATE = 16000
WAV_F0_HZ = 200.0


def http_json(
    url: str,
    payload: dict[str, Any] | None = None,
    token: str | None = None,
) -> Any:
    """GET (payload None) or POST JSON and return the decoded JSON response."""
    data = None if payload is None else json.dumps(payload).encode()
    headers = {"Content-Type": "application/json"}
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        return json.load(response)


def check_health(base_url: str) -> None:
    body = http_json(f"{base_url}/health")
    if body.get("status") != "ok":
        raise SystemExit(f"FAIL /health: unexpected body {body}")
    print("PASS /health")


def check_prototypes(base_url: str) -> list[dict[str, Any]]:
    rows = http_json(f"{base_url}/prototypes/")
    if not isinstance(rows, list) or not rows:
        raise SystemExit(
            "FAIL /prototypes/: empty voicebank. "
            "Run scripts/seed_prototypes.py before smoke testing."
        )
    print(f"PASS /prototypes/ ({len(rows)} registered voices):")
    for row in rows:
        print(f"  id={row['id']}  {row['voice_name']} @ speed {row['speed']}")
    return rows


def check_preview(base_url: str, prototype_id: int) -> None:
    url = f"{base_url}/prototypes/{prototype_id}/preview"
    with urllib.request.urlopen(url, timeout=TIMEOUT_SECONDS) as response:
        content_type = response.headers.get("Content-Type", "")
        body = response.read()
    if "audio/wav" not in content_type or len(body) < 100:
        raise SystemExit(
            f"FAIL preview: content-type={content_type!r}, {len(body)} bytes"
        )
    print(f"PASS /prototypes/{prototype_id}/preview ({len(body)} bytes of WAV)")


def onboard(base_url: str) -> str:
    body = http_json(
        f"{base_url}/users/onboard",
        payload={
            "accent_background": "smoke-test",
            "vocal_training_history": "smoke-test",
        },
    )
    token = body.get("token", "")
    if not token:
        raise SystemExit(f"FAIL /users/onboard: no token in {body}")
    print("PASS /users/onboard (token issued)")
    return token


def create_session(base_url: str, token: str, prototype_id: int) -> int:
    body = http_json(
        f"{base_url}/sessions/",
        payload={"prototype_id": prototype_id},
        token=token,
    )
    session_id = body.get("session_id")
    if not isinstance(session_id, int):
        raise SystemExit(f"FAIL /sessions/ create: {body}")
    print(f"PASS /sessions/ (session_id={session_id})")
    return session_id


def generate_wav_bytes() -> bytes:
    """
    Synthesize a voiced-like test signal entirely in the standard library.

    Same target as voicematchr-service/tests/conftest.py's tmp_wav fixture (a
    16 kHz mono signal with strong harmonic content near 200 Hz, so webrtcvad
    and the F0 extractor see voiced frames), reimplemented without numpy: this
    script is meant to run against a deployed instance from an arbitrary host,
    matching the no-pip-installs convention already used by seed_prototypes.py
    and export_results.py. A naive (non-band-limited) sawtooth via phase
    wrapping is sufficient for that purpose and does not need numpy.
    """
    rng = random.Random(6460)  # deterministic across runs
    frames = bytearray()
    for n in range(WAV_SECONDS * WAV_RATE):
        t = n / WAV_RATE
        phase = t * WAV_F0_HZ
        sawtooth = 2.0 * (phase - math.floor(phase + 0.5))
        sample = 0.6 * sawtooth + 0.02 * (rng.random() * 2.0 - 1.0)
        frames += struct.pack("<h", int(max(-1.0, min(1.0, sample)) * 32767))
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(WAV_RATE)
        wav.writeframes(bytes(frames))
    return buffer.getvalue()


def build_multipart(session_id: int, wav_bytes: bytes) -> tuple[str, bytes]:
    """Assemble a multipart/form-data body for POST /recordings/analyze."""
    boundary = uuid.uuid4().hex
    parts = [
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="session_id"\r\n\r\n'
        f"{session_id}\r\n".encode(),
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="file"; filename="smoke.wav"\r\n'
        "Content-Type: audio/wav\r\n\r\n".encode(),
        wav_bytes,
        f"\r\n--{boundary}--\r\n".encode(),
    ]
    return f"multipart/form-data; boundary={boundary}", b"".join(parts)


def check_analyze(base_url: str, token: str, session_id: int) -> None:
    content_type, body = build_multipart(session_id, generate_wav_bytes())
    request = urllib.request.Request(
        f"{base_url}/recordings/analyze",
        data=body,
        headers={
            "Content-Type": content_type,
            "Authorization": f"Bearer {token}",
        },
    )
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        result = json.load(response)
    for key in ("cosine_distance", "coaching_text", "delta_vector"):
        if key not in result:
            raise SystemExit(f"FAIL /recordings/analyze: missing {key!r} in {result}")
    print(
        "PASS /recordings/analyze "
        f"(cosine_distance={result['cosine_distance']:.4f}, "
        f"coaching dimension={result['coaching_dimension']})"
    )


def check_sessions(base_url: str, token: str, session_id: int) -> None:
    rows = http_json(f"{base_url}/sessions/", token=token)
    match = next((row for row in rows if row["session_id"] == session_id), None)
    if match is None or len(match["recordings"]) != 1:
        raise SystemExit(f"FAIL /sessions/ history: {rows}")
    print("PASS /sessions/ (history shows the analyzed recording)")


def check_kokoro_voices(kokoro_url: str) -> None:
    """
    LAN-only check: the allowlist proxy's raw voice inventory.

    ghcr.io/remsky/kokoro-fastapi-gpu returns a list of voice objects, each
    keyed by "id" (see voicematchr-service/app/services/kokoro.py, list_voices),
    not a dict wrapper or a flat list of strings.
    """
    voices = http_json(f"{kokoro_url}/v1/audio/voices")
    ids = [voice.get("id", "?") for voice in voices]
    print(f"PASS {kokoro_url}/v1/audio/voices ({len(ids)} synthesizable voices):")
    print(f"  {', '.join(ids)}")


def run_checks(args: argparse.Namespace) -> None:
    base_url = args.base_url.rstrip("/")
    check_health(base_url)
    prototypes = check_prototypes(base_url)
    check_preview(base_url, prototypes[0]["id"])
    if args.kokoro_url:
        check_kokoro_voices(args.kokoro_url.rstrip("/"))
    if args.skip_analyze:
        print("SKIP write-path checks (--skip-analyze)")
        return
    token = onboard(base_url)
    session_id = create_session(base_url, token, prototypes[0]["id"])
    check_analyze(base_url, token, session_id)
    check_sessions(base_url, token, session_id)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help="API base, no trailing slash (default: %(default)s; "
        "use http://localhost:8080/api against a local stack)",
    )
    parser.add_argument(
        "--skip-analyze",
        action="store_true",
        help="run only the read-only checks; write nothing to the database",
    )
    parser.add_argument(
        "--kokoro-url",
        default="",
        help="optional LAN-side Kokoro allowlist proxy base "
        "(e.g. http://kokoro-proxy:8881) to also list synthesizable voices",
    )
    args = parser.parse_args()
    try:
        run_checks(args)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")
        raise SystemExit(f"FAIL {exc.url}: HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(
            f"Cannot reach {args.base_url} ({exc.reason}). Is the stack up?"
        ) from exc
    print("All smoke checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
