import pytest
from app.coaching.taxonomy import DIMENSIONS
from app.coaching.templates import TEMPLATES, select_template


def test_all_dimensions_have_templates():
    for dim in DIMENSIONS:
        assert dim in TEMPLATES, f"No template entry for dimension: {dim}"


def test_each_dimension_has_both_directions():
    for dim in DIMENSIONS:
        assert "above" in TEMPLATES[dim], f"Missing 'above' template for {dim}"
        assert "below" in TEMPLATES[dim], f"Missing 'below' template for {dim}"


def test_all_templates_render_without_error():
    for dim in DIMENSIONS:
        for direction in ("above", "below"):
            rendered = select_template(dim, direction, delta=1.23)
            assert isinstance(rendered, str)
            assert len(rendered) > 30, f"Template suspiciously short: {dim}/{direction}"


def test_delta_value_appears_in_rendered_output():
    rendered = select_template("f0_mean", "above", delta=3.7)
    assert "3.7" in rendered


def test_invalid_dimension_raises_key_error():
    with pytest.raises(KeyError):
        select_template("nonexistent_dim", "above", delta=1.0)
