"""LVS: Wire crossing detection.

Demonstrates a short where two routes on different nets cross on the
metal layer. The crossing merges them into a single layout net that
doesn't match the schematic.
"""

import gdsfactory as gf


def schematic():
    """Pad array and rectangle with two crossing routes."""
    return {
        "wire_crossing_yaml": {
            "instances": {
                "mpd": {
                    "component": "rectangle",
                    "settings": {"size": [100, 20], "layer": "M3"},
                },
                "pad_array_inst": {
                    "component": "pad_array",
                    "settings": {"port_orientation": 90},
                },
            },
            "connections": {},
            "routes": {
                "route1": {
                    "links": {"pad_array_inst,e13": "mpd,e3"},
                    "routing_strategy": "route_bundle_electrical",
                    "settings": {},
                },
                "route2": {
                    "links": {"pad_array_inst,e15": "mpd,e1"},
                    "routing_strategy": "route_bundle_electrical",
                    "settings": {
                        "end_straight_length": 100,
                        "start_straight_length": 100,
                    },
                },
            },
            "nets": [],
            "ports": {},
            "placements": {
                "mpd": {"x": -500, "y": 500, "rotation": 90},
                "pad_array_inst": {},
            },
            "name": "wire_crossing_yaml",
        }
    }


@gf.cell(tags=["lvs"])
def sample_lvs_wire_crossing() -> gf.Component:
    """Two routes crossing on the metal layer (LVS.short + net errors).

    Routes from a pad array to a rectangle cross each other, merging
    separate nets in the layout.
    """
    s = schematic()
    return gf.read.from_yaml(s["wire_crossing_yaml"])
