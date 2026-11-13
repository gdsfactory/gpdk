"""A* single-wire routing that finds paths avoiding obstacles.

Uses a grid-based A* search to route a single waveguide from one port
to another while avoiding collision layers, with control over grid
resolution and clearance.
"""

import doroutes as dr
import gdsfactory as gf


@gf.cell(tags=["routing"])
def sample_routing_astar() -> gf.Component:
    """Single A* route between two straights with obstacles.

    Two input/output straights are placed with waveguide stubs as
    obstacles in between. A* finds a path on the WG layer that
    doesn't cross any of those obstacles.
    """
    c = gf.Component()

    wg_in = c << gf.c.straight(length=1, width=1)
    wg_in.dmove((2, 3))
    wg_out = c << gf.c.straight(length=1, width=1)
    wg_out.dmove((48, 48))

    # Add obstacle stubs
    obs1 = c << gf.c.straight(length=40, width=5)
    obs1.dmove((1, 29))
    obs2 = c << gf.c.straight(length=5, width=5)
    obs2.dmove((46, 30))
    obs3 = c << gf.c.straight(length=40, width=1)
    obs3.dmove((11, 40))

    dr.add_route_astar(
        c,
        wg_in.ports["o2"],
        wg_out.ports["o1"],
        straight="straight",
        bend={"component": "bend_euler", "settings": {"radius": 5}},
        layers=["WG"],
        grid_unit=500,
    )
    return c
