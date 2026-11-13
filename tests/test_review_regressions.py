"""Regression checks for the sample-to-PDK integration boundary."""

import importlib.util
import pathlib
import subprocess
import sys

import gdsfactory as gf
import pytest

import gpdk
from gpdk import tech


def test_routing_preserves_existing_keys():
    """Extending demo routing must retain every existing strategy."""
    assert set(tech.routing_strategies) <= set(gpdk.PDK.routing_strategies)


def test_route_bundle_accepts_schematic_nets():
    """The registered router accepts positional schematic nets."""
    gpdk.PDK.activate()
    c = gf.Component()
    a = c << gpdk.cells.straight()
    b = c << gpdk.cells.straight()
    b.dmove((100, 60))
    routes = gpdk.PDK.routing_strategies["route_bundle"](
        c,
        [(a.ports["o2"], b.ports["o1"])],
    )
    assert len(routes) == 1
    assert routes[0].length > 0


def test_cross_section_exports_match_registration():
    """The public re-export and registered factories have identical entries."""
    from gpdk.cross_section import cross_sections

    assert cross_sections is tech.cross_sections
    assert cross_sections == gpdk.PDK.cross_sections


def _installer():
    path = pathlib.Path(__file__).parents[1] / "install_tech.py"
    spec = importlib.util.spec_from_file_location("install_tech", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("kind", ["directory", "file", "symlink", "broken_symlink"])
def test_technology_cleanup(tmp_path, kind):
    """Reinstallation handles copied trees and links without deleting targets."""
    target = tmp_path / "target"
    target.mkdir()
    dest = tmp_path / "dest"
    if kind == "directory":
        dest.mkdir()
        (dest / "old.lyt").write_text("old")
    elif kind == "file":
        dest.write_text("old")
    else:
        dest.symlink_to(target if kind == "symlink" else tmp_path / "missing")
    _installer().remove_path_or_dir(dest)
    assert not dest.exists() and not dest.is_symlink()
    assert target.is_dir()


def test_technology_installer_cli(tmp_path):
    """The script installs the bundled technology to an explicit destination."""
    installer = pathlib.Path(__file__).parents[1] / "install_tech.py"
    dest = tmp_path / "tech" / "gpdk"
    subprocess.run([sys.executable, str(installer), "--dest", str(dest)], check=True)
    assert (dest / "tech.lyt").is_file()


def test_playdough_adapter_owned_by_library():
    """The production strategy does not depend on the removable demo module."""
    from gpdk.routing_strategies import route_bundle_playdough

    assert route_bundle_playdough.__module__ == "gpdk.routing_strategies"
