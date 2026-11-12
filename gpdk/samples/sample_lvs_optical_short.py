"""LVS: Optical short detection.

Demonstrates a short where two waveguide arms of an MZI cross and
overlap on the silicon layer, creating a geometric short between
two independent signal paths. Elvis flags it as LVS.short.
"""

import gdsfactory as gf


def schematic():
    """MZI with crossing arms (top arm folds the wrong way)."""
    return {
        "mzi_arms": {
            "instances": {
                "combiner": {"component": "mmi2x2", "settings": {}},
                "splitter": {"component": "mmi1x2", "settings": {}},
            },
            "connections": {},
            "routes": {
                "bottom_arm": {
                    "links": {"splitter,o3": "combiner,o1"},
                    "routing_strategy": "route_bundle",
                    "settings": {
                        "radius": 10.0,
                        "steps": [{"dx": 20, "dy": -20}, {"dx": 1}],
                    },
                },
                "top_arm": {
                    "links": {"splitter,o2": "combiner,o2"},
                    "routing_strategy": "route_bundle",
                    "settings": {
                        "radius": 10.0,
                        "steps": [{"dx": 20, "dy": -40}, {"dx": 1}],
                    },
                },
            },
            "nets": [],
            "ports": {
                "o1": "splitter,o1",
                "o2": "combiner,o3",
                "o3": "combiner,o4",
            },
            "placements": {
                "combiner": {"x": 70, "y": 0},
                "splitter": {"x": 0, "y": 0},
            },
        }
    }


@gf.cell(tags=["lvs"])
def sample_lvs_optical_short() -> gf.Component:
    """MZI with crossing waveguide arms (LVS.short on silicon layer).

    The top arm steers 40 um downward while the bottom arm steers only
    20 um, causing them to cross and overlap.
    """
    s = schematic()
    return gf.read.from_yaml(s["mzi_arms"])
