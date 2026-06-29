import wave
from pathlib import Path

import numpy as np
import pytest


@pytest.fixture(scope="session")
def tmp_wav(tmp_path_factory) -> Path:
    """
    4-second, 16 kHz, mono WAV containing a 200 Hz multi-harmonic signal
    (sawtooth approximation) plus low-level broadband noise.

    Properties:
    - webrtcvad detects voiced frames from the 400+ Hz harmonics.
    - openSMILE eGeMAPSv02 extracts a stable F0 near 200 Hz.
    - The file is deterministic (fixed RNG seed) and session-scoped so it is
      written once and shared across all test modules.
    """
    tmp = tmp_path_factory.mktemp("audio")
    path = tmp / "probe.wav"

    sample_rate = 16_000
    duration = 4.0
    n_samples = int(sample_rate * duration)
    rng = np.random.default_rng(42)

    t = np.linspace(0, duration, n_samples, endpoint=False)
    f0 = 200.0
    nyquist = sample_rate / 2.0
    n_harmonics = int(nyquist / f0)

    signal = sum(np.sin(2 * np.pi * f0 * k * t) / k for k in range(1, n_harmonics + 1))
    signal += rng.normal(0, 0.05, n_samples)
    signal /= np.abs(signal).max()
    pcm = (signal * 0.75 * 32767).astype(np.int16)

    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm.tobytes())

    return path
