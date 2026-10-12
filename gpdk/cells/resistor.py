"""Resistor PCells ported from gf180mcu (Magic VLSI geometry).

Layouts are centered at the origin with length along y and width along x.
"""

from __future__ import annotations

from math import floor
from typing import Literal

import gdsfactory as gf

from gpdk.layer_map import LAYER

__all__ = ["res_metal", "res_poly"]

# gf180mcu sm141064.ngspice res_typical sheet resistances (ohm/sq).
SHEET_RESISTANCE = {
    "ppolyf_u": 350.0,
    "npolyf_u": 310.0,
    "ppolyf_s": 7.3,
    "npolyf_s": 6.8,
    "M1": 0.09,
    "M2": 0.09,
    "M3": 0.09,
}

# Magic gf180mcu ruleset constants.
_CONTACT_SIZE = 0.23  # internal contact box
_CONTACT_GDS = 0.22  # contact as written to GDS
_POLY_SURROUND = 0.065
_DIFF_SURROUND = 0.065
_METAL_SURROUND = 0.055
_SUB_SURROUND = 0.12
_METAL_SPACING = 0.23
_CONTACT_PITCH = 0.47
_DIFFT = _CONTACT_SIZE + 2 * _DIFF_SURROUND  # guard ring bar width
_NSD_OUTER_BLOAT = 0.16
_NSD_INNER_BLOAT = 0.11

_METAL_RES = {
    "M1": (LAYER.M1, LAYER.M1_RES),
    "M2": (LAYER.M2, LAYER.M2_RES),
    "M3": (LAYER.M3, LAYER.M3_RES),
}


def _rect(c: gf.Component, x0: float, y0: float, x1: float, y1: float, layer) -> None:
    c.add_polygon([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], layer=layer)


def _sym(c: gf.Component, hx: float, hy: float, layer) -> None:
    """Rectangle centered on the origin with half-sizes hx, hy."""
    _rect(c, -hx, -hy, hx, hy, layer)


def _contacts(c: gf.Component, cx: float, cy: float, fill_w: float, fill_h: float):
    """2D contact array centered at (cx, cy) filling fill_w x fill_h."""

    def centers(size: float) -> list[float]:
        n = max(
            floor((max(size, _CONTACT_SIZE) - _CONTACT_SIZE) / _CONTACT_PITCH) + 1, 1
        )
        return [(i - (n - 1) / 2) * _CONTACT_PITCH for i in range(n)]

    h = _CONTACT_GDS / 2
    for dx in centers(fill_w):
        for dy in centers(fill_h):
            _rect(c, cx + dx - h, cy + dy - h, cx + dx + h, cy + dy + h, LAYER.VIAC)


def _guard_ring(
    c: gf.Component,
    gw: float,
    gh: float,
    implant_layer,
    well_layer,
    is_psd: bool,
) -> None:
    """Magic gf180mcu::guard_ring: ACTIVE + implant + M1 ring with side contacts."""
    hw, hh, hd = gw / 2, gh / 2, _DIFFT / 2

    # ACTIVE ring (top, bottom, left, right bars).
    _rect(c, -(hw + hd), hh - hd, hw + hd, hh + hd, LAYER.ACTIVE)
    _rect(c, -(hw + hd), -(hh + hd), hw + hd, -(hh - hd), LAYER.ACTIVE)
    _rect(c, -(hw + hd), -(hh + hd), -(hw - hd), hh + hd, LAYER.ACTIVE)
    _rect(c, hw - hd, -(hh + hd), hw + hd, hh + hd, LAYER.ACTIVE)

    if not is_psd:
        ox, oy = hw + hd + _NSD_OUTER_BLOAT, hh + hd + _NSD_OUTER_BLOAT
        ix, iy = hw - hd - _NSD_INNER_BLOAT, hh - hd - _NSD_INNER_BLOAT
        _rect(c, -ox, iy, ox, oy, implant_layer)
        _rect(c, -ox, -oy, ox, -iy, implant_layer)
        _rect(c, -ox, -iy, -ix, iy, implant_layer)
        _rect(c, ix, -iy, ox, iy, implant_layer)
    else:
        # psd implant shape from Magic CIF extraction.
        co_x, co_y, ci_x, ci_y = hw + hd, hh + hd, hw - hd, hh - hd
        b_out, b_side, gap = 0.02, 0.03, 0.125
        sx = ci_x - b_side
        _rect(c, -(co_x + b_out), ci_y - b_out, co_x + b_out, co_y + b_out, implant_layer)  # fmt: skip
        _rect(c, -(co_x + b_out), -(co_y + b_out), co_x + b_out, -(ci_y - b_out), implant_layer)  # fmt: skip
        _rect(c, -(co_x + b_side), -(ci_y - gap), -sx, ci_y - gap, implant_layer)
        _rect(c, sx, -(ci_y - gap), co_x + b_side, ci_y - gap, implant_layer)
        for s in (-1, 1):
            _rect(c, -(co_x + b_out), s * (ci_y - gap), -sx, s * (ci_y - b_out), implant_layer)  # fmt: skip
            _rect(c, sx, s * (ci_y - gap), co_x + b_out, s * (ci_y - b_out), implant_layer)  # fmt: skip

    # M1 ring.
    hc = _CONTACT_SIZE / 2
    _rect(c, -(hw + hc), -(hh - hc), -(hw - hc), hh - hc, LAYER.M1)
    _rect(c, hw - hc, -(hh - hc), hw + hc, hh - hc, LAYER.M1)
    _rect(c, -(hw + hc), hh - hc, hw + hc, hh + hc, LAYER.M1)
    _rect(c, -(hw + hc), -(hh + hc), hw + hc, -(hh - hc), LAYER.M1)

    # Contacts on the left and right bars.
    ch = max(gh - _CONTACT_SIZE - 2 * (_METAL_SURROUND + _METAL_SPACING), _CONTACT_SIZE)
    _contacts(c, -hw, 0, 0, ch)
    _contacts(c, hw, 0, 0, ch)

    if well_layer is not None:
        e = _CONTACT_SIZE / 2 + _DIFF_SURROUND + _SUB_SURROUND
        _sym(c, hw + e, hh + e, well_layer)


def _end_contact(c: gf.Component, cy: float, fill_w: float) -> None:
    """Magic draw_contact for a poly resistor end cap centered at (0, cy)."""
    hw = max(fill_w, _CONTACT_SIZE) / 2
    hh = _CONTACT_SIZE / 2
    _contacts(c, 0, cy, 2 * hw, 2 * hh)
    es, ms = _POLY_SURROUND, _METAL_SURROUND
    _rect(c, -hw - es, cy - hh - es, hw + es, cy + hh + es, LAYER.POLY)
    _rect(c, -hw - ms, cy - hh, hw + ms, cy + hh, LAYER.M1)


def _add_ports(c: gf.Component, y: float, width: float, layer) -> None:
    for name, sign, orientation in (("r0", 1, 90), ("r1", -1, 270)):
        c.add_port(
            name=name,
            center=(0, sign * y),
            width=width,
            orientation=orientation,
            layer=layer,
            port_type="electrical",
        )


@gf.cell(tags=["electrical", "resistor"])
def res_poly(
    l_res: float = 1.0,
    w_res: float = 0.8,
    res_type: Literal["ppolyf_u", "npolyf_u", "ppolyf_s", "npolyf_s"] = "ppolyf_u",
    label: bool = False,
    r0_label: str = "",
    r1_label: str = "",
) -> gf.Component:
    """Returns a poly resistor with end contacts and a guard ring.

    Port of gf180mcu ``res`` (``_poly_res``). ``*_u`` types are unsilicided
    (SAB over the body), ``*_s`` types are silicided.

    Args:
        l_res: resistor body length (y) in um.
        w_res: resistor body width (x) in um.
        res_type: poly resistor flavour (p/n implant, unsilicided/silicided).
        label: if True, add r0_label/r1_label text on the TEXT layer.
        r0_label: label text for terminal r0.
        r1_label: label text for terminal r1.
    """
    if res_type not in ("ppolyf_u", "npolyf_u", "ppolyf_s", "npolyf_s"):
        raise ValueError(f"Unknown res_type: {res_type!r}")
    c = gf.Component()
    hw, hl = w_res / 2, l_res / 2
    silicided = res_type.endswith("_s")

    if silicided:
        res_to_endcont = _POLY_SURROUND + _CONTACT_SIZE / 2
        end_spacing = 0.28
        res_diff_spacing = 0.28 if res_type == "npolyf_s" else 0.41
    else:
        res_to_endcont = 0.33
        end_spacing = 0.60
        res_diff_spacing = 0.60

    body_impl = LAYER.PPP if res_type.startswith("p") else LAYER.NPP
    # npolyf_u: p+ guard ring in lvpwell (no gpdk equivalent, well dropped).
    if res_type == "npolyf_u":
        gr_impl, well, is_psd = LAYER.PPP, None, True
    else:
        gr_impl, well, is_psd = LAYER.NPP, LAYER.NWELL, False

    hesz = _CONTACT_SIZE / 2 + _POLY_SURROUND
    poly_hy = hl + res_to_endcont + hesz

    _sym(c, hw, hl, LAYER.RES_MK)
    _sym(c, hw, poly_hy, LAYER.POLY)
    if not silicided:
        _sym(c, hw + 0.28, hl, LAYER.SAB)
    impl_ext = hesz if silicided else 0.30
    _sym(c, hw + impl_ext, poly_hy + impl_ext, body_impl)

    end_cy = hl + res_to_endcont
    cpl = w_res - 2 * _POLY_SURROUND
    _end_contact(c, end_cy, cpl)
    _end_contact(c, -end_cy, cpl)

    gx = w_res + 2 * (res_diff_spacing + _DIFF_SURROUND) + _CONTACT_SIZE
    gy = 2 * poly_hy + 2 * (end_spacing + _DIFF_SURROUND) + _CONTACT_SIZE
    _guard_ring(c, gx, gy, gr_impl, well, is_psd)

    _add_ports(c, hl, w_res, LAYER.M1)
    if label:
        c.add_label(r0_label, position=(0, end_cy), layer=LAYER.TEXT)
        c.add_label(r1_label, position=(0, -end_cy), layer=LAYER.TEXT)

    c.info["model"] = res_type
    c.info["resistance_ohm"] = SHEET_RESISTANCE[res_type] * l_res / w_res
    c.info["l_res"] = l_res
    c.info["w_res"] = w_res
    return c


@gf.cell(tags=["electrical", "resistor"])
def res_metal(
    l_res: float = 0.2,
    w_res: float = 0.2,
    metal: Literal["M1", "M2", "M3"] = "M1",
) -> gf.Component:
    """Returns a metal resistor: a metal strip with a resistor marker on its body.

    Port of gf180mcu ``res`` (``_metal_res``, rm1/rm2/rm3).

    Args:
        l_res: resistor body length (y) in um, i.e. marker length.
        w_res: resistor width (x) in um.
        metal: metal layer of the resistor.
    """
    if metal not in _METAL_RES:
        raise ValueError(f"metal must be one of {list(_METAL_RES)}")
    m_layer, res_layer = _METAL_RES[metal]
    c = gf.Component()
    hw, hl = w_res / 2, l_res / 2
    ext = 0.315  # res_to_endcont + contact_size / 2
    _sym(c, hw, hl, res_layer)
    _sym(c, hw, hl + ext, m_layer)
    _add_ports(c, hl + ext, w_res, m_layer)

    c.info["model"] = f"r{metal.lower()}"
    c.info["resistance_ohm"] = SHEET_RESISTANCE[metal] * l_res / w_res
    c.info["l_res"] = l_res
    c.info["w_res"] = w_res
    return c
