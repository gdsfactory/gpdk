"""LVS: Electrical short detection.

Demonstrates a short where two routes on the metal layer overlap,
shorting two independent nets. Elvis flags it as LVS.short.
"""

import gdsfactory as gf


def schematic():
    """Four pads with two crossing electrical routes."""
    return {
        "elec": {
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
    }


@gf.cell(tags=["lvs"])
def sample_lvs_electrical_short() -> gf.Component:
    """Four pads with overlapping electrical routes (LVS.short error).

    Two routes on the metal layer overlap, shorting independent nets.
    """
    s = schematic()
    return gf.read.from_yaml(s["elec"])
