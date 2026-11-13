"""Side-by-side comparison of bundle routing methods.

All methods are demonstrated on a shared topology: 5 metal pads on
top at 200 um pitch, 5 on bottom at 150 um pitch. Covers gdsfactory
route_bundle and add_bundle_astar with manhattan fan-in.
"""

from functools import partial

import doroutes as dr
import gdsfactory as gf

from gpdk import PDK

NUM_PORTS = 5
SRC_PITCH = 200
DST_PITCH = 150
VSEP = 1000
SPACING = 20

BEND_SPEC = partial(PDK.get_component, "wire_corner", cross_section="metal_routing")
STRAIGHT_SPEC = partial(PDK.get_component, "straight", cross_section="metal_routing")
LAYERS_TO_AVOID = [(49, 0)]
GRID_UNIT = 2500


@gf.cell(tags=["routing"])
def sample_routing_bundle_comparison_gf() -> gf.Component:
    """Baseline: gdsfactory's built-in route_bundle."""
    c = gf.Component()
    pad = PDK.get_component("pad")
    top = c.add_ref(
        pad, name="top", columns=NUM_PORTS, rows=1, column_pitch=SRC_PITCH, row_pitch=0
    )
    top.dmove((0, VSEP))
    bot = c.add_ref(
        pad, name="bot", columns=NUM_PORTS, rows=1, column_pitch=DST_PITCH, row_pitch=0
    )
    p1 = [top.ports["e4", i, 0] for i in range(NUM_PORTS)]
    p2 = [bot.ports["e2", i, 0] for i in range(NUM_PORTS)]

    xs = gf.get_cross_section("metal_routing")
    gf.routing.route_bundle(
        c,
        ports1=p1,
        ports2=p2,
        cross_section=xs,
        bend="wire_corner",
        sort_ports=True,
    )
    return c


@gf.cell(tags=["routing"])
def sample_routing_bundle_comparison_manhattan() -> gf.Component:
    """A* bundle with default manhattan fan-in (5 ports)."""
    c = gf.Component()
    pad = PDK.get_component("pad")
    top = c.add_ref(
        pad, name="top", columns=NUM_PORTS, rows=1, column_pitch=SRC_PITCH, row_pitch=0
    )
    top.dmove((0, VSEP))
    bot = c.add_ref(
        pad, name="bot", columns=NUM_PORTS, rows=1, column_pitch=DST_PITCH, row_pitch=0
    )
    p1 = [top.ports["e4", i, 0] for i in range(NUM_PORTS)]
    p2 = [bot.ports["e2", i, 0] for i in range(NUM_PORTS)]

    dr.add_bundle_astar(
        component=c,
        ports1=p1,
        ports2=p2,
        spacing=SPACING,
        straight=STRAIGHT_SPEC,
        bend=BEND_SPEC,
        layers=LAYERS_TO_AVOID,
        grid_unit=GRID_UNIT,
    )
    return c
