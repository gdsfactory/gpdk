"""Generic 3.3V MOSFET parametric cells (``nch``, ``pch``).

Ported from the gf180mcu ``nfet``/``pfet`` generators, which replicate the
open_pdks Magic VLSI procedures polygon-for-polygon:
  - gf180mcu::mos_device   (single finger drawing)
  - gf180mcu::mos_draw     (tiling + guard ring)
  - gf180mcu::draw_contact (contact + surround + metal)
  - gf180mcu::guard_ring   (substrate guard ring)

Only the 3.3V device path is ported (no 5V/6V/10V, native, deep n-well,
DSS or asymmetric variants).

All geometric computations use Magic's "painted" dimension values (contact_size
= 0.23, diff_surround = 0.065, etc.).  At the point of polygon output, these
are converted to physical GDS dimensions:
  - contact cut = 0.22 (painted 0.23 shrunk by 0.005/side in CIF)
  - active surround = 0.07 (painted 0.065 grown by 0.005/side in CIF)
  - metal surround  = 0.06 (painted 0.055 grown by 0.005/side in CIF)

The total envelope is conserved (0.23/2 + 0.065 = 0.22/2 + 0.07 = 0.18).
"""

from __future__ import annotations

from math import floor
from typing import Literal

import gdsfactory as gf
import klayout.db as kdb
from gdsfactory.add_pins import add_electrical_pins
from gdsfactory.typings import Strs

from gpdk.layer_map import LAYER

__all__ = ["nch", "pch"]

# ---------------------------------------------------------------------------
# Grid snapping — Magic CIF output grid is 5 nm
# ---------------------------------------------------------------------------

_GRID = 0.005  # 5 nm


def _snap(v: float) -> float:
    """Round *v* to the nearest 5 nm grid point."""
    return round(round(v / _GRID) * _GRID, 4)


def _um(v: float) -> int:
    """Convert microns to integer database units (1 nm)."""
    return round(v * 1000)


# ---------------------------------------------------------------------------
# Magic ruleset (from gf180mcu::ruleset in open_pdks gf180mcu.tcl)
# These are the "painted" values used for all geometric computations.
# ---------------------------------------------------------------------------

_RULES = dict(
    contact_size=0.23,
    poly_surround=0.065,
    diff_surround=0.065,
    gate_to_diffcont=0.26,
    gate_to_polycont=0.28,
    gate_extension=0.22,
    diff_extension=0.23,
    metal_surround=0.055,
    sub_surround=0.12,
    diff_spacing=0.33,
    poly_spacing=0.24,
    diff_poly_space=0.10,
    diff_gate_space=0.11,
    metal_spacing=0.23,
)

# Physical GDS dimensions (after CIF conversion)
_CIF_CONTACT_CUT = 0.22  # contact cut
_CIF_CONTACT_PITCH = 0.47  # contact cut 0.22 + min gap 0.25

# Layer aliases
_L_COMP = LAYER.ACTIVE
_L_POLY = LAYER.POLY
_L_PPLUS = LAYER.PPP
_L_NPLUS = LAYER.NPP
_L_CONTACT = LAYER.VIAC
_L_METAL1 = LAYER.M1
_L_NWELL = LAYER.NWELL


# ---------------------------------------------------------------------------
# Helper: add a snapped rectangle
# ---------------------------------------------------------------------------


def _rect(c, x0, y0, x1, y1, layer_spec):
    x0, y0, x1, y1 = _snap(x0), _snap(y0), _snap(x1), _snap(y1)
    if abs(x1 - x0) < 1e-6 or abs(y1 - y0) < 1e-6:
        return
    c.add_polygon([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], layer=layer_spec)


# ---------------------------------------------------------------------------
# Contact cut array — places 0.22 x 0.22 cuts with 0.47 pitch
# ---------------------------------------------------------------------------


def _contact_cuts(c, cx, cy, w_envelope, h_envelope):
    """Place contact cuts within an envelope centered at (cx, cy).

    The envelope is the painted region size (using Magic's contact_size).
    In CIF output the contact region shrinks by 0.005/side, so the physical
    area is envelope - 0.01 per axis: painted 0.23 -> one 0.22 cut; larger
    regions get floor((phys - cut) / pitch) + 1 cuts with a 0.25 gap.
    """
    cut = _CIF_CONTACT_CUT
    pitch = _CIF_CONTACT_PITCH

    phys_w = max(w_envelope - 0.01, cut)
    phys_h = max(h_envelope - 0.01, cut)

    nx = max(1, floor((phys_w - cut) / pitch + 1 + 1e-6))
    ny = max(1, floor((phys_h - cut) / pitch + 1 + 1e-6))

    span_x = (nx - 1) * pitch
    span_y = (ny - 1) * pitch

    for ix in range(nx):
        for iy in range(ny):
            x = _snap(cx - span_x / 2.0 + ix * pitch)
            y = _snap(cy - span_y / 2.0 + iy * pitch)
            _rect(c, x - cut / 2, y - cut / 2, x + cut / 2, y + cut / 2, _L_CONTACT)


# ---------------------------------------------------------------------------
# draw_contact — replicates gf180mcu::draw_contact
# ---------------------------------------------------------------------------


def _draw_contact(c, cx, cy, w, h, rules, active_layer, orient="vert"):
    """Draw contact with surrounding active/poly and metal1.

    w, h: requested contact area size (painted dimensions).
    cx, cy: center position.
    orient: "vert" (metal grows N/S), "horz" (metal grows E/W).

    Returns (ax0, ay0, ax1, ay1): active/poly surround bounding box.
    """
    contact_size = rules["contact_size"]
    diff_surround = rules["diff_surround"]
    metal_surround = rules["metal_surround"]

    # Enforce minimum painted size
    cw = max(w, contact_size)
    ch = max(h, contact_size)

    hw = cw / 2.0
    hh = ch / 2.0

    # Contact cuts (physical 0.22 within the painted region)
    _contact_cuts(c, cx, cy, cw, ch)

    # Active/poly surround: total extent hw + diff_surround (painted) is the
    # same boundary as the physical GDS active.
    ds = diff_surround
    ax0 = _snap(cx - hw - ds)
    ay0 = _snap(cy - hh - ds)
    ax1 = _snap(cx + hw + ds)
    ay1 = _snap(cy + hh + ds)
    _rect(c, ax0, ay0, ax1, ay1, active_layer)

    # Metal1 surround
    ms = metal_surround
    mx0, my0, mx1, my1 = cx - hw, cy - hh, cx + hw, cy + hh
    if orient in ("vert", "full"):
        my0 = cy - hh - ms
        my1 = cy + hh + ms
    if orient in ("horz", "full"):
        mx0 = cx - hw - ms
        mx1 = cx + hw + ms
    _rect(c, mx0, my0, mx1, my1, _L_METAL1)

    return (ax0, ay0, ax1, ay1)


# ---------------------------------------------------------------------------
# Guard ring — replicates gf180mcu::guard_ring
# ---------------------------------------------------------------------------


def _guard_ring(c, gx, gy, rules, sub_layer):
    """Draw guard ring centered at origin, contacted on the left and right sides.

    gx, gy: guard ring size measured to contact centers (painted coords).
    sub_layer: well layer drawn around the ring, or None to skip it.
    """
    contact_size = rules["contact_size"]
    diff_surround = rules["diff_surround"]
    metal_surround = rules["metal_surround"]
    metal_spacing = rules["metal_spacing"]
    sub_surround = rules["sub_surround"]

    hx = contact_size / 2.0
    hw = gx / 2.0
    hh = gy / 2.0

    difft = contact_size + 2 * diff_surround
    hdifft = difft / 2.0
    hdiffw = (gx + difft) / 2.0
    hdiffh = (gy + difft) / 2.0

    # Guard ring diffusion (active layer) — 4 bars forming a ring
    _rect(c, -hdiffw, hh - hdifft, hdiffw, hh + hdifft, _L_COMP)  # top
    _rect(c, -hdiffw, -hh - hdifft, hdiffw, -hh + hdifft, _L_COMP)  # bottom
    _rect(c, hw - hdifft, -hdiffh, hw + hdifft, hdiffh, _L_COMP)  # right
    _rect(c, -hw - hdifft, -hdiffh, -hw + hdifft, hdiffh, _L_COMP)  # left

    # Full metal ring
    hmetw = (gx + contact_size) / 2.0
    hmeth = (gy + contact_size) / 2.0
    _rect(c, -hmetw, hh - hx, hmetw, hh + hx, _L_METAL1)  # top
    _rect(c, -hmetw, -hh - hx, hmetw, -hh + hx, _L_METAL1)  # bottom
    _rect(c, hw - hx, -hmeth, hw + hx, hmeth, _L_METAL1)  # right
    _rect(c, -hw - hx, -hmeth, -hw + hx, hmeth, _L_METAL1)  # left

    # Contact height for side contacts
    ch = gy - contact_size - 2 * (metal_surround + metal_spacing)
    if ch < contact_size:
        ch = contact_size

    # Side contacts
    _draw_contact(c, hw, 0, 0, ch, rules, _L_COMP, "vert")
    _draw_contact(c, -hw, 0, 0, ch, rules, _L_COMP, "vert")

    # Substrate/well layer
    sub_ext = hx + diff_surround + sub_surround
    if sub_layer is not None:
        _rect(c, -hw - sub_ext, -hh - sub_ext, hw + sub_ext, hh + sub_ext, sub_layer)

    return (-hw - sub_ext, -hh - sub_ext, hw + sub_ext, hh + sub_ext)


# ---------------------------------------------------------------------------
# Guard ring implant
# ---------------------------------------------------------------------------


def _guard_ring_implant(c, gx, gy, implant_layer, rules):
    """Draw implant for the guard ring.

    Magic's CIF output generates implant shapes around the guard ring
    diffusion with technology-specific bloat/shrink rules.

    For pplus (NFET guard ring): 8 rectangles with ~0.02/0.03 bloat
    For nplus (PFET guard ring): 4 rectangles with ~0.16 bloat
    """
    contact_size = rules["contact_size"]
    diff_surround = rules["diff_surround"]
    metal_surround = rules["metal_surround"]
    metal_spacing = rules["metal_spacing"]

    hw = gx / 2.0
    hh = gy / 2.0
    difft = contact_size + 2 * diff_surround
    hdifft = difft / 2.0
    hdiffw = (gx + difft) / 2.0

    # GR active bar extents
    bar_outer_x = _snap(hdiffw)
    bar_outer_y = _snap(hh + hdifft)
    bar_inner_y = _snap(hh - hdifft)
    side_outer_x = _snap(hw + hdifft)
    side_inner_x = _snap(hw - hdifft)

    # Guard ring side contact height (from guard_ring function)
    ch = gy - contact_size - 2 * (metal_surround + metal_spacing)
    if ch < contact_size:
        ch = contact_size
    # Side bar implant Y extent = contact surround + CIF bloat.
    # The psd/nsd painted region extends ch/2 + diff_surround from center,
    # plus the CIF implant bloat.
    side_bloat_y = 0.03  # CIF Y-direction bloat for side bars
    side_impl_half_y = _snap(ch / 2.0 + diff_surround + side_bloat_y)

    if implant_layer == _L_PPLUS:
        # NFET guard ring: pplus with small CIF bloat (~0.02-0.03)
        enc_tb = 0.02  # top/bottom bar bloat
        enc_side_x = 0.03  # side bar X bloat
        bx0, bx1 = -bar_outer_x - enc_tb, bar_outer_x + enc_tb
        lx0, lx1 = -side_outer_x - enc_side_x, -side_inner_x + enc_side_x
        rx0, rx1 = side_inner_x - enc_side_x, side_outer_x + enc_side_x

        # Top / bottom bars
        _rect(c, bx0, bar_inner_y - enc_tb, bx1, bar_outer_y + enc_tb, implant_layer)
        _rect(c, bx0, -bar_outer_y - enc_tb, bx1, -bar_inner_y + enc_tb, implant_layer)
        # Left / right side bars (main body)
        _rect(c, lx0, -side_impl_half_y, lx1, side_impl_half_y, implant_layer)
        _rect(c, rx0, -side_impl_half_y, rx1, side_impl_half_y, implant_layer)
        # Corner pieces (bridge between bars and side bars)
        _rect(c, bx0, side_impl_half_y, lx1, bar_inner_y - enc_tb, implant_layer)
        _rect(c, rx0, side_impl_half_y, bx1, bar_inner_y - enc_tb, implant_layer)
        _rect(c, bx0, -bar_inner_y + enc_tb, lx1, -side_impl_half_y, implant_layer)
        _rect(c, rx0, -bar_inner_y + enc_tb, bx1, -side_impl_half_y, implant_layer)

    else:
        # PFET guard ring: nplus with outer bloat 0.16, inner bloat 0.11 (3.3V)
        enc_out = 0.16
        enc_in = 0.11

        # Inner boundary of the nplus ring
        inner_x = _snap(side_inner_x - enc_in)
        inner_y = _snap(bar_inner_y - enc_in)
        bx0, bx1 = -bar_outer_x - enc_out, bar_outer_x + enc_out

        # Top / bottom bars (full width, from inner_y to outer edge)
        _rect(c, bx0, inner_y, bx1, bar_outer_y + enc_out, implant_layer)
        _rect(c, bx0, -bar_outer_y - enc_out, bx1, -inner_y, implant_layer)
        # Left / right side bars (between inner_y bounds)
        _rect(c, -side_outer_x - enc_out, -inner_y, -inner_x, inner_y, implant_layer)
        _rect(c, inner_x, -inner_y, side_outer_x + enc_out, inner_y, implant_layer)


# ---------------------------------------------------------------------------
# Device implant
# ---------------------------------------------------------------------------


def _device_implant_region(finger_results, bloat=0.16, gate_bloat=0.23):
    """Build a kdb.Region for the device implant.

    For each finger, creates the typed-diffusion shape:
    - Channel region (hw in Y, full X extent)
    - Dogbone extensions (cdwmin/2 in Y, only at S/D contact positions)
    Then bloats by the specified amount.

    The gate region is computed as the UNION of all fingers' gates, then bloated
    once (not per-finger) to avoid artifacts at finger boundaries.
    """
    region = kdb.Region()

    for r in finger_results:
        # Channel extent (hw in Y, full X)
        cx0, cy0, cx1, cy1 = r["channel"]
        region.insert(
            kdb.Box(
                _um(cx0 - bloat), _um(cy0 - bloat), _um(cx1 + bloat), _um(cy1 + bloat)
            )
        )

        # Dogbone tabs (individual rectangles, not bounding box)
        for t0, t1, t2, t3 in r["dogbone_tabs"]:
            region.insert(
                kdb.Box(
                    _um(t0 - bloat), _um(t1 - bloat), _um(t2 + bloat), _um(t3 + bloat)
                )
            )

    # Gate region: for dogbone devices (w < cdwmin), add each finger's gate
    # individually so the gap between fingers is preserved (implant notch at
    # shared contacts). For non-dogbone, use bounding box of all gates.
    if finger_results:
        # Detect dogbone: channel Y extent < active Y extent
        r0 = finger_results[0]
        is_dogbone = (
            abs(r0["channel"][3] - r0["channel"][1])
            < abs(r0["active"][3] - r0["active"][1]) - 0.001
        )
        if is_dogbone and len(finger_results) > 1:
            gates = [r["gate"] for r in finger_results]
        else:
            gates = [
                (
                    min(r["gate"][0] for r in finger_results),
                    min(r["gate"][1] for r in finger_results),
                    max(r["gate"][2] for r in finger_results),
                    max(r["gate"][3] for r in finger_results),
                )
            ]
        for gx0, gy0, gx1, gy1 in gates:
            region.insert(
                kdb.Box(
                    _um(gx0 - gate_bloat),
                    _um(gy0 - gate_bloat),
                    _um(gx1 + gate_bloat),
                    _um(gy1 + gate_bloat),
                )
            )

    return region.merged()


def _draw_region(c, region, layer_spec):
    """Draw a kdb.Region as polygons on the given layer."""
    for poly in region.each():
        points = [
            (_snap(p.x / 1000.0), _snap(p.y / 1000.0)) for p in poly.each_point_hull()
        ]
        if len(points) >= 3:
            c.add_polygon(points, layer=layer_spec)


# ---------------------------------------------------------------------------
# Single MOS device geometry computation
# ---------------------------------------------------------------------------


def _mos_geometry(w, ln, rules, topc=True, botc=True):
    """Compute geometry for one MOS finger using Magic's algorithm.

    Returns dict with all coordinates needed for drawing and tiling.
    All values in Magic's "painted" coordinate space.
    """
    eps = 0.0005
    contact_size = rules["contact_size"]
    diff_surround = rules["diff_surround"]
    poly_surround = rules["poly_surround"]
    gate_to_diffcont = rules["gate_to_diffcont"]
    gate_to_polycont = rules["gate_to_polycont"]
    gate_extension = rules["gate_extension"]
    diff_extension = rules["diff_extension"]
    diff_poly_space = rules["diff_poly_space"]

    hw = w / 2.0
    hl = ln / 2.0

    # --- Dogbone Rule 1: diffusion contact ---
    cdwmin = contact_size + 2 * diff_surround
    cstem = gate_to_diffcont - cdwmin / 2.0
    cgrow = diff_poly_space - cstem
    diffcont_orient = "vert"
    ddover = 0.0

    if (w + eps) < cdwmin:
        if cgrow > 0:
            gate_to_diffcont += cgrow
            diffcont_orient = "horz"
        ddover = (cdwmin - w) / 2.0

    # --- Rule 2: poly contact dogbone ---
    cplmin = contact_size + 2 * poly_surround
    cstem_p = gate_to_polycont - cplmin / 2.0
    cgrow_p = diff_poly_space - cstem_p
    if (ln + eps) < cplmin:
        if cgrow_p > 0:
            gate_to_polycont += cgrow_p

    # --- Rule 3: both dogbone ---
    if (w + eps) < cdwmin and (ln + eps) < cplmin:
        cgrow3 = (cplmin - w) / 2.0
        gate_to_polycont += cgrow3

    # --- Contact dimensions ---
    cdw = w - 2 * diff_surround
    cpl = ln - 2 * poly_surround

    # --- Diffusion extent from gate edge ---
    hc = contact_size / 2.0
    if diff_extension > gate_to_diffcont:
        diff_grow_d = diff_extension  # drain side
        diff_grow_s = diff_extension  # source side
    else:
        diff_grow_d = gate_to_diffcont + hc
        diff_grow_s = gate_to_diffcont + hc

    # --- Poly extent ---
    if gate_extension > gate_to_polycont:
        poly_ext_top = gate_extension
        poly_ext_bot = gate_extension
    else:
        poly_ext_top = gate_to_polycont if topc else gate_extension
        poly_ext_bot = gate_to_polycont if botc else gate_extension

    # --- Single device bounding box (used for tiling) ---
    # fw and fh are the bounding box extents returned by mos_device (cext).
    # They include all drawn elements: diffusion + contact surround + poly pads.
    #
    # fw: The diffusion contact's active surround extends diff_surround beyond
    # the painted contact region. So the total X extent from gate center is:
    #   hl + diff_grow + diff_surround
    # where diff_grow includes gate_to_diffcont + contact_size/2.
    fw = 2 * (hl + max(diff_grow_d, diff_grow_s) + diff_surround)

    # fh: From the max of (poly gate extent) and (poly contact pad extent).
    # Poly gate: hw + poly_ext_top (= gate_extension or gate_to_polycont)
    # Contact pad: hw + gate_to_polycont + poly_surround + contact_size/2
    # Diffusion contact extents in Y (dogbone: cdwmin/2 + diff_surround) are
    # typically smaller, so fh is dominated by the poly pads.
    if topc:
        top_ext = max(
            poly_ext_top, gate_to_polycont + poly_surround + contact_size / 2.0
        )
    else:
        top_ext = poly_ext_top
    if botc:
        bot_ext = max(
            poly_ext_bot, gate_to_polycont + poly_surround + contact_size / 2.0
        )
    else:
        bot_ext = poly_ext_bot
    fh = hw + top_ext + hw + bot_ext

    return dict(
        w=w,
        l=ln,
        hw=hw,
        hl=hl,
        gate_to_diffcont=gate_to_diffcont,
        gate_to_polycont=gate_to_polycont,
        gate_extension=gate_extension,
        diff_grow_d=diff_grow_d,
        diff_grow_s=diff_grow_s,
        poly_ext_top=poly_ext_top,
        poly_ext_bot=poly_ext_bot,
        diffcont_orient=diffcont_orient,
        ddover=ddover,
        cdw=cdw,
        cpl=cpl,
        fw=fw,
        fh=fh,
        cdwmin=cdwmin,
        cplmin=cplmin,
    )


# ---------------------------------------------------------------------------
# Draw single MOS device finger
# ---------------------------------------------------------------------------


def _draw_mos_finger(c, cx, cy, geom, rules, evens=1, topc=True, botc=True):
    """Draw one MOS finger at (cx, cy). Returns device extents."""
    w = geom["w"]
    hw = geom["hw"]
    hl = geom["hl"]
    gate_to_diffcont = geom["gate_to_diffcont"]
    gate_to_polycont = geom["gate_to_polycont"]
    diff_grow_d = geom["diff_grow_d"]
    diff_grow_s = geom["diff_grow_s"]
    diffcont_orient = geom["diffcont_orient"]
    cdw = geom["cdw"]
    cpl = geom["cpl"]
    cdwmin = geom["cdwmin"]

    contact_size = rules["contact_size"]
    diff_surround = rules["diff_surround"]
    poly_surround = rules["poly_surround"]

    # Drain/source sides: drain left on even fingers, right on odd
    dside = -1 if evens == 1 else 1
    sside = -dside

    # --- Diffusion (active) painting ---
    # Magic paints drain diff and source diff separately
    if dside == -1:
        drain_left = cx - hl - diff_grow_d
        drain_right = cx + hl
    else:
        drain_left = cx - hl
        drain_right = cx + hl + diff_grow_d

    if sside == -1:
        source_left = cx - hl - diff_grow_s
        source_right = cx + hl
    else:
        source_left = cx - hl
        source_right = cx + hl + diff_grow_s

    comp_left = min(drain_left, source_left)
    comp_right = max(drain_right, source_right)

    # Main active (device)
    _rect(c, comp_left, cy - hw, comp_right, cy + hw, _L_COMP)

    drain_cx = cx + dside * (hl + gate_to_diffcont)
    source_cx = cx + sside * (hl + gate_to_diffcont)
    is_dogbone = w < cdwmin - 0.0001

    # Dogbone extensions for diffusion contacts: the contact's active
    # surround extends beyond the device channel width, painted here as
    # separate rectangles above and below the channel.
    dogbone_tabs = []
    if is_dogbone:
        dog_hw = cdwmin / 2.0
        for scx in (drain_cx, source_cx):
            left = scx - contact_size / 2 - diff_surround
            right = scx + contact_size / 2 + diff_surround
            _rect(c, left, cy + hw, right, cy + dog_hw, _L_COMP)
            _rect(c, left, cy - dog_hw, right, cy - hw, _L_COMP)
            # Tab rectangles for the device implant shape
            left, right = _snap(left), _snap(right)
            dogbone_tabs.append((left, _snap(cy + hw), right, _snap(cy + dog_hw)))
            dogbone_tabs.append((left, _snap(cy - dog_hw), right, _snap(cy - hw)))

    # --- Poly gate ---
    poly_top = cy + hw + geom["poly_ext_top"]
    poly_bot = cy - hw - geom["poly_ext_bot"]
    _rect(c, cx - hl, poly_bot, cx + hl, poly_top, _L_POLY)

    # --- Diffusion contacts ---
    _draw_contact(c, drain_cx, cy, 0, cdw, rules, _L_COMP, diffcont_orient)
    _draw_contact(c, source_cx, cy, 0, cdw, rules, _L_COMP, diffcont_orient)

    # --- Poly contacts ---
    if topc:
        _draw_contact(c, cx, cy + hw + gate_to_polycont, cpl, 0, rules, _L_POLY, "horz")
    if botc:
        _draw_contact(c, cx, cy - hw - gate_to_polycont, cpl, 0, rules, _L_POLY, "horz")

    # Active area extent for device implant.
    # The implant is based on the total typed-diffusion (ndiff/pdiff) extent,
    # which includes: gate painting + contact's active surround.
    # X: hl + gate_to_diffcont + contact_size/2 + diff_surround
    # Y: max(hw, cdwmin/2) — the max of gate height and contact dogbone height
    act_half_x = hl + gate_to_diffcont + contact_size / 2.0 + diff_surround
    act_left = cx - act_half_x
    act_right = cx + act_half_x
    act_half_y = cdwmin / 2.0 if is_dogbone else hw
    act_bot = cy - act_half_y
    act_top = cy + act_half_y

    # Full extent including poly pads (for tiling computation)
    ext_bot = act_bot
    ext_top = act_top
    if topc:
        pad_top = cy + hw + gate_to_polycont + contact_size / 2 + poly_surround
        ext_top = max(ext_top, pad_top)
    if botc:
        pad_bot = cy - hw - gate_to_polycont - contact_size / 2 - poly_surround
        ext_bot = min(ext_bot, pad_bot)

    return dict(
        cext=(_snap(act_left), _snap(ext_bot), _snap(act_right), _snap(ext_top)),
        active=(_snap(act_left), _snap(act_bot), _snap(act_right), _snap(act_top)),
        # Channel extent (just the gate channel, hw in Y, full active X)
        channel=(_snap(act_left), _snap(cy - hw), _snap(act_right), _snap(cy + hw)),
        # Gate extent (just the gate polygon area, for implant gate bloat)
        gate=(_snap(cx - hl), _snap(cy - hw), _snap(cx + hl), _snap(cy + hw)),
        dogbone_tabs=dogbone_tabs,
        drain_cx=_snap(drain_cx),
        source_cx=_snap(source_cx),
    )


# ---------------------------------------------------------------------------
# Main MOS drawing — replicates gf180mcu::mos_draw
# ---------------------------------------------------------------------------


def _mos_draw(c, w, ln, nf, rules, is_nfet=True, topc=True, botc=True, guard=True):
    """Draw complete MOSFET with guard ring. Returns port metadata."""
    contact_size = rules["contact_size"]
    diff_surround = rules["diff_surround"]
    diff_spacing = rules["diff_spacing"]
    diff_gate_space = rules["diff_gate_space"]
    gate_extension = rules["gate_extension"]

    geom = _mos_geometry(w, ln, rules, topc, botc)
    fw = geom["fw"]
    fh = geom["fh"]

    # Tiling pitch (doverlap=1): overlap diffusion contacts
    dx = fw - (diff_surround * 2 + contact_size)

    # Core dimensions
    corex = (nf - 1) * dx + fw
    corey = fh

    # Guard ring adjustments for dogbone
    cdwmin = contact_size + 2 * diff_surround
    if guard and (w + 0.0005) < cdwmin:
        inset = (contact_size + 2 * diff_surround - w) / 2.0
        sdiff = inset + diff_spacing - (gate_extension + diff_gate_space)
        if sdiff > 0:
            if not topc:
                corey += sdiff
            if not botc:
                corey += sdiff

    # Guard ring size (to contact centers)
    gx = corex + 2 * (diff_spacing + diff_surround) + contact_size
    gy = corey + 2 * (diff_gate_space + diff_surround) + contact_size

    # Layer configuration. The nch substrate well (gf180 lvpwell) has no
    # generic-PDK equivalent: the p-substrate is implicit, so it is not drawn.
    if is_nfet:
        gr_implant = _L_PPLUS
        dev_implant = _L_NPLUS
        sub_layer = None
    else:
        gr_implant = _L_NPLUS
        dev_implant = _L_PPLUS
        sub_layer = _L_NWELL

    # Draw guard ring
    if guard:
        _guard_ring(c, gx, gy, rules, sub_layer)
        _guard_ring_implant(c, gx, gy, gr_implant, rules)

    # Draw device fingers
    start_x = -(nf - 1) * dx / 2.0
    evens = 1
    all_finger_results = []
    for i in range(nf):
        fx = start_x + i * dx
        result = _draw_mos_finger(
            c, fx, 0, geom, rules, evens=evens, topc=topc, botc=botc
        )
        all_finger_results.append(result)
        evens = 1 - evens

    # Device implant
    _draw_region(c, _device_implant_region(all_finger_results), dev_implant)

    # -----------------------------------------------------------------
    # Collect port metadata for Source, Drain, Gate, Bulk
    # -----------------------------------------------------------------
    drain_xs = sorted({r["drain_cx"] for r in all_finger_results})
    source_xs = sorted({r["source_cx"] for r in all_finger_results})

    gate_poly_centers = []
    gate_contacts = []
    gate_to_polycont = geom["gate_to_polycont"]
    hw = geom["hw"]
    for i in range(nf):
        fx = start_x + i * dx
        gate_poly_centers.append((_snap(fx), 0.0))
        if topc:
            gate_contacts.append((_snap(fx), _snap(hw + gate_to_polycont)))
        if botc:
            gate_contacts.append((_snap(fx), _snap(-(hw + gate_to_polycont))))

    bulk_contacts = []
    if guard:
        bulk_contacts = [
            (0.0, _snap(gy / 2.0)),
            (0.0, _snap(-gy / 2.0)),
            (_snap(-gx / 2.0), 0.0),
            (_snap(gx / 2.0), 0.0),
        ]

    return dict(
        drain_xs=drain_xs,
        source_xs=source_xs,
        sd_port_width=max(geom["cdw"], contact_size),
        gate_poly_centers=gate_poly_centers,
        gate_poly_width=ln,
        gate_contacts=gate_contacts,
        gate_contact_width=max(geom["cpl"], contact_size),
        bulk_contacts=bulk_contacts,
        bulk_port_width=contact_size + 2 * diff_surround,
    )


# ---------------------------------------------------------------------------
# Port / pin helper
# ---------------------------------------------------------------------------


def _add_mos_ports(c, port_data):
    """Add electrical ports and logical pins to a MOSFET component."""

    def add(prefix, centers, width, layer, names=None):
        names = [] if names is None else names
        for x, y in centers:
            name = f"{prefix}_{len(names)}"
            c.add_port(
                name=name,
                center=(float(x), float(y)),
                width=float(width),
                orientation=90,
                layer=layer,
                port_type="electrical",
            )
            names.append(name)
        return names

    sd_w = port_data["sd_port_width"]
    drain_c = [(x, 0.0) for x in port_data["drain_xs"]]
    source_c = [(x, 0.0) for x in port_data["source_xs"]]
    pin_mapping = {
        "Drain": add("Drain", drain_c, sd_w, _L_METAL1),
        "Source": add("Source", source_c, sd_w, _L_METAL1),
    }

    # Gate ports: poly gate centers first, then poly contacts (on metal1)
    gate_ports = add(
        "Gate", port_data["gate_poly_centers"], port_data["gate_poly_width"], _L_POLY
    )
    pin_mapping["Gate"] = add(
        "Gate",
        port_data["gate_contacts"],
        port_data["gate_contact_width"],
        _L_METAL1,
        gate_ports,
    )

    bulk_ports = add(
        "Bulk", port_data["bulk_contacts"], port_data["bulk_port_width"], _L_METAL1
    )
    if bulk_ports:
        pin_mapping["Bulk"] = bulk_ports

    # No pin layer maps: registers logical pins only, no pin marker shapes.
    add_electrical_pins(c, port_pin_mapping=pin_mapping)


def _mos(
    model: str, l_gate: float, w_gate: float, nf: int, grw: float, gate_con_pos: str
) -> gf.Component:
    c = gf.Component()
    port_data = _mos_draw(
        c,
        w_gate,
        l_gate,
        nf,
        _RULES,
        is_nfet=model == "nch",
        topc=gate_con_pos in ("alternating", "top"),
        botc=gate_con_pos in ("alternating", "bottom"),
        guard=grw > 0,
    )
    _add_mos_ports(c, port_data)
    c.info["model"] = model
    c.info["l_gate"] = l_gate
    c.info["w_gate"] = w_gate
    c.info["nf"] = nf
    return c


# ---------------------------------------------------------------------------
# Public cells
# ---------------------------------------------------------------------------


@gf.cell(tags=["electrical", "mos"])
def nch(
    l_gate: float = 0.28,
    w_gate: float = 0.22,
    sd_con_col: int = 1,
    inter_sd_l: float = 0.24,
    nf: int = 1,
    grw: float = 0.22,
    bulk: str = "None",
    con_bet_fin: int = 1,
    gate_con_pos: Literal["alternating", "top", "bottom", "none"] = "alternating",
    interdig: int = 0,
    patt: str = "",
    label: bool = False,
    sd_label: Strs | None = (),
    g_label: Strs = (),
    sub_label: str = "",
    patt_label: bool = False,
) -> gf.Component:
    """Return a 3.3V NMOS transistor with a p+ guard ring.

    Ports: ``Drain_i``/``Source_i`` (metal1, S/D contact centers),
    ``Gate_i`` (poly gate centers, then metal1 poly contacts) and
    ``Bulk_i`` (metal1 guard ring, top/bottom/left/right; only if ``grw > 0``).

    Args:
        l_gate: gate length in microns.
        w_gate: gate width in microns.
        sd_con_col: number of source/drain contact columns (not used by the geometry).
        inter_sd_l: inter source/drain length (not used by the geometry).
        nf: number of gate fingers.
        grw: guard-ring width; set to 0 to disable the guard ring.
        bulk: bulk connection option (not used by the geometry).
        con_bet_fin: contacts between fingers (not used by the geometry).
        gate_con_pos: gate contact position ("alternating"=both, "top"=top only,
            "bottom"=bottom only, "none"=remove all).
        interdig: interdigitated layout toggle (not used by the geometry).
        patt: gate pattern option (not used by the geometry).
        label: add text labels (not used by the geometry).
        sd_label: per-terminal source/drain label strings (not used by the geometry).
        g_label: gate label strings (not used by the geometry).
        sub_label: substrate label string (not used by the geometry).
        patt_label: enable pattern labels (not used by the geometry).
    """
    return _mos("nch", l_gate, w_gate, nf, grw, gate_con_pos)


@gf.cell(tags=["electrical", "mos"])
def pch(
    l_gate: float = 0.28,
    w_gate: float = 0.22,
    sd_con_col: int = 1,
    inter_sd_l: float = 0.24,
    nf: int = 1,
    grw: float = 0.22,
    bulk: str = "None",
    con_bet_fin: int = 1,
    gate_con_pos: Literal["alternating", "top", "bottom", "none"] = "alternating",
    interdig: int = 0,
    patt: str = "",
    label: bool = False,
    sd_label: Strs | None = (),
    g_label: Strs = (),
    sub_label: str = "",
    patt_label: bool = False,
) -> gf.Component:
    """Return a 3.3V PMOS transistor in an n-well with an n+ guard ring.

    Ports: ``Drain_i``/``Source_i`` (metal1, S/D contact centers),
    ``Gate_i`` (poly gate centers, then metal1 poly contacts) and
    ``Bulk_i`` (metal1 guard ring, top/bottom/left/right; only if ``grw > 0``).

    Args:
        l_gate: gate length in microns.
        w_gate: gate width in microns.
        sd_con_col: number of source/drain contact columns (not used by the geometry).
        inter_sd_l: inter source/drain length (not used by the geometry).
        nf: number of gate fingers.
        grw: guard-ring width; set to 0 to disable the guard ring.
        bulk: bulk connection option (not used by the geometry).
        con_bet_fin: contacts between fingers (not used by the geometry).
        gate_con_pos: gate contact position ("alternating"=both, "top"=top only,
            "bottom"=bottom only, "none"=remove all).
        interdig: interdigitated layout toggle (not used by the geometry).
        patt: gate pattern option (not used by the geometry).
        label: add text labels (not used by the geometry).
        sd_label: per-terminal source/drain label strings (not used by the geometry).
        g_label: gate label strings (not used by the geometry).
        sub_label: substrate label string (not used by the geometry).
        patt_label: enable pattern labels (not used by the geometry).
    """
    return _mos("pch", l_gate, w_gate, nf, grw, gate_con_pos)
