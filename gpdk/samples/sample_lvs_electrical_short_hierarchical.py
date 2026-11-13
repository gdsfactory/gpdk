"""LVS: Hierarchical electrical short detection.

Demonstrates shorts detected through hierarchy: two instances of a
sub-cell (elec) are placed so their internal wires overlap, plus
each sub-cell already has an internal short. Elvis detects shorts
at both hierarchy levels.
"""

import gdsfactory as gf

from gpdk import PDK

_ELEC_YAML = {
    "instances": {
        "pad1": {"component": "pad", "settings": {}},
        "pad2": {"component": "pad", "settings": {}},
        "pad3": {"component": "pad", "settings": {}},
        "pad4": {"component": "pad", "settings": {}},
    },
    "connections": {},
    "routes": {
        "electrical": {
            "links": {"pad1,e3": "pad2,e1"},
            "routing_strategy": "route_bundle_electrical",
            "settings": {
                "allow_layer_mismatch": False,
                "allow_type_mismatch": False,
                "allow_width_mismatch": False,
            },
        },
        "electrical2": {
            "links": {"pad3,e3": "pad4,e3"},
            "routing_strategy": "route_bundle_electrical",
            "settings": {
                "allow_layer_mismatch": False,
                "allow_type_mismatch": False,
                "allow_width_mismatch": False,
                "radius": 10,
            },
        },
    },
    "nets": [],
    "ports": {},
    "placements": {
        "pad1": {"x": 0, "y": 0, "dx": -98.125, "dy": -19.273},
        "pad2": {"x": 0, "y": 0, "dx": 349.71, "dy": -394.94},
        "pad3": {
            "x": -98.125,
            "y": -19.273,
            "dx": -97.005,
            "dy": -423.277,
        },
        "pad4": {"x": 0, "y": 0, "dx": 137.75, "dy": -124.39},
    },
}

_TWO_ELEC_YAML = {
    "instances": {
        "instance1": {"component": "elec", "settings": {}},
        "instance2": {"component": "elec", "settings": {}},
    },
    "connections": {},
    "routes": {},
    "nets": [],
    "ports": {},
    "placements": {
        "instance1": {
            "x": 0,
            "y": 0,
            "dx": 491.989,
            "dy": -104.859,
            "rotation": 90,
        },
        "instance2": {
            "x": 100,
            "y": 0,
            "dx": 267.46,
            "dy": 53.93,
        },
    },
}

# Register the child cell at import time so it's available before
# all_cells iterates over PDK.cells.
if "elec" not in PDK.cells:
    _elec = gf.read.from_yaml(_ELEC_YAML, name="elec")
    PDK.cells["elec"] = lambda: _elec


@gf.cell(tags=["lvs"])
def sample_lvs_electrical_short_hierarchical() -> gf.Component:
    """Two overlapping sub-cells with internal shorts (hierarchical LVS).

    Three geometric shorts transitively tie six pad ports onto a single
    electrical net that the schematic doesn't declare.
    """
    return gf.read.from_yaml(_TWO_ELEC_YAML, name="two_elec")
