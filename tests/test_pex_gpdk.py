"""Consistency checks for the gfpex default PEX rules of gpdk."""

from __future__ import annotations

import pytest

pytest.importorskip(
    "gfpex.gfpex"
)  # not bare "gfpex": a folder named gfpex on sys.path would satisfy it

from gfpex.gfpex import Techfile  # noqa: E402

from gpdk.layer_map import LAYER  # noqa: E402
from gpdk.pex.rules import DEFAULT_PEX_RULES_CONFIG as CFG  # noqa: E402


def _names() -> set[str]:
    """Drawn layer names plus the LVS computed names gpdk uses for stack layers and contacts."""
    return {layer.name for layer in CFG.layers} | {
        computed.layer_info.name for computed in CFG.lvs_computed_layers
    }


def _contacts():
    for stack_layer in CFG.process_stack.layers:
        layer = stack_layer.metal_layer or stack_layer.diffusion_layer
        if layer is not None and layer.contact_above is not None:
            yield layer.contact_above


def test_round_trip() -> None:
    """The config is a Techfile and survives a JSON round trip."""
    assert isinstance(CFG, Techfile)
    assert Techfile.model_validate_json(CFG.to_json()) == CFG


def test_names_resolve() -> None:
    """Every stack, contact and parasitic-table name is a drawn or LVS computed layer."""
    names = _names()
    used = [
        s.name
        for s in CFG.process_stack.layers
        if s.metal_layer is not None or s.diffusion_layer is not None
    ]
    for contact in _contacts():
        used += [contact.name, contact.layer_below, contact.metal_above]
    resistance = CFG.process_parasitics.resistance
    capacitance = CFG.process_parasitics.capacitance
    used += [r.layer_name for r in resistance.layers]
    used += [
        n
        for r in resistance.contacts
        for n in (r.contact_name, r.device_layer_name, r.layer_above)
    ]
    used += [r.via_name for r in resistance.vias]
    used += [c.layer_name for c in capacitance.substrates + capacitance.sidewalls]
    used += [
        n for c in capacitance.overlaps for n in (c.top_layer_name, c.bottom_layer_name)
    ]
    used += [
        n for c in capacitance.sideoverlaps for n in (c.in_layer_name, c.out_layer_name)
    ]
    assert set(used) - names == set()


def test_gds_pairs_match_layer() -> None:
    """Drawn GDS pairs equal gpdk LAYER."""
    for layer in CFG.layers:
        pair = layer.drw_gds_pair
        assert (pair.layer, pair.datatype) == tuple(getattr(LAYER, layer.name)), (
            layer.name
        )


def test_metal_z_increases() -> None:
    """Metal z increases with stack order."""
    metals = [
        s.metal_layer for s in CFG.process_stack.layers if s.metal_layer is not None
    ]
    z = [m.z for m in metals]
    assert len(z) > 1
    assert z == sorted(z)
    # M1 and HEATER share a level by design; any metals on different levels must not overlap.
    for below, above in zip(metals, metals[1:]):
        if above.z != below.z:
            assert below.z + below.thickness <= above.z


def test_z_lookup_has_contacts() -> None:
    """The z lookup covers every contact."""
    lookup = CFG.build_layer_z_lookup()
    names = {c.name for c in _contacts()}
    assert names
    assert names <= lookup.keys()
