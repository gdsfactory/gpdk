"""Bundle routing through explicit corners or relative steps.

``add_bundle_from_corners`` performs a fan-in at each end so the N
wires converge onto a single bundle line, then routes that bundle
through user-specified corners or steps.
"""

import doroutes as dr
import gdsfactory as gf


@gf.cell(tags=["routing"])
def sample_routing_bundle_from_corners() -> gf.Component:
    """5-port bundle through explicit absolute corner points.

    Routes through a Z-shape detour via four corners, going south
    at x=50, east at y=30, north at x=80 back to the output bundle line.
    """
    c = gf.Component()
    ref = c << dr.pcells.fanout_frame2(transition="ew", add_frame=True)
    c.add_ports(ref)

    dr.add_bundle_from_corners(
        component=c,
        ports1=[p for p in c.ports if str(p.name).startswith("in")],
        ports2=[p for p in c.ports if str(p.name).startswith("out")],
        corners=[
            (50, 100),
            (50, 30),
            (80, 30),
            (80, 75),
        ],
        spacing=1.0,
        bend={"component": "bend_euler", "settings": {"radius": 5}},
        straight="straight",
    )
    return c


@gf.cell(tags=["routing"])
def sample_routing_bundle_from_steps() -> gf.Component:
    """5-port bundle through relative coordinate steps.

    Same Z-shape detour expressed as relative moves from the bundle
    exit.
    """
    c = gf.Component()
    ref = c << dr.pcells.fanout_frame2(transition="ew", add_frame=True)
    c.add_ports(ref)

    dr.add_bundle_from_steps(
        component=c,
        ports1=[p for p in c.ports if str(p.name).startswith("in")],
        ports2=[p for p in c.ports if str(p.name).startswith("out")],
        steps=[
            {"dy": -70},
            {"dx": 37},
            {"dy": 45},
        ],
        spacing=1.0,
        bend={"component": "bend_euler", "settings": {"radius": 5}},
        straight="straight",
    )
    return c
