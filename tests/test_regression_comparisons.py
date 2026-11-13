"""Checks that portable netlist comparisons retain numeric and connectivity checks."""

import pytest
from conftest import assert_yaml_equal


def test_yaml_comparison_accepts_integral_rotation_spelling(tmp_path):
    """An integral rotation has the same value as its floating-point spelling."""
    reference = tmp_path / "reference.yml"
    obtained = tmp_path / "obtained.yml"
    reference.write_text("placements:\n  crossing:\n    rotation: 45\n")
    obtained.write_text("placements:\n  crossing:\n    rotation: 45.0\n")
    assert_yaml_equal(obtained, reference)


def test_yaml_comparison_preserves_boolean_types(tmp_path):
    """Boolean settings must not compare equal to numeric settings."""
    reference = tmp_path / "reference.yml"
    obtained = tmp_path / "obtained.yml"
    reference.write_text("settings:\n  mirror: true\n")
    obtained.write_text("settings:\n  mirror: 1\n")
    with pytest.raises(AssertionError):
        assert_yaml_equal(obtained, reference)


@pytest.mark.parametrize(
    "changed",
    [
        "placements:\n  crossing:\n    rotation: 45.001\n",
        "placements:\n  crossing:\n    rotation: 90\n",
        "placements:\n  another_cell:\n    rotation: 45\n",
        'placements:\n  crossing:\n    rotation: "45"\n',
    ],
)
def test_yaml_comparison_rejects_value_or_connectivity_changes(tmp_path, changed):
    """No angular tolerance or dropped instance keys are allowed."""
    reference = tmp_path / "reference.yml"
    obtained = tmp_path / "obtained.yml"
    reference.write_text("placements:\n  crossing:\n    rotation: 45\n")
    obtained.write_text(changed)
    with pytest.raises(AssertionError):
        assert_yaml_equal(obtained, reference)
