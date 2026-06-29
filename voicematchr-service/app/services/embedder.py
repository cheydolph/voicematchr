from __future__ import annotations

import threading
from pathlib import Path

import numpy as np
from resemblyzer import VoiceEncoder, preprocess_wav

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
    Return a 256-dimensional L2-normalized speaker embedding for the WAV at
    `wav_path` using the Resemblyzer GE2E encoder.

    The returned list contains Python floats (not numpy scalars) and is safe
    for JSON serialization.

    Raises FileNotFoundError if `wav_path` does not exist.
    Raises ValueError if the audio is shorter than ~1.6 seconds of voiced
    content after VAD trimming.
    """
    path = Path(wav_path)
    if not path.exists():
        raise FileNotFoundError(f"WAV not found: {path}")

    wav = preprocess_wav(path)

    if len(wav) < 16_000:
        raise ValueError(
            f"Insufficient voiced content after VAD trimming ({len(wav)} samples). "
            "Recording must contain at least 1.6 seconds of speech."
        )

    embedding: np.ndarray = _get_encoder().embed_utterance(wav)
    return embedding.tolist()
