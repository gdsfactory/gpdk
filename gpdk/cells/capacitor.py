"""Capacitor PCells: MIM (ported from gf180mcu) and MOM (ported from IHP)."""

from __future__ import annotations

from math import floor
from typing import Literal

import gdsfactory as gf

from gpdk.layer_map import LAYER

__all__ = ["cmim", "cmom"]

# gf180mcu mim_2p0fF model (MIM-A): 2 fF/um^2.
MIM_CAP_DENSITY = 2.0

# IHP SG13G2 rules used by the MOM capacitor (ihp.tech.TECH / LAYER_STACK).
MOM_MIN_WIDTH = 0.14  # min(metal1..metal5 width)
MOM_MIN_SPACING = 0.14  # min(metal1..metal5 spacing)
MOM_VIA_SIZE = 0.26  # Via1/Via2 size
MOM_VIA_PITCH = 0.36  # Via1/Via2 "spacing" (used as pitch by IHP via_array)
MOM_VIA_ENCLOSURE = 0.06
MOM_METAL_THICKNESS = {"M1": 0.42, "M2": 0.49, "M3": 0.49}

_METALS = {"M1": LAYER.M1, "M2": LAYER.M2, "M3": LAYER.M3}
_VIAS_ABOVE = {"M1": LAYER.VIA1, "M2": LAYER.VIA2}


def _rect(c: gf.Component, x0: float, y0: float, x1: float, y1: float, layer) -> None:
    c.add_polygon([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], layer=layer)


@gf.cell(tags=["electrical", "capacitor"])
def cmim(
    lc: float = 5,
    wc: float = 5,
    label: bool = False,
    top_label: str = "",
    bot_label: str = "",
) -> gf.Component:
    """Returns a MIM capacitor (M2 bottom plate, MIM top plate, VIA2 to M3).

    Port of gf180mcu ``cap_mim`` (MIM-A option, Magic cap_mim_2p0fF geometry).

    Args:
        lc: capacitor plate length (y) in um.
        wc: capacitor plate width (x) in um.
        label: if True, add top_label/bot_label text on the TEXT layer.
        top_label: label text for the top terminal.
        bot_label: label text for the bottom terminal.
    """
    c = gf.Component()

    cap_surround = 0.4
    bot_surround = 0.6
    end_surround = 0.31
    end_spacing = 0.60
    contact_size = 0.36
    metal_surround = 0.05
    via_size = 0.26
    diff_surround = 0.065
    cap_via_pitch = 0.76
    arm_via_pitch = 0.52

    hw = wc / 2
    hl = lc / 2
    cl = lc + 2 * bot_surround - 2 * end_surround - metal_surround

    # Via cluster on the cap plate.
    cap_hw = hw - cap_surround
    cap_hl = hl - cap_surround
    cap_ncols = floor((2 * cap_hw - via_size) / cap_via_pitch) + 1
    cap_nrows = floor((2 * cap_hl - via_size) / cap_via_pitch) + 1
    cap_array_w = (cap_ncols - 1) * cap_via_pitch + via_size
    cap_array_h = (cap_nrows - 1) * cap_via_pitch + via_size

    # Via cluster on the contact arm to the right.
    m3_arm_enc_y = end_surround + diff_surround
    arm_nrows = (
        floor((lc + 2 * (bot_surround - m3_arm_enc_y - via_size / 2)) / arm_via_pitch)
        + 1
    )
    arm_ncols = floor(contact_size / via_size) + 2
    arm_array_w = (arm_ncols - 1) * arm_via_pitch + via_size
    arm_array_h = (arm_nrows - 1) * arm_via_pitch + via_size
    cursor_x = hw + bot_surround + end_spacing
    arm_via_x0 = cursor_x - contact_size / 2 + (arm_via_pitch - end_surround)
    arm_via_cx = arm_via_x0 + arm_array_w / 2

    m3_arm_w = arm_array_w + 2 * 0.25
    m3_arm_h = cl + arm_via_pitch - via_size - 2 * metal_surround

    m2_xmin = -(hw + bot_surround)
    m2_ymin = -(hl + bot_surround)
    m2_xmax = arm_via_cx + m3_arm_w / 2 + end_surround
    m2_ymax = hl + bot_surround

    # Center the M2 bottom plate on the origin (Magic cap_draw centering).
    sx = -(m2_xmax + m2_xmin) / 2
    sy = -(m2_ymax + m2_ymin) / 2

    def r(x0: float, y0: float, x1: float, y1: float, layer) -> None:
        _rect(c, round(x0 + sx, 4), round(y0 + sy, 4), round(x1 + sx, 4), round(y1 + sy, 4), layer)  # fmt: skip

    r(-hw, -hl, hw, hl, LAYER.MIM)
    r(-hw - 0.2, -hl - 0.2, hw + 0.2, hl + 0.2, LAYER.CAP_MK)
    r(-cap_hw, -cap_hl, cap_hw, cap_hl, LAYER.M3)
    r(arm_via_cx - m3_arm_w / 2, -m3_arm_h / 2, arm_via_cx + m3_arm_w / 2, m3_arm_h / 2, LAYER.M3)  # fmt: skip
    # M2 frame around the cap plate (top, bottom, left, right incl. arm).
    r(m2_xmin, hl, m2_xmax, m2_ymax, LAYER.M2)
    r(m2_xmin, m2_ymin, m2_xmax, -hl, LAYER.M2)
    r(m2_xmin, -hl, -hw, hl, LAYER.M2)
    r(hw, -hl, m2_xmax, hl, LAYER.M2)

    via = gf.components.rectangle(size=(via_size, via_size), layer=LAYER.VIA2)
    c.add_ref(
        via,
        columns=cap_ncols,
        rows=cap_nrows,
        column_pitch=cap_via_pitch,
        row_pitch=cap_via_pitch,
    ).move((round(-cap_array_w / 2 + sx, 4), round(-cap_array_h / 2 + sy, 4)))
    c.add_ref(
        via,
        columns=arm_ncols,
        rows=arm_nrows,
        column_pitch=arm_via_pitch,
        row_pitch=arm_via_pitch,
    ).move((round(arm_via_x0 + sx, 4), round(-arm_array_h / 2 + sy, 4)))

    c.add_port(
        name="top",
        center=(round(sx, 4), round(sy, 4)),
        width=wc,
        orientation=90,
        layer=LAYER.M3,
        port_type="electrical",
    )
    c.add_port(
        name="bottom",
        center=(0, 0),
        width=round(m2_xmax - m2_xmin, 4),
        orientation=90,
        layer=LAYER.M2,
        port_type="electrical",
    )
    if label:
        c.add_label(top_label, position=c.ports["top"].center, layer=LAYER.TEXT)
        c.add_label(bot_label, position=c.ports["bottom"].center, layer=LAYER.TEXT)

    c.info["model"] = "cmim"
    c.info["capacitance_fF"] = MIM_CAP_DENSITY * lc * wc
    c.info["lc"] = lc
    c.info["wc"] = wc
    return c


def _cmom_capacitance(
    nfingers: int, length: float, spacing: float, metals: list[str]
) -> float:
    """IHP cmom_extractor: parallel-plate finger estimate + 20% fringe, in fF."""
    eps = 3.8 * 8.8541878188e-3  # fF/um
    total = sum(
        eps
        * (MOM_METAL_THICKNESS[m] / spacing)
        * (2 * nfingers * (length + spacing) + MOM_MIN_WIDTH * (2 * nfingers + 1))
        for m in metals
    )
    return total * 1.2


@gf.cell(tags=["electrical", "capacitor"])
def cmom(
    nfingers: int = 1,
    length: float = 4.0,
    spacing: float = 0.26,
    botmetal: Literal["M1", "M2", "M3"] = "M1",
    topmetal: Literal["M1", "M2", "M3"] = "M3",
) -> gf.Component:
    """Returns a MOM (metal-oxide-metal) interdigitated finger capacitor.

    Port of IHP ``cmom``: the same finger comb is drawn on every metal from
    botmetal to topmetal and the bus bars are stitched with via arrays.

    Args:
        nfingers: number of inner (MINUS) fingers; PLUS has nfingers + 1.
        length: finger length in um.
        spacing: spacing between PLUS and MINUS fingers in um.
        botmetal: lowest metal of the stack.
        topmetal: highest metal of the stack.
    """
    order = list(_METALS)
    if botmetal not in order or topmetal not in order:
        raise ValueError(f"botmetal/topmetal must be in {order}")
    if order.index(botmetal) > order.index(topmetal):
        raise ValueError(f"botmetal {botmetal!r} is above topmetal {topmetal!r}")
    if length <= 3 * MOM_MIN_WIDTH:
        raise ValueError(f"length must be > {3 * MOM_MIN_WIDTH}")
    if spacing <= MOM_MIN_SPACING:
        raise ValueError(f"spacing must be > {MOM_MIN_SPACING}")
    if nfingers < 1:
        raise ValueError("nfingers must be >= 1")

    metals = order[order.index(botmetal) : order.index(topmetal) + 1]
    w = MOM_MIN_WIDTH
    pitch = 2 * (spacing + w)
    total_length = (w + spacing) * (2 * nfingers + 1) - spacing
    pad_h = 3 * w

    c = gf.Component()
    for m in metals:
        layer = _METALS[m]
        for i in range(nfingers + 1):  # PLUS fingers, attached to the top bar
            _rect(c, i * pitch, spacing, i * pitch + w, spacing + length, layer)
        for i in range(nfingers):  # MINUS fingers, attached to the bottom bar
            x0 = w + spacing + i * pitch
            _rect(c, x0, 0, x0 + w, length, layer)
        _rect(c, 0, length + spacing, total_length, length + spacing + pad_h, layer)
        _rect(c, 0, -pad_h, total_length, 0, layer)

    # Marker and boundary cover the bus-bar extent (vias sit inside it).
    for marker in (LAYER.CAP_MK, LAYER.DEVREC):
        _rect(c, 0, -pad_h, total_length, length + spacing + pad_h, marker)

    # Via arrays stitching the bus bars (IHP via_stack, single row).
    ncols = min(
        4 * nfingers,
        int((total_length - 2 * MOM_VIA_ENCLOSURE - MOM_VIA_SIZE) / MOM_VIA_PITCH) + 1,
    )
    array_w = (ncols - 1) * MOM_VIA_PITCH + MOM_VIA_SIZE
    via_x0 = total_length / 2 - array_w / 2
    top_cy = length + spacing + pad_h / 2
    bot_cy = -pad_h / 2
    for m in metals[:-1]:
        via = gf.components.rectangle(
            size=(MOM_VIA_SIZE, MOM_VIA_SIZE), layer=_VIAS_ABOVE[m]
        )
        for cy in (top_cy, bot_cy):
            c.add_ref(via, columns=ncols, rows=1, column_pitch=MOM_VIA_PITCH).move(
                (via_x0, cy - MOM_VIA_SIZE / 2)
            )

    c.add_port(
        "PLUS",
        center=(total_length / 2, top_cy),
        width=w,
        orientation=90,
        layer=_METALS[topmetal],
        port_type="electrical",
    )
    c.add_port(
        "MINUS",
        center=(total_length / 2, bot_cy),
        width=w,
        orientation=270,
        layer=_METALS[topmetal],
        port_type="electrical",
    )

    c.info["model"] = "cmom"
    c.info["capacitance_fF"] = _cmom_capacitance(nfingers, length, spacing, metals)
    c.info["nfingers"] = nfingers
    c.info["length"] = length
    c.info["spacing"] = spacing
    return c
