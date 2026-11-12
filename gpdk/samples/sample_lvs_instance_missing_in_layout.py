"""LVS: Instance missing in layout.

Demonstrates an error where the schematic declares an instance
(fake_coupler) but the layout doesn't contain it. Elvis flags it
as LVS.instance.missing_in_layout.
"""

import gdsfactory as gf


def schematic():
    """Clean splitter schematic without fake_coupler (used to build GDS)."""
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
def sample_lvs_instance_missing_in_layout() -> gf.Component:
    """Layout missing an instance declared in the reference schematic.

    The GDS is built from a clean schematic without fake_coupler,
    while the reference schematic declares it.
    """
    s = schematic()
    return gf.read.from_yaml(s["simple_splitter"])
