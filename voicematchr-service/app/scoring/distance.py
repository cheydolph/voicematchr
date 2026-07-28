"""
Pure, stateless scoring functions for VoiceMatchr.

No I/O dependencies. Must not import aiosqlite, httpx, or resemblyzer.
All inputs are plain Python lists/dicts; all outputs are JSON-safe.
"""

from __future__ import annotations

import numpy as np

from app.services.extractor import DIMENSIONS


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Return cosine similarity in [0, 1] between vectors a and b."""
    va = np.array(a, dtype=float)
    vb = np.array(b, dtype=float)
    denom = np.linalg.norm(va) * np.linalg.norm(vb)
    if np.isclose(denom, 0.0, rtol=1e-09, atol=1e-09):
        raise ValueError("Cannot compute cosine similarity for a zero vector.")
    return float(np.dot(va, vb) / denom)


def cosine_distance(a: list[float], b: list[float]) -> float:
    """Return 1 - cosine_similarity(a, b)."""
    return 1.0 - cosine_similarity(a, b)


def compute_signed_deltas(
    learner: dict[str, float],
    prototype: dict[str, float],
) -> dict[str, float]:
    """
    Return signed per-dimension deltas: learner_value - prototype_value.
    Positive means the learner is above the prototype on that dimension.
    """
    return {dim: learner[dim] - prototype[dim] for dim in DIMENSIONS}


def rank_dimensions(deltas: dict[str, float]) -> list[tuple[str, float]]:
    """Return (dimension, signed_delta) tuples sorted by absolute magnitude, descending."""
    return sorted(deltas.items(), key=lambda kv: abs(kv[1]), reverse=True)


def select_coaching_target(deltas: dict[str, float]) -> tuple[str, float, str]:
    """Return (dimension, abs_delta, direction) for the highest-priority dimension."""
    dimension, signed_delta = rank_dimensions(deltas)[0]
    direction = "above" if signed_delta > 0 else "below"
    return dimension, abs(signed_delta), direction
