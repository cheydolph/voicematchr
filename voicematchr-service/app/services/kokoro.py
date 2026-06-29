from __future__ import annotations

import os
from typing import Any

import httpx

# Cloudflare tunnel forwarding to ghcr.io/remsky/kokoro-fastapi-gpu:latest on port 8881.
# Image is configured with DOWNLOAD_MODEL=true; models persist at
# /mnt/.../models on the host. If that volume is empty on first start,
# the image downloads the model before serving any synthesis request.
# SYNTHESIS_TIMEOUT covers that scenario; normal (warm) synthesis completes in ~5s.
KOKORO_BASE_URL: str = os.environ.get("KOKORO_BASE_URL", "http://localhost:8880")
SYNTHESIS_TIMEOUT: float = 600.0  # 10 minutes; covers cold model-download + synthesis

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
    Request WAV synthesis from the Kokoro FastAPI service and return raw bytes.

    Uses the OpenAI-compatible /v1/audio/speech endpoint exposed by
    ghcr.io/remsky/kokoro-fastapi-gpu:latest.

    Args:
        voice: A voice ID returned by list_voices() (e.g. 'af_bella', 'am_adam').
               Voice-mixing syntax ('voice1+voice2') is supported by this image
               for blended acoustic profiles.
        speed: Speaking-rate multiplier. Supported range: 0.5–2.0.
        text:  Text to synthesize. Defaults to PROBE_PASSAGE.

    Raises:
        httpx.HTTPStatusError: Kokoro returned a non-2xx response.
        httpx.ConnectError:    The Kokoro service is unreachable.
        httpx.TimeoutException: Synthesis exceeded SYNTHESIS_TIMEOUT, which most
                                likely means the model is downloading on first run.
                                Wait for the Kokoro container to finish initializing
                                (watch its logs) then retry.
    """
    payload = {
        "model": "kokoro",
        "voice": voice,
        "input": text,
        "speed": speed,
        "response_format": "wav",
    }
    async with httpx.AsyncClient(timeout=SYNTHESIS_TIMEOUT) as client:
        response = await client.post(
            f"{KOKORO_BASE_URL}/v1/audio/speech",
            json=payload,
        )
        response.raise_for_status()
        return response.content


async def list_voices() -> list[dict[str, Any]]:
    """
    Return the voice list from the Kokoro service.

    Used by the Week 7 prototype selection screen to populate the onboarding
    dropdown. The response schema from ghcr.io/remsky/kokoro-fastapi-gpu:latest
    is a list of objects; the 'id' field on each entry is the voice name to pass
    to synthesize_wav().
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(f"{KOKORO_BASE_URL}/v1/voices")
        response.raise_for_status()
        return response.json()
