"""A* bundle routing for N parallel waveguides.

Routes N parallel waveguides as a single bundle between two port
arrays, with fan-in, A* search, and fan-out stages. Useful when
the exact path shape doesn't matter as long as it avoids obstacles.
"""

import doroutes as dr
import gdsfactory as gf

from gpdk.cells.mmis import mmi


@gf.cell(tags=["routing"])
def sample_routing_astar_bundle_inline() -> gf.Component:
    """In-line A* bundle route with obstacles.

    Input and output sides face along the same axis. Two MMIs are
    dropped into the routing channel as obstacles that A* must
    weave around while keeping the bundle intact.
    """
    c = gf.Component()
    ref = c << dr.pcells.fanout_frame2(transition="ew", add_frame=True)
    c.add_ports(ref)

    r = c << mmi()
    r.dmove((40, 120))
    r = c << mmi()
    r.drotate(90)
    r.dmove((60, 40))

    dr.add_bundle_astar(
        component=c,
        ports1=[p for p in c.ports if str(p.name).startswith("in")],
        ports2=[p for p in c.ports if str(p.name).startswith("out")],
        spacing=1.0,
        straight="straight",
        bend={"component": "bend_euler", "settings": {"radius": 5}},
        layers=["WG"],
    )
    return c


@gf.cell(tags=["routing"])
def sample_routing_astar_bundle_corner() -> gf.Component:
    """A* bundle route around a 90-degree corner.

    Input and output sides are rotated 90 degrees relative to each
    other, so the bundle has to make a corner turn. The bundle's
    effective radius scales with port count and spacing.
    """
    c = gf.Component()
    ref = c << dr.pcells.fanout_frame3(transition="ew")
    c.add_ports(ref)
    dr.add_bundle_astar(
        component=c,
        ports1=[p for p in c.ports if str(p.name).startswith("in")],
        ports2=[p for p in c.ports if str(p.name).startswith("out")],
        spacing=1.0,
        straight="straight",
        bend={"component": "bend_euler", "settings": {"radius": 5}},
        layers=["WG"],
    )
    return c
