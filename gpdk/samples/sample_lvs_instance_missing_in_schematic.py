"""LVS: Instance missing in schematic.

Demonstrates an error where an extra instance (fake_coupler) appears
in the layout but is not declared in the reference schematic. Elvis
flags it as LVS.instance.missing_in_schematic.
"""

import gdsfactory as gf


def schematic():
    """Schematic with an extra fake_coupler instance (used to build GDS)."""
    return {
        "simple_splitter_instance_error": {
            "instances": {
                "fake_coupler": {"component": "coupler", "settings": {}},
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
                "o1": "wg_in,o1",
                "o2": "wg_out1,o2",
                "o3": "wg_out2,o2",
            },
            "placements": {
                "fake_coupler": {"x": 50, "y": 0},
                "mmi": {"x": 0, "y": 0},
                "wg_in": {"x": -20, "y": 0},
                "wg_out1": {"x": 15.5, "y": 0.625},
                "wg_out2": {"x": 15.5, "y": -0.625},
            },
        }
    }


@gf.cell(tags=["lvs"])
def sample_lvs_instance_missing_in_schematic() -> gf.Component:
    """Layout with an extra coupler not in the reference schematic.

    The GDS has a fake_coupler that the clean reference schematic
    does not declare.
    """
    s = schematic()
    return gf.read.from_yaml(s["simple_splitter_instance_error"])
