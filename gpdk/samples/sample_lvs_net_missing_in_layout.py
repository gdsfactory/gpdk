"""LVS: Net missing in layout.

Demonstrates an error where the schematic declares a connection
(via nets:) but no physical metal trace exists in the GDS. Elvis
flags it as LVS.net.missing_in_layout.
"""

import gdsfactory as gf


def schematic():
    """Two pads with a declared net but no route geometry."""
    return {
        "metal_polys_scm": {
            "instances": {
                "pad1": {"component": "pad", "settings": {}},
                "pad2": {"component": "pad", "settings": {}},
            },
            "connections": {},
            "routes": {},
            "nets": [{"p1": "pad1,e3", "p2": "pad2,e1"}],
            "ports": {},
            "placements": {
                "pad1": {"x": 0.0, "y": 0.0},
                "pad2": {"x": 1000, "y": 0.0},
            },
        }
    }


@gf.cell(tags=["lvs"])
def sample_lvs_net_missing_in_layout() -> gf.Component:
    """Two pads with a declared net but no routing (LVS.net.missing_in_layout).

    The schematic declares pad1,e3 <-> pad2,e1 but no metal trace
    exists.
    """
    s = schematic()
    return gf.read.from_yaml(s["metal_polys_scm"])
