"""Single-wire routing through explicit corner points.

``add_route_from_corners`` builds a route that passes through a list
of explicit corner points in absolute coordinates. Useful for keeping
a waveguide inside a routing channel or matching a specific floorplan.
"""

import doroutes as dr
import gdsfactory as gf


@gf.cell(tags=["routing"])
def sample_routing_corners() -> gf.Component:
    """Z-detour through four explicit corner points.

    Routes between two straights through four corners: east, north,
    west, then south to the destination.
    """
    c = gf.Component()

    wg_in = c << gf.c.straight(length=1, width=1)
    wg_in.dmove((2, 3))
    wg_out = c << gf.c.straight(length=1, width=1)
    wg_out.dmove((48, 48))

    start = wg_in.ports["o2"]
    stop = wg_out.ports["o1"]

    corners = [
        (44.0, start.dcenter[1]),
        (44.0, 35.0),
        (1.0, 35.0),
        (1.0, stop.dcenter[1]),
    ]

    dr.add_route_from_corners(
        component=c,
        start=start,
        stop=stop,
        corners=corners,
        straight="straight",
        bend={"component": "bend_euler", "settings": {"radius": 5}},
    )
    return c
