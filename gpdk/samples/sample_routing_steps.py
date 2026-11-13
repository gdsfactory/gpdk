"""Single-wire routing through relative coordinate steps.

``add_route_from_steps`` is the relative-coordinate sibling of
``add_route_from_corners``. Each leg of the route is described as a
one-axis step. The same step recipe works at any placement, making it
natural for reusable routing patterns.
"""

import doroutes as dr
import gdsfactory as gf


@gf.cell(tags=["routing"])
def sample_routing_steps() -> gf.Component:
    """Z-detour described as relative and absolute steps.

    Mixes relative moves (dx, dy) and absolute anchors (x, y) to
    route between two straights.
    """
    c = gf.Component()

    wg_in = c << gf.c.straight(length=1, width=1)
    wg_in.dmove((2, 3))
    wg_out = c << gf.c.straight(length=1, width=1)
    wg_out.dmove((48, 48))

    start = wg_in.ports["o2"]
    stop = wg_out.ports["o1"]

    steps = [
        {"dx": 41.5},
        {"dy": 32.5},
        {"x": 2.0},
        {"y": stop.dcenter[1]},
    ]

    dr.add_route_from_steps(
        component=c,
        start=start,
        stop=stop,
        steps=steps,
        straight="straight",
        bend={"component": "bend_euler", "settings": {"radius": 5}},
    )
    return c
