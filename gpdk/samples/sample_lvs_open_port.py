"""LVS: Open port detection.

Demonstrates an open port error where a port is connected in the
layout but never promoted to a top-level schematic port. Elvis flags
it as LVS.open (dangling port).
"""

import gdsfactory as gf


def schematic():
    """Schematic with a missing port promotion (wg_in,o1 is dangling)."""
    return {
        "simple_splitter": {
            "instances": {
                "mmi": {"component": "mmi1x2", "settings": {}},
                "wg_in": {"component": "straight", "settings": {"length": 10}},
                "wg_out1": {"component": "straight", "settings": {"length": 10}},
                "wg_out2": {"component": "straight", "settings": {"length": 10}},
            },
            "connections": {
                "mmi,o2": "wg_out1,o1",
                "mmi,o3": "wg_out2,o1",
                "wg_in,o2": "mmi,o1",
            },
            "routes": {},
            "nets": [],
            "ports": {
                # "o1": "wg_in,o1",  # <-- missing! causes LVS.open
                "o2": "wg_out1,o2",
                "o3": "wg_out2,o2",
            },
            "placements": {
                "mmi": {"x": 0, "y": 0},
                "wg_in": {"x": -20, "y": 0},
                "wg_out1": {"x": 15.5, "y": 0.625},
                "wg_out2": {"x": 15.5, "y": -0.625},
            },
        }
    }


@gf.cell(tags=["lvs"])
def sample_lvs_open_port() -> gf.Component:
    """Splitter with a dangling input port (LVS.open error).

    wg_in,o1 is connected in the layout but not promoted to a
    top-level schematic port.
    """
    s = schematic()
    return gf.read.from_yaml(s["simple_splitter"])
