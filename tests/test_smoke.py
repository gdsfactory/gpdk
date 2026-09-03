"""Smoke tests for the package skeleton."""

import gpdk


def test_version_is_string_literal():
    """The package exposes a version string."""
    assert isinstance(gpdk.__version__, str)
    assert gpdk.__version__ == "0.0.1"


def test_paths_point_inside_the_package():
    """PATH.module points at the installed gpdk package directory."""
    assert gpdk.PATH.module.name == "gpdk"
    assert gpdk.PATH.repo == gpdk.PATH.module.parent
