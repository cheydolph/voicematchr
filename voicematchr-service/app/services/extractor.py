from __future__ import annotations

import threading
from pathlib import Path

import opensmile

# Single source of truth for dimension ordering. All downstream modules
# (taxonomy.py, templates.py, scoring/distance.py) import from here.
DIMENSIONS: list[str] = [
    "f0_mean",
    "f0_range",
    "hnr",
    "spectral_tilt",
    "loudness",
]

_COLUMN_MAP: dict[str, str] = {
    "f0_mean": "F0semitoneFrom27.5Hz_sma3nz_amean",
    "f0_range": "F0semitoneFrom27.5Hz_sma3nz_stddevNorm",
    "hnr": "HNRdBACF_sma3nz_amean",
    "spectral_tilt": "alphaRatioV_sma3nz_amean",
    "loudness": "loudness_sma3_amean",
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

    result = _get_smile().process_file(str(path))
    row = result.iloc[0]

    missing = [col for col in _COLUMN_MAP.values() if col not in row.index]
    if missing:
        raise RuntimeError(
            f"Expected eGeMAPSv02 columns absent from openSMILE output: {missing}. "
            f"Run 'smile.feature_names' to inspect available columns."
        )

    return {dim: float(row[col]) for dim, col in _COLUMN_MAP.items()}


def feature_vector(wav_path: str | Path) -> list[float]:
    """
    Return extracted features as an ordered list aligned with DIMENSIONS.
    Suitable for JSON serialization and vectorized delta computation.
    """
    feats = extract_features(wav_path)
    return [feats[d] for d in DIMENSIONS]
