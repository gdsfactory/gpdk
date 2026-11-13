"""Effect of grid resolution on A* routing paths.

The A* router projects everything onto a uniform grid. ``grid_unit``
(in dbu) controls the grid pitch: coarser grids are faster but
produce boxier paths; finer grids hug obstacles closely.
"""

import doroutes as dr
import gdsfactory as gf


@gf.cell(tags=["routing"])
def sample_routing_discretization_coarse() -> gf.Component:
    """A* route at a coarse grid (grid_unit=2500 dbu = 2.5 um).

    Exactly half the 5 um bend radius (the coarsest the router
    accepts). The path looks blocky with limited freedom per step.
    """
    c = gf.Component()

    wg_in = c << gf.c.straight(length=1, width=1)
    wg_in.dmove((2, 3))
    wg_out = c << gf.c.straight(length=1, width=1)
    wg_out.dmove((48, 48))

    obs1 = c << gf.c.straight(length=40, width=5)
    obs1.dmove((1, 29))

    dr.add_route_astar(
        component=c,
        start=wg_in.ports["o2"],
        stop=wg_out.ports["o1"],
        straight="straight",
        bend={"component": "bend_euler", "settings": {"radius": 5}},
        layers=["WG"],
        grid_unit=2500,
    )
    return c


@gf.cell(tags=["routing"])
def sample_routing_discretization_fine() -> gf.Component:
    """A* route at a fine grid (grid_unit=250 dbu = 0.25 um).

    A twentieth of the bend radius. The path hugs obstacles closely
    and takes a more compact route.
    """
    c = gf.Component()

    wg_in = c << gf.c.straight(length=1, width=1)
    wg_in.dmove((2, 3))
    wg_out = c << gf.c.straight(length=1, width=1)
    wg_out.dmove((48, 48))

    obs1 = c << gf.c.straight(length=40, width=5)
    obs1.dmove((1, 29))

    dr.add_route_astar(
        component=c,
        start=wg_in.ports["o2"],
        stop=wg_out.ports["o1"],
        straight="straight",
        bend={"component": "bend_euler", "settings": {"radius": 5}},
        layers=["WG"],
        grid_unit=250,
    )
    return c
