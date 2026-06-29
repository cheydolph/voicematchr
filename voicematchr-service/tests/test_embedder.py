import numpy as np
import pytest
from app.services.embedder import compute_embedding


def test_embedding_shape(tmp_wav):
    emb = compute_embedding(tmp_wav)
    assert len(emb) == 256, f"Expected 256 dims, got {len(emb)}"


def test_embedding_values_are_python_floats(tmp_wav):
    emb = compute_embedding(tmp_wav)
    assert all(isinstance(v, float) for v in emb)


def test_embedding_is_unit_normalized(tmp_wav):
    emb = compute_embedding(tmp_wav)
    norm = np.linalg.norm(emb)
    assert abs(norm - 1.0) < 1e-5, f"Embedding not unit-normalized: norm={norm:.6f}"


def test_missing_file_raises_file_not_found():
    with pytest.raises(FileNotFoundError):
        compute_embedding("/nonexistent/path/probe.wav")


def test_same_file_produces_same_embedding(tmp_wav):
    assert compute_embedding(tmp_wav) == compute_embedding(tmp_wav)
