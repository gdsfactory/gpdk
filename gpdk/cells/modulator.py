"""Ribbed (corrugated) lateral PN-junction phase shifter."""

from __future__ import annotations

import gdsfactory as gf

from gpdk.layer_map import LAYER

__all__ = ["straight_pn_ribbed"]

# Continuous full-length strips: (layer, y-offset from core, width, x-inset per end).
# SHALLOW_ETCH is two partial-etch rails straddling the core centreline (0.4 um gap).
# Lateral PN junction: P side below the core (y < 0), N side above (y > 0).
_STRIPS = (
    (LAYER.SHALLOW_ETCH, -0.95, 1.5, 0.0),
    (LAYER.SHALLOW_ETCH, 0.95, 1.5, 0.0),
    (LAYER.PPP, -2.465, 3.61, 0.25),
    (LAYER.PP, -1.75, 2.9, 0.0),
    (LAYER.P, -1.55, 3.3, 0.0),
    (LAYER.N, 1.65, 3.1, 0.0),
    (LAYER.NP, 1.75, 2.9, 0.0),
    (LAYER.NPP, 2.465, 3.61, 0.25),
)
_JUNCTION_Y = 0.1  # P (top edge -1.55 + 3.3 / 2) meets N (bottom edge 1.65 - 3.1 / 2)

# Per-period M1 electrode pad (one per side), centred in the period.
_M1_Y = 2.73
_M1_SIZE = (9.0, 2.0)

# Per-period VIAC contact array: 3 rows per side, 37 columns on a 0.236 um pitch.
_CA_SIZE = 0.09
_CA_ROWS = (1.979, 2.215, 2.451)
_CA_X0 = 0.752  # first contact centre, relative to the period start
_CA_PITCH = 0.236
_CA_NCOL = 37


def _rect(c: gf.Component, size, center, layer) -> None:
    """Add a ``size=(w, h)`` rectangle centred at ``center`` on ``layer``."""
    (w, h), (cx, cy) = size, center
    c.add_polygon(
        [
            (cx - w / 2, cy - h / 2),
            (cx + w / 2, cy - h / 2),
            (cx + w / 2, cy + h / 2),
            (cx - w / 2, cy + h / 2),
        ],
        layer=layer,
    )


@gf.cell
def _unit_cell(period: float, width: float, tooth_length: float) -> gf.Component:
    """One period: full-width WG tooth, M1 pads and VIAC contacts on both sides."""
    c = gf.Component()
    _rect(c, (tooth_length, width), (period / 2, 0.0), LAYER.WG)
    for s in (1, -1):
        _rect(c, _M1_SIZE, (period / 2, s * _M1_Y), LAYER.M1)
        for row in _CA_ROWS:
            for i in range(_CA_NCOL):
                _rect(
                    c,
                    (_CA_SIZE, _CA_SIZE),
                    (_CA_X0 + i * _CA_PITCH, s * row),
                    LAYER.VIAC,
                )
    return c


@gf.cell(tags=["electrical", "modulator", "waveguides"])
def straight_pn_ribbed(
    length: float = 2000.0,
    width: float = 5.4,
    neck_width: float = 3.2,
    period: float = 10.0,
    tooth_length: float = 9.0,
) -> gf.Component:
    """Ribbed (corrugated) lateral PN-junction phase shifter.

    A continuous ``neck_width`` WG core with a ``tooth_length`` x ``width`` tooth
    centred in each ``period``, two SHALLOW_ETCH rails, a lateral PN junction
    (P/PP/PPP below the core, N/NP/NPP above) and a per-period VIAC + M1 electrode
    on each side. Continuous M1 buses join the per-period pads into the
    ``anode`` (P side) and ``cathode`` (N side) electrodes. Propagates along +x,
    centred on y = 0.

    Args:
        length: total length in um; snapped down to a whole number of periods.
        width: full WG core width at a tooth in um.
        neck_width: narrowed WG core width between teeth in um.
        period: corrugation / electrode period in um.
        tooth_length: length of the full-width tooth within each period in um.
    """
    c = gf.Component()
    n = int(length / period)
    span = n * period

    _rect(c, (span, neck_width), (span / 2, 0.0), LAYER.WG)
    for layer, y, w, inset in _STRIPS:
        _rect(c, (span - 2 * inset, w), (span / 2, y), layer)

    c.add_ref(
        _unit_cell(period=period, width=width, tooth_length=tooth_length),
        columns=n,
        rows=1,
        column_pitch=period,
    )

    # The per-period M1 pads are disjoint; a continuous bus per side joins them.
    for name, s in (("anode", -1), ("cathode", 1)):
        _rect(c, (span, _M1_SIZE[1]), (span / 2, s * _M1_Y), LAYER.M1)
        c.add_port(
            name,
            center=(0.0, s * _M1_Y),
            width=_M1_SIZE[1],
            orientation=180,
            layer=LAYER.M1,
            port_type="electrical",
        )

    c.add_port("o1", center=(0.0, 0.0), width=width, orientation=180, layer=LAYER.WG)
    c.add_port("o2", center=(span, 0.0), width=width, orientation=0, layer=LAYER.WG)

    c.info["length"] = span
    c.info["period"] = period
    c.info["n_periods"] = n
    c.info["junction_offset"] = _JUNCTION_Y
    return c
