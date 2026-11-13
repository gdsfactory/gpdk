"""LVS: Cross-layer short through a VIA.

Demonstrates a short where a VIA bridges an M1 route and an M2 route
at their crossing, creating a cross-layer short between independent
nets. Elvis flags it as LVS.short.
"""

import gdsfactory as gf


def schematic():
    """Four pads on M1/M2 with crossing routes and a VIA at the intersection."""
    return {
        "via_short": {
            "instances": {
                "pad_m1_a": {"component": "pad", "settings": {"layer": "M1"}},
                "pad_m1_b": {"component": "pad", "settings": {"layer": "M1"}},
                "pad_m2_a": {"component": "pad", "settings": {"layer": "M2"}},
                "pad_m2_b": {"component": "pad", "settings": {"layer": "M2"}},
                "via": {
                    "component": "via",
                    "settings": {"size": [5, 5], "layer": "VIA1"},
                },
            },
            "connections": {},
            "routes": {
                "route_m1": {
                    "links": {"pad_m1_a,e3": "pad_m1_b,e1"},
                    "routing_strategy": "route_bundle_electrical",
                    "settings": {
                        "allow_layer_mismatch": False,
                        "allow_type_mismatch": False,
                        "allow_width_mismatch": False,
                        "cross_section": "metal1",
                    },
                },
                "route_m2": {
                    "links": {"pad_m2_a,e4": "pad_m2_b,e2"},
                    "routing_strategy": "route_bundle_electrical",
                    "settings": {
                        "allow_layer_mismatch": False,
                        "allow_type_mismatch": False,
                        "allow_width_mismatch": False,
                        "cross_section": "metal2",
                    },
                },
            },
            "nets": [],
            "ports": {},
            "placements": {
                "pad_m1_a": {"x": 0, "y": 0},
                "pad_m1_b": {"x": 800, "y": 0},
                "pad_m2_a": {"x": 400, "y": 400},
                "pad_m2_b": {"x": 400, "y": -400},
                "via": {"x": 400, "y": 0.0},
            },
        }
    }


@gf.cell(tags=["lvs"])
def sample_lvs_via_short() -> gf.Component:
    """M1/M2 routes crossing through a VIA (LVS.short cross-layer error).

    A VIA bridges two routes on different metal layers, creating a
    cross-layer short.
    """
    s = schematic()
    return gf.read.from_yaml(s["via_short"])
