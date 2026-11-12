"""LVS: Same net (star topology, passing case).

Demonstrates that Elvis correctly handles multi-branch nets: three
pads all on the same net, connected via two routes through a central
hub pad. Branching nets are valid topology, not shorts.
"""

import gdsfactory as gf


def schematic():
    """Three pads in a star topology — pad2 connects to both pad1 and pad3."""
    return {
        "same_net": {
            "instances": {
                "pad1": {"component": "pad", "settings": {}},
                "pad2": {"component": "pad", "settings": {}},
                "pad3": {"component": "pad", "settings": {}},
            },
            "connections": {},
            "routes": {
                "bundle1": {
                    "links": {"pad2,e4": "pad1,e2"},
                    "routing_strategy": "route_bundle_electrical",
                    "settings": {
                        "allow_layer_mismatch": False,
                        "allow_type_mismatch": False,
                        "allow_width_mismatch": False,
                    },
                },
                "bundle2": {
                    "links": {"pad2,e4": "pad3,e2"},
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
                "pad1": {"x": 0, "y": 0, "dx": -281.78, "dy": -140},
                "pad2": {"x": 0, "y": 0, "dx": 28.02, "dy": 128.78},
                "pad3": {"x": 0, "y": 0, "dx": 268.59, "dy": -145.57},
            },
        }
    }


@gf.cell(tags=["lvs"])
def sample_lvs_same_net() -> gf.Component:
    """Star topology: three pads on the same net (LVS passes).

    pad2 connects to both pad1 and pad3. Elvis recognizes this as
    valid multi-connection, not a short.
    """
    s = schematic()
    return gf.read.from_yaml(s["same_net"])
