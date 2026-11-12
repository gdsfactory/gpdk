"""Building circuits from YAML netlists with doroutes routing strategies.

Registers doroutes' ``add_bundle_astar`` as a named routing strategy on
the PDK, then uses it declaratively in YAML netlists via
``routing_strategy: doroute_astar``.
"""

import gdsfactory as gf
from doroutes import add_bundle_astar

from gpdk import PDK

PDK.routing_strategies["doroute_astar"] = add_bundle_astar


@gf.cell(tags=["routing"])
def sample_routing_circuit_from_netlist_mmi() -> gf.Component:
    """Two MMI splitters linked by a single-wire A* bundle.

    A one-wire bundle confirms the strategy is registered and the YAML
    wiring works before scaling up to a real bundle.
    """
    yaml = """
instances:
  mmi1:
    component: mmi1x2
    settings: {}
  mmi2:
    component: mmi1x2
    settings: {}
connections: {}
routes:
  bundle:
    links:
      mmi1,o3: mmi2,o1
    routing_strategy: doroute_astar
    settings:
        spacing: 1.0
        bend:
            component: bend_euler
            settings:
                radius: 5
        straight: straight
        layers:
            - WG
nets: []
ports:
  o1: mmi1,o1
  o2: mmi2,o2
  o3: mmi2,o3
placements:
  mmi1:
    mirror: 0
    rotation: 0
    x: 0
    y: 0
  mmi2:
    dx: 100
    dy: 100
    mirror: 0
    rotation: 0
    x: mmi1,o2
    y: 0
"""
    return gf.read.from_yaml(yaml)


@gf.cell(tags=["routing"])
def sample_routing_circuit_from_netlist_crossing() -> gf.Component:
    """Two-wire A* bundle across a crossing of four straights.

    The bundle has to cross the layout from right to left while
    obstacle straights sit in the middle.
    """
    yaml = """
instances:
  s1:
    component: straight
    settings: {}
  s2:
    component: straight
    settings: {}
  s3:
    component: straight
    settings: {}
  s4:
    component: straight
    settings: {}
connections: {}
routes:
  my_bundle:
    links:
      s3-4,o1: s1-2,o2
    routing_strategy: 'doroute_astar'
    settings:
        spacing: 1.0
        bend:
            component: bend_euler
            settings:
                radius: 5
        straight: straight
        layers:
            - WG
nets: []
ports: {}
placements:
  s1:
    y: 100
  s2:
    y: -100
  s3:
    x: 200
    y: 100
  s4:
    x: 200
    y: -100
"""
    return gf.read.from_yaml(yaml)
