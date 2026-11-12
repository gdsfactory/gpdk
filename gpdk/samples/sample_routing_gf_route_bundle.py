"""Comparison of doroutes steps routing with gdsfactory route_bundle.

Routes the same frame layout using doroutes add_route_from_steps and
gdsfactory's built-in route_bundle for comparison.
"""

import doroutes as dr
import gdsfactory as gf


@gf.cell(tags=["routing"])
def sample_routing_gf_route_bundle_steps() -> gf.Component:
    """Route a frame using doroutes add_route_from_steps per port pair.

    Each port pair is routed individually with computed step offsets
    based on port positions and spacing.
    """
    c = gf.Component()
    ref = c << dr.pcells.routing_frame()
    c.add_ports(ref)

    spacing = 1.0
    radius = 5.0

    starts = sorted(
        [p for p in c.ports if str(p.name).startswith("in")],
        key=lambda p: p.dcenter[1],
    )
    stops_by_name = {str(p.name): p for p in c.ports if str(p.name).startswith("out")}

    num_links = len(starts)
    below = num_links - sum(
        1
        for p in starts
        if p.dcenter[1] > stops_by_name[str(p.name).replace("in", "out")].dcenter[1]
    )

    for i, start in enumerate(starts):
        stop = stops_by_name[str(start.name).replace("in", "out")]
        dr.add_route_from_steps(
            component=c,
            start=start,
            stop=stop,
            steps=[
                {"dx": radius + max((below - i - 1), (i - below)) * spacing},
                {"y": stop.dcenter[1]},
            ],
            straight="straight",
            bend={"component": "bend_euler", "settings": {"radius": 5}},
        )
    return c


@gf.cell(tags=["routing"])
def sample_routing_gf_route_bundle_builtin() -> gf.Component:
    """Route a frame using gdsfactory's built-in route_bundle."""
    c = gf.Component()
    ref = c << dr.pcells.routing_frame()
    c.add_ports(ref)
    starts = sorted(
        [p for p in c.ports if str(p.name).startswith("in")], key=lambda p: p.center
    )
    stops = sorted(
        [p for p in c.ports if str(p.name).startswith("out")], key=lambda p: p.center
    )

    xs = gf.get_cross_section("strip").copy()
    xs.__dict__["radius"] = 5
    gf.routing.route_bundle(
        c,
        starts,
        stops,
        cross_section=xs,
        straight="straight",
        bend={"component": "bend_euler", "settings": {"radius": 5}},
    )
    return c
