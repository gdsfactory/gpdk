"""LVS: Array instances with crossed routes.

Demonstrates shorts and opens in pad arrays: two routes connecting
pad arrays cross each other, causing geometric shorts, missing-net
groups, and dangling ports on unrouted pads.
"""

import gdsfactory as gf


def schematic():
    """Two rows of 5 pads with crossing routes."""
    return {
        "simple_array": {
            "instances": {
                "pads": {
                    "component": "pad",
                    "settings": {},
                    "array": {
                        "columns": 5,
                        "rows": 1,
                        "column_pitch": 200.0,
                        "row_pitch": 100.0,
                    },
                },
                "pads2": {
                    "component": "pad",
                    "settings": {},
                    "array": {
                        "columns": 5,
                        "rows": 1,
                        "column_pitch": 200.0,
                        "row_pitch": 100.0,
                    },
                },
            },
            "connections": {},
            "routes": {
                "elec1": {
                    "links": {"pads<1.0>,e4": "pads2<3.0>,e2"},
                    "routing_strategy": "route_bundle_electrical",
                    "settings": {
                        "allow_layer_mismatch": False,
                        "allow_type_mismatch": False,
                        "allow_width_mismatch": False,
                    },
                },
                "elec2": {
                    "links": {"pads<3.0>,e4": "pads2<0.0>,e2"},
                    "routing_strategy": "route_bundle_electrical",
                    "settings": {
                        "allow_layer_mismatch": False,
                        "allow_type_mismatch": False,
                        "allow_width_mismatch": False,
                    },
                },
            },
            "nets": [],
            "ports": {},
            "placements": {
                "pads": {"x": 0, "y": 0, "dx": -96.428, "dy": -26.49},
                "pads2": {
                    "x": -96.428,
                    "y": -26.49,
                    "dx": 0.0,
                    "dy": -515.322,
                },
            },
        }
    }


@gf.cell(tags=["lvs"])
def sample_lvs_array_instances() -> gf.Component:
    """Pad arrays with crossing routes (LVS.short + LVS.open errors).

    Two routes cross between pad arrays, causing shorts, a net group
    error, and open ports on unrouted pads.
    """
    s = schematic()
    return gf.read.from_yaml(s["simple_array"])
