"""Technology definitions for the generic PDK."""

from functools import partial

import gdsfactory as gf
from gdsfactory.cross_section import cross_sections
from gdsfactory.routing.factories import support_nets
from gdsfactory.technology import LayerViews
from gdsfactory.typings import RoutingStrategy

from gpdk.config import PATH
from gpdk.layer_map import LAYER
from gpdk.layer_stack import LAYER_STACK

LAYER_VIEWS = LayerViews(filepath=PATH.lyp_yaml)

PORT_MARKER_LAYER_TO_TYPE = {
    LAYER.PORT: "optical",
    LAYER.PORTE: "dc",
    LAYER.TE: "vertical_te",
    LAYER.TM: "vertical_tm",
}

PORT_LAYER_TO_TYPE = {
    LAYER.WG: "optical",
    LAYER.WGN: "optical",
    LAYER.SLAB150: "optical",
    LAYER.M1: "dc",
    LAYER.M2: "dc",
    LAYER.M3: "dc",
    LAYER.TE: "vertical_te",
    LAYER.TM: "vertical_tm",
}

PORT_TYPE_TO_MARKER_LAYER = {v: k for k, v in PORT_MARKER_LAYER_TO_TYPE.items()}

LAYER_CONNECTIVITY = [
    ("NPP", "VIAC", "M1"),
    ("PPP", "VIAC", "M1"),
    ("M1", "VIA1", "M2"),
    ("M2", "VIA2", "M3"),
]


class GenericConstants(gf.Constants):
    """Generic PDK constants."""

    fiber_input_to_output_spacing: float = 200.0
    metal_spacing: float = 10.0
    pad_pitch: float = 100.0
    pad_size: tuple[float, float] = (80.0, 80.0)
    wavelength: float = 1.55


layer_transitions = {
    LAYER.WG: "taper",
    LAYER.WG_ABSTRACT: partial(gf.c.taper, cross_section="rib_with_trenches"),
    (LAYER.WG, LAYER.WGN): "taper_sc_nc",
    (LAYER.WGN, LAYER.WG): "taper_nc_sc",
    LAYER.M3: "taper_electrical",
}

route_bundle = partial(gf.routing.route_bundle, cross_section="strip")

routing_strategies: dict[str, RoutingStrategy] = {
    "route_bundle": support_nets(route_bundle),
    "route_bundle_all_angle": support_nets(
        partial(gf.routing.route_bundle_all_angle, cross_section="strip")
    ),
    "route_bundle_electrical": support_nets(
        partial(gf.routing.route_bundle, cross_section="metal_routing")
    ),
    "route_bundle_nitride": support_nets(
        partial(gf.routing.route_bundle, cross_section="nitride")
    ),
    "route_bundle_rib": support_nets(
        partial(gf.routing.route_bundle, cross_section="rib")
    ),
    "route_bundle_metal1": support_nets(
        partial(gf.routing.route_bundle, cross_section="metal1")
    ),
    "route_bundle_metal2": support_nets(
        partial(gf.routing.route_bundle, cross_section="metal2")
    ),
    "route_bundle_metal3": support_nets(
        partial(gf.routing.route_bundle, cross_section="metal3")
    ),
    "route_bundle_sbend": partial(gf.routing.route_bundle_sbend, cross_section="strip"),
    "route_bundle_sbend_nitride": partial(
        gf.routing.route_bundle_sbend, cross_section="nitride"
    ),
    "route_bundle_sbend_metal3": partial(
        gf.routing.route_bundle_sbend, cross_section="metal3", port_name="e1"
    ),
}

PDK = gf.Pdk(
    name="gpdk",
    layers=LAYER,
    layer_stack=LAYER_STACK,
    layer_views=LAYER_VIEWS,
    cross_sections=cross_sections,
    routing_strategies=routing_strategies,
    cells={},
)

__all__ = [
    "LAYER",
    "LAYER_CONNECTIVITY",
    "LAYER_STACK",
    "LAYER_VIEWS",
    "GenericConstants",
    "PDK",
    "cross_sections",
    "layer_transitions",
    "routing_strategies",
]
