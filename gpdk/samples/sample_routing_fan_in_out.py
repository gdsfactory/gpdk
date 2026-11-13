"""Fan-in and fan-out with A* bundle routing in between.

Demonstrates composing fan-in on both ends with a single A* route
for the bundle backbone, including obstacles in the routing channel.
"""

from functools import partial

import doroutes as dr
import gdsfactory as gf
import numpy as np

from gpdk.cells.mmis import mmi


@gf.cell(tags=["routing"])
def sample_routing_fan_in_out() -> gf.Component:
    """Fan-in/out with A* backbone routing around obstacles.

    Two fan-ins converge the input and output ports, then a single A*
    route connects the bundle backbones while avoiding obstacles on
    the WG layer.
    """
    c = gf.Component()
    ref = c << dr.pcells.fanout_frame2(transition=("e", "w"), add_frame=True)
    c.add_ports(ref)
    r = c << mmi()
    r.dmove((40, 120))
    r = c << mmi()
    r.drotate(90)
    r.dmove((60, 40))

    straight = "straight"
    bend = {"component": "bend_euler", "settings": {"radius": 5}}
    spacing = 1.0

    starts, _ = dr.add_fan_in(
        component=c,
        inputs=[p for p in c.ports if str(p.name).startswith("in")],
        straight=straight,
        bend=bend,
        spacing=spacing,
    )
    stops, _ = dr.add_fan_in(
        component=c,
        inputs=[p for p in c.ports if str(p.name).startswith("out")],
        straight=straight,
        bend=bend,
        spacing=spacing,
    )

    dr.add_route_astar(
        component=c,
        start=(*np.mean(starts, axis=0), "e"),
        stop=(*np.mean(stops, axis=0), "e"),
        straight=partial(dr.pcells.straights, straight, len(starts), spacing),
        bend=partial(dr.pcells.bends, bend, straight, len(starts), spacing),
        layers=[(3, 0)],
        grid_unit=800,
    )
    return c
