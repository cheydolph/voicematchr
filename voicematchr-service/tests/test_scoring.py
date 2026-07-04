import pytest
from app.scoring.distance import (
    compute_signed_deltas,
    cosine_distance,
    cosine_similarity,
    rank_dimensions,
    select_coaching_target,
)


def test_identical_vectors_similarity_is_one():
    v = [1.0, 2.0, 3.0]
    assert cosine_similarity(v, v) == pytest.approx(1.0)


def test_orthogonal_vectors_similarity_is_zero():
    assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)


def test_cosine_distance_is_one_minus_similarity():
    assert cosine_distance([1.0, 0.0], [0.0, 1.0]) == pytest.approx(1.0)


def test_zero_vector_raises_value_error():
    with pytest.raises(ValueError):
        cosine_similarity([0.0, 0.0], [1.0, 1.0])


def test_signed_deltas_sign_correctness():
    learner = {
        "f0_mean": 40.0,
        "f0_range": 0.2,
        "hnr": 10.0,
        "spectral_tilt": -12.0,
        "loudness": 0.5,
    }
    prototype = {
        "f0_mean": 35.0,
        "f0_range": 0.25,
        "hnr": 12.0,
        "spectral_tilt": -10.0,
        "loudness": 0.4,
    }
    deltas = compute_signed_deltas(learner, prototype)
    assert deltas["f0_mean"] == pytest.approx(5.0)
    assert deltas["f0_range"] == pytest.approx(-0.05)
    assert deltas["loudness"] == pytest.approx(0.1)


def test_rank_dimensions_orders_by_absolute_magnitude():
    deltas = {
        "f0_mean": 1.0,
        "f0_range": -5.0,
        "hnr": 2.0,
        "spectral_tilt": 0.1,
        "loudness": -0.5,
    }
    ranked = rank_dimensions(deltas)
    assert ranked[0][0] == "f0_range"
    assert ranked[-1][0] == "spectral_tilt"


def test_select_coaching_target_direction_above():
    deltas = {
        "f0_mean": 4.2,
        "f0_range": -0.08,
        "hnr": 1.1,
        "spectral_tilt": -0.03,
        "loudness": 0.12,
    }
    dim, abs_delta, direction = select_coaching_target(deltas)
    assert dim == "f0_mean"
    assert abs_delta == pytest.approx(4.2)
    assert direction == "above"


def test_select_coaching_target_direction_below():
    deltas = {
        "f0_mean": -3.0,
        "f0_range": 0.01,
        "hnr": -0.2,
        "spectral_tilt": 0.05,
        "loudness": -0.02,
    }
    dim, _, direction = select_coaching_target(deltas)
    assert dim == "f0_mean"
    assert direction == "below"
