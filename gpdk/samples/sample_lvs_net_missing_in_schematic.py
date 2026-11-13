"""LVS: Net missing in schematic.

Demonstrates an error where a connection exists in the layout (via a
hand-drawn polygon) but is not declared in the schematic. Elvis flags
it as LVS.net.missing_in_schematic.
"""

import gdsfactory as gf


@gf.cell(tags=["lvs"])
def sample_lvs_net_missing_in_schematic() -> gf.Component:
    """Two pads bridged by a rectangle not declared in the schematic.

    A rectangle instance ties the pads together through geometric
    overlap, but the schematic (from get_netlist) has no such net.
    """
    c = gf.Component()
    c.add_ref(gf.c.pad(), name="pad1")
    c.add_ref(gf.c.pad(), name="pad2").move((1000, 1))
    c.add_ref(gf.c.rectangle((1000, 10), layer="M3", port_type=None))
    return c
