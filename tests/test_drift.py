"""Drift guards.

Tier A guards gpdk against gdsfactory's component set and survives the later stage where
core drops its own generic PDK. Tier B compares gpdk's copied technology against
``gdsfactory.gpdk`` and is deliberately temporary: when core removes that module these
tests skip themselves. The migration at that point is to DELETE tier B, not to fix it.
"""

import filecmp
import pathlib

import pytest

import gpdk

gf_gpdk = pytest.importorskip("gdsfactory.gpdk", reason="tier B: core dropped its gpdk")

GF_ROOT = pathlib.Path(gf_gpdk.__file__).parent
GF_KLAYOUT = GF_ROOT.parent / "generic_tech" / "klayout"


def test_layer_map_matches_core():
    """Tier B: every layer name and (layer, datatype) pair matches core."""
    ours = {layer.name: (layer.layer, layer.datatype) for layer in gpdk.tech.LAYER}
    theirs = {layer.name: (layer.layer, layer.datatype) for layer in gf_gpdk.LAYER}
    assert ours == theirs


def test_layer_stack_matches_core():
    """Tier B: layer stack level names and thicknesses match core."""
    ours = {
        name: (level.thickness, level.zmin)
        for name, level in gpdk.tech.LAYER_STACK.layers.items()
    }
    theirs = {
        name: (level.thickness, level.zmin)
        for name, level in gf_gpdk.LAYER_STACK.layers.items()
    }
    assert ours == theirs


def test_layer_views_yaml_is_byte_identical_to_core():
    """Tier B: layers.yaml is an unmodified copy of core's layer_views.yaml."""
    assert filecmp.cmp(gpdk.PATH.lyp_yaml, GF_ROOT / "layer_views.yaml", shallow=False)


def test_layers_lyp_is_byte_identical_to_core():
    """Tier B: layers.lyp is an unmodified copy of core's."""
    assert filecmp.cmp(gpdk.PATH.lyp, GF_KLAYOUT / "layers.lyp", shallow=False)
