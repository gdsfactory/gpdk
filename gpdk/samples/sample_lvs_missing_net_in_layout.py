"""LVS: Missing net in layout.

Demonstrates a net error where a connection is declared in the
schematic but the ports don't meet in the layout because an instance
is offset. Elvis flags it as LVS.net.missing_in_layout.
"""

import gdsfactory as gf


def schematic():
    """Schematic where wg_out2 is offset, breaking the mmi,o3 connection."""
    return {
        "simple_splitter_with_error": {
            "instances": {
                "mmi": {"component": "mmi1x2", "settings": {}},
                "wg_in": {"component": "straight", "settings": {"length": 10}},
                "wg_out1": {"component": "straight", "settings": {"length": 10}},
                "wg_out2": {"component": "straight", "settings": {"length": 10}},
            },
            "connections": {
                "mmi,o2": "wg_out1,o1",
                "wg_in,o2": "mmi,o1",
            },
            "routes": {},
            "nets": [{"p1": "mmi,o3", "p2": "wg_out2,o1"}],
            "ports": {
                "o1": "wg_in,o1",
                "o2": "wg_out1,o2",
                "o3": "wg_out2,o2",
            },
            "placements": {
                "mmi": {"x": 0, "y": 0},
                "wg_in": {"x": -20, "y": 0},
                "wg_out1": {"x": 15.5, "y": 0.625},
                "wg_out2": {
                    "x": 15.5,
                    "y": -0.625,
                    "dx": 2.247,
                    "dy": -10.826,  # <-- shifts wg_out2 ~11 um off
                },
            },
        }
    }


@gf.cell(tags=["lvs"])
def sample_lvs_missing_net_in_layout() -> gf.Component:
    """Splitter with an offset output (LVS.net.missing_in_layout error).

    wg_out2 is shifted ~11 um from its nominal position, breaking the
    connection to mmi,o3.
    """
    s = schematic()
    return gf.read.from_yaml(s["simple_splitter_with_error"])
