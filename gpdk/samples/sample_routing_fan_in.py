"""Fan-in strategies for converging N ports onto a bundle line.

``add_fan_in`` takes a set of N ports and produces N parallel
waveguides that converge into a tightly-pitched bundle line.
"""

import doroutes as dr
import gdsfactory as gf


@gf.cell(tags=["routing"])
def sample_routing_fan_in_manhattan() -> gf.Component:
    """Manhattan (90-degree comb) fan-in on a 5-port frame.

    Each port goes straight then turns 90 degrees onto the bundle line.
    """
    c = gf.Component()
    ref = c << dr.pcells.fanout_frame(orientation="e")
    c.add_ports(ref)
    dr.add_fan_in(
        component=c,
        inputs=c.ports,
        straight="straight",
        bend={"component": "bend_euler", "settings": {"radius": 5}},
    )
    return c


@gf.cell(tags=["routing"], check_instances=False)
def sample_routing_fan_in_sbend() -> gf.Component:
    """S-bend fan-in on a tight-pitch (7 um) frame.

    Each port is routed via two euler bends connected by an angled
    straight. Best when port pitch < 2*radius.
    """
    c = gf.Component()
    ref = c << dr.pcells.fanout_frame(
        orientation="e",
        num_inputs=5,
        input_spacing=7,
        width=30,
    )
    c.add_ports(ref)
    dr.add_fan_in(
        component=c,
        inputs=c.ports,
        straight="straight",
        bend={"component": "bend_euler", "settings": {"radius": 5}},
        strategy="sbend",
    )
    return c


@gf.cell(tags=["routing"])
def sample_routing_fan_in_lbend() -> gf.Component:
    """L-bend fan-in on a 5-port frame.

    Each port emits straight, 90-degree bend, straight. The bundle
    direction ends up perpendicular to the input direction.
    """
    c = gf.Component()
    ref = c << dr.pcells.fanout_frame(orientation="e")
    c.add_ports(ref)
    dr.add_fan_in(
        component=c,
        inputs=c.ports,
        straight="straight",
        bend={"component": "bend_euler", "settings": {"radius": 5}},
        strategy="lbend",
    )
    return c
