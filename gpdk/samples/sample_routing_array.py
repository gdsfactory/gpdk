"""Routing between arrayed instances (pad grids, probe arrays).

Shows how to wire arrayed instances using array-port indexing with
A* bundle routing and corners bundle routing.
"""

from functools import partial

import doroutes as dr
import gdsfactory as gf

from gpdk import PDK


def _pad_arrays() -> gf.Component:
    """Two rows of 3 pads, 200 um pitch, 500 um vertical separation."""
    c = gf.Component()
    pad = PDK.get_component("pad")

    top = c.add_ref(pad, name="top", columns=3, rows=1, column_pitch=200, row_pitch=0)
    top.dmove((0, 500))
    bot = c.add_ref(pad, name="bot", columns=3, rows=1, column_pitch=200, row_pitch=0)

    for i in range(3):
        c.add_port(f"e{i + 1}", port=top.ports["e4", i, 0])
        c.add_port(f"e{i + 4}", port=bot.ports["e2", i, 0])

    return c


@gf.cell(tags=["routing"])
def sample_routing_array_astar() -> gf.Component:
    """A* bundle route between two rows of 3 pads.

    Routes on the metal-routing cross-section using wire_corner bends.
    """
    c = _pad_arrays()
    ports1 = [p for p in c.ports if p.name in ["e1", "e2", "e3"]]
    ports2 = [p for p in c.ports if p.name in ["e4", "e5", "e6"]]

    dr.add_bundle_astar(
        component=c,
        ports1=ports1,
        ports2=ports2,
        spacing=20,
        bend=partial(PDK.get_component, "wire_corner", cross_section="metal_routing"),
        straight=partial(PDK.get_component, "straight", cross_section="metal_routing"),
        layers=[(49, 0)],
        grid_unit=2500,
    )
    return c


@gf.cell(tags=["routing"])
def sample_routing_array_corners() -> gf.Component:
    """Corners bundle route between two rows of 3 pads.

    Routes through four absolute corner points producing a Z-shaped
    detour around the centre of the layout.
    """
    c = _pad_arrays()
    ports1 = [p for p in c.ports if p.name in ["e1", "e2", "e3"]]
    ports2 = [p for p in c.ports if p.name in ["e4", "e5", "e6"]]

    dr.add_bundle_from_corners(
        component=c,
        ports1=ports1,
        ports2=ports2,
        corners=[
            (200, 350),
            (400, 350),
            (400, 150),
            (200, 150),
        ],
        spacing=20,
        bend=partial(gf.c.wire_corner),
        straight=partial(gf.c.straight, cross_section="metal_routing"),
    )
    return c
