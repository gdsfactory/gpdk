"""You can define a path as list of points.

To create a component you need to extrude the path with a cross-section.
"""

from functools import partial
from typing import Any, Protocol

import gdsfactory as gf
from doroutes.bundles import add_bundle_astar
from gdsfactory.routing.factories import support_nets

from gpdk.cells.bends import bend_s as _bend_s
from gpdk.routing_3d import route_bundle_3d
from gpdk.tech import routing_strategies as _base_strategies

route_single = partial(gf.routing.route_single, cross_section="strip")
route_bundle = partial(gf.routing.route_bundle, cross_section="strip")


class _RoutingStrategy(Protocol):
    def __call__(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> Any: ...


route_bundle_nitride = partial(route_bundle, cross_section="nitride")
route_bundle_rib = partial(route_bundle, cross_section="rib")
route_bundle_metal1 = partial(route_bundle, cross_section="metal1")
route_bundle_metal2 = partial(route_bundle, cross_section="metal2")
route_bundle_metal3 = partial(route_bundle, cross_section="metal3")

route_bundle_electrical = partial(
    gf.routing.route_bundle,
    bend="wire_corner",
    allow_width_mismatch=True,
    cross_section="metal_routing",
)

route_bundle_all_angle = partial(
    gf.routing.route_bundle_all_angle,
    cross_section="strip",
    separation=3,
    bend="bend_euler_all_angle",
    straight="straight_all_angle",
)

route_bundle_sbend = partial(
    gf.routing.route_bundle_sbend,
    cross_section="strip",
    bend_s=_bend_s,
)

route_bundle_sbend_nitride = partial(
    gf.routing.route_bundle_sbend,
    cross_section="nitride",
    bend_s=_bend_s,
)

route_bundle_sbend_metal3 = partial(
    gf.routing.route_bundle_sbend,
    cross_section="metal3",
    bend_s=_bend_s,
    port_name="e1",
)

route_astar = partial(
    add_bundle_astar,
    layers=["WG"],
    bend="bend_euler",
    straight="straight",
    grid_unit=500,
    spacing=3,
)

route_astar_metal3 = partial(
    add_bundle_astar,
    layers=["M3"],
    bend="wire_corner",
    straight="wire_straight",
    grid_unit=500,
    spacing=15,
)


def route_bundle_playdough(
    component: gf.Component,
    ports1: list[gf.Port],
    ports2: list[gf.Port],
    **kwargs: Any,
) -> list:
    """Routing strategy adapter for playdough.

    Matches the ``(component, ports1, ports2, **settings)`` contract
    that gdsfactory's YAML ``routing_strategy`` expects, and forwards
    to ``pld.add_route_bundle``.

    Finetune-specific keys (``lr``, ``max_steps``, ``non_manhattan``,
    etc.) are extracted from ``kwargs`` and passed to ``router.finetune()``.
    If none are present, only manhattan initialization runs.
    """
    import jax
    import playdough as pld

    jax.config.update("jax_enable_x64", False)
    pld.config.BACKEND = "hlo"

    finetune_keys = {
        "lr",
        "max_steps",
        "non_manhattan",
        "length_matching",
        "min_radius_violation",
        "route_collision",
        "obstacle_collision",
        "bending",
        "lengthening",
        "radius_mismatch",
        "port_straightening",
    }
    finetune_kwargs = {k: kwargs.pop(k) for k in finetune_keys & set(kwargs)}
    length_matching_groups = kwargs.pop("length_matching_groups", None)

    router = pld.add_route_bundle(
        component,
        start_ports=ports1,
        end_ports=ports2,
        **kwargs,
    )

    if length_matching_groups:
        router.length_matching_groups = length_matching_groups

    if finetune_kwargs:
        router.finetune(**finetune_kwargs, manhattan_constrained=False)
        router.build_gds()

    return []


_ported_strategies: dict[str, _RoutingStrategy] = {
    "route_bundle": route_bundle,
    "route_bundle_electrical": route_bundle_electrical,
    "route_bundle_nitride": route_bundle_nitride,
    "route_bundle_metal1": route_bundle_metal1,
    "route_bundle_metal2": route_bundle_metal2,
    "route_bundle_metal3": route_bundle_metal3,
    "route_bundle_sbend": route_bundle_sbend,
    "route_bundle_sbend_nitride": route_bundle_sbend_nitride,
    "route_bundle_sbend_metal3": route_bundle_sbend_metal3,
    "route_astar": route_astar,
    "route_astar_metal3": route_astar_metal3,
    "route_bundle_3d": route_bundle_3d,
    "route_bundle_playdough": route_bundle_playdough,
}

# Retain the existing PDK surface and accept both YAML port lists and editor nets.
routing_strategies = {
    **_base_strategies,
    **{name: support_nets(router) for name, router in _ported_strategies.items()},
}
