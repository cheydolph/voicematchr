import pytest

from app.services.extractor import DIMENSIONS, extract_features, feature_vector


def test_returns_all_dimensions(tmp_wav):
    feats = extract_features(tmp_wav)
    assert set(feats.keys()) == set(DIMENSIONS), (
        f"Missing dimensions: {set(DIMENSIONS) - set(feats.keys())}"
    )


def test_all_values_are_float(tmp_wav):
    feats = extract_features(tmp_wav)
    for dim, val in feats.items():
        assert isinstance(val, float), (
            f"Dimension {dim} returned {type(val)}, expected float"
        )


def test_feature_vector_length(tmp_wav):
    vec = feature_vector(tmp_wav)
    assert len(vec) == len(DIMENSIONS)


def test_feature_vector_order(tmp_wav):
    feats = extract_features(tmp_wav)
    vec = feature_vector(tmp_wav)
    for i, dim in enumerate(DIMENSIONS):
        assert vec[i] == feats[dim], f"Ordering mismatch at index {i} ({dim})"


def test_missing_file_raises(tmp_wav):
    with pytest.raises(FileNotFoundError):
        extract_features("/nonexistent/audio.wav")


def test_f0_mean_reflects_voiced_signal(tmp_wav):
    # The 200 Hz fundamental gives F0 in semitones from 27.5 Hz of ~34.
    # Asserting > 20 confirms a valid F0 was detected, not just silence or noise.
    feats = extract_features(tmp_wav)
    assert feats["f0_mean"] > 20.0, (
        f"f0_mean={feats['f0_mean']:.2f} unexpectedly low; "
        "check that the test WAV contains voiced content."
    )
