"""Every shipped sample schematic builds through gdsfactory's YAML reader.

The ``*.pic.yml`` files under ``gpdk/samples/`` are the demo circuits that
accompany the PDK (LVS, routing, transceivers, packing). They are not PDK cells,
so ``make test`` only covers them through this module; it builds each one and
requires non-empty geometry so an empty schematic cannot pass.
"""

from __future__ import annotations

import pathlib

import gdsfactory as gf
import pytest
import yaml

import gpdk

SAMPLES = pathlib.Path(__file__).resolve().parent.parent / "gpdk" / "samples"
SCHEMATICS = sorted(SAMPLES.rglob("*.pic.yml"))


def _declares_instances(path: pathlib.Path) -> bool:
    """True if the schematic places at least one instance."""
    return bool((yaml.safe_load(path.read_text()) or {}).get("instances"))


@pytest.fixture(autouse=True)
def activate_pdk() -> None:
    """Activate the gpdk PDK (schematic routes need its cross-sections)."""
    gpdk.PDK.activate()


def test_sample_schematics_are_discovered() -> None:
    """The discovery finds the shipped schematics (guards an empty glob)."""
    assert SCHEMATICS, f"no *.pic.yml found under {SAMPLES}"


@pytest.mark.parametrize("path", SCHEMATICS, ids=lambda p: p.name)
def test_sample_schematic_builds(path: pathlib.Path) -> None:
    """A shipped schematic builds; one that places instances yields geometry.

    A blank canvas (no instances) legitimately builds to an empty component, so
    the geometry assertion only applies to schematics that place something.
    """
    component = gf.read.from_yaml(str(path))
    if _declares_instances(path):
        assert component.insts or component.get_polygons(), (
            f"{path.name} built no nested references or polygons"
        )
