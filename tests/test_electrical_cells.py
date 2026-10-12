"""Unit tests for the hand-written electrical and electro-optic cells."""

from __future__ import annotations

import pytest

from gpdk import PDK
from gpdk.cells.capacitor import cmim, cmom
from gpdk.cells.modulator import straight_pn_ribbed
from gpdk.cells.mos import nch, pch
from gpdk.cells.resistor import res_metal, res_poly
from gpdk.layer_map import LAYER


@pytest.fixture(autouse=True)
def _activate_pdk() -> None:
    """Other test modules may activate gdsfactory's own generic PDK."""
    PDK.activate()


_BY_GDS = {(layer.layer, layer.datatype): layer for layer in LAYER}


def _layers(c) -> set[LAYER]:
    return {_BY_GDS[layer] for layer in c.layers}


def _ports(c, prefix: str = "") -> list[str]:
    return [p.name for p in c.ports if p.name.startswith(prefix)]


@pytest.mark.parametrize("cell", [nch, pch])
def test_mos_ports_and_layers(cell) -> None:
    """MOS cells expose electrical S/D/G ports on the CMOS front-end layers."""
    c = cell()
    assert {"Drain_0", "Source_0", "Gate_0"} <= set(_ports(c))
    assert all(p.port_type == "electrical" for p in c.ports)
    assert {LAYER.ACTIVE, LAYER.POLY, LAYER.VIAC, LAYER.M1} <= _layers(c)
    assert c.info["model"] == cell.__name__


def test_mos_implants() -> None:
    """Nch uses n+ S/D; pch uses p+ S/D inside an n-well."""
    assert LAYER.NPP in _layers(nch(grw=0))
    assert LAYER.PPP not in _layers(nch(grw=0))
    assert {LAYER.PPP, LAYER.NWELL} <= _layers(pch())


def test_mos_fingers_add_terminals() -> None:
    """More gate fingers add drain terminals."""
    assert len(_ports(nch(nf=4), "Drain")) > len(_ports(nch(nf=1), "Drain"))


def test_mos_guard_ring_toggles_bulk_ports() -> None:
    """Bulk ports only exist when the guard ring is drawn."""
    assert _ports(nch(grw=0.22), "Bulk")
    assert not _ports(nch(grw=0), "Bulk")


def test_cmim() -> None:
    """Cmim draws the MIM stack and its capacitance scales with area."""
    c = cmim()
    assert set(_ports(c)) == {"top", "bottom"}
    assert {LAYER.M2, LAYER.MIM, LAYER.VIA2, LAYER.M3, LAYER.CAP_MK} <= _layers(c)
    assert cmim(lc=10, wc=10).info["capacitance_fF"] == pytest.approx(
        4 * c.info["capacitance_fF"]
    )


def test_cmom() -> None:
    """Cmom spans botmetal..topmetal and capacitance grows with fingers."""
    c = cmom()
    assert set(_ports(c)) == {"PLUS", "MINUS"}
    assert {LAYER.M1, LAYER.VIA1, LAYER.M2, LAYER.VIA2, LAYER.M3} <= _layers(c)
    assert cmom(nfingers=5).info["capacitance_fF"] > c.info["capacitance_fF"]
    assert LAYER.M3 not in _layers(cmom(topmetal="M2"))


def test_cmom_rejects_inverted_metals() -> None:
    """Botmetal above topmetal is rejected."""
    with pytest.raises(ValueError):
        cmom(botmetal="M3", topmetal="M1")


@pytest.mark.parametrize("res_type", ["ppolyf_u", "npolyf_u", "ppolyf_s", "npolyf_s"])
def test_res_poly(res_type: str) -> None:
    """Implant follows the doping type; only unsilicided types draw SAB."""
    c = res_poly(res_type=res_type)
    assert set(_ports(c)) == {"r0", "r1"}
    assert {LAYER.POLY, LAYER.RES_MK, LAYER.VIAC, LAYER.M1} <= _layers(c)
    implant = LAYER.PPP if res_type.startswith("p") else LAYER.NPP
    assert implant in _layers(c)
    assert (LAYER.SAB in _layers(c)) == res_type.endswith("_u")


def test_res_poly_scales_with_squares() -> None:
    """Resistance scales with the number of squares l/w."""
    r = res_poly(l_res=1.0, w_res=1.0).info["resistance_ohm"]
    assert res_poly(l_res=4.0, w_res=1.0).info["resistance_ohm"] == pytest.approx(4 * r)
    assert res_poly(l_res=1.0, w_res=2.0).info["resistance_ohm"] == pytest.approx(r / 2)


@pytest.mark.parametrize(
    "metal, marker",
    [("M1", LAYER.M1_RES), ("M2", LAYER.M2_RES), ("M3", LAYER.M3_RES)],
)
def test_res_metal(metal: str, marker: LAYER) -> None:
    """Metal resistor draws its metal plus the matching resistor marker."""
    c = res_metal(metal=metal)
    assert set(_ports(c)) == {"r0", "r1"}
    assert {LAYER[metal], marker} <= _layers(c)


def test_straight_pn_ribbed_snaps_length() -> None:
    """Length snaps down to a whole number of rib periods."""
    c = straight_pn_ribbed(length=55)
    assert c.info["length"] == 50
    assert c.info["n_periods"] == 5
    assert c.ports["o2"].center[0] - c.ports["o1"].center[0] == pytest.approx(50)


def test_straight_pn_ribbed_ports_and_doping() -> None:
    """Optical + anode/cathode ports, and all six doping layers drawn."""
    c = straight_pn_ribbed(length=50)
    assert {p.name: p.port_type for p in c.ports} == {
        "o1": "optical",
        "o2": "optical",
        "anode": "electrical",
        "cathode": "electrical",
    }
    assert c.ports["anode"].center[1] < 0 < c.ports["cathode"].center[1]
    doping = {LAYER.P, LAYER.N, LAYER.PP, LAYER.NP, LAYER.PPP, LAYER.NPP}
    assert doping | {LAYER.WG, LAYER.SHALLOW_ETCH, LAYER.VIAC, LAYER.M1} <= _layers(c)


def test_new_cells_registered() -> None:
    """Every hand-written cell is registered in the PDK."""
    new = {"nch", "pch", "cmim", "cmom", "res_poly", "res_metal", "straight_pn_ribbed"}
    assert new <= set(PDK.cells)
