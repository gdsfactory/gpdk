"""Playdough obstacle-aware routing in the schematic-driven YAML flow.

``route_bundle_playdough`` adapts playdough's differentiable router to
the gdsfactory routing-strategy contract so it can be invoked from
``.pic.yml`` schematics.  The strategy extracts obstacle geometry from
the component's routing layer, so dragging an obstacle instance in the
schematic editor triggers a live re-route.

Two cells demonstrate the effect:

- ``sample_routing_playdough_obstacles``: manhattan-only (fast)
- ``sample_routing_playdough_obstacles_finetuned``: with gradient finetuning

A companion schematic ``playdough_obstacle_routing.pic.yml`` uses the
strategy declaratively — open it in the schematic editor, drag the
obstacle, and watch the routes update.
"""

from __future__ import annotations

from typing import Any

import gdsfactory as gf
import jax
import playdough as pld

import gpdk

_CONFIGURED = False


def _ensure_configured() -> None:
    global _CONFIGURED  # noqa: PLW0603
    if _CONFIGURED:
        return
    gpdk.PDK.activate()
    jax.config.update("jax_enable_x64", False)
    pld.config.BACKEND = "hlo"
    _CONFIGURED = True


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
    _ensure_configured()

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


@gf.cell(tags=["routing"])
def sample_routing_playdough_obstacles() -> gf.Component:
    """Manhattan-only playdough routing around a movable obstacle.

    Two MMI outputs are connected while avoiding a rectangle on the
    WG layer.  Move the obstacle in the schematic editor and watch
    the routes update.
    """
    _ensure_configured()

    c = gf.Component()

    mmi_in = c << gf.c.mmi1x2()
    mmi_out = c << gf.c.mmi1x2()
    mmi_out.dmove((120, 0))

    obs = c << gf.c.rectangle(size=(20, 15), layer="WG")
    obs.dmove((50, -5))

    route_bundle_playdough(
        c,
        ports1=[mmi_in.ports["o2"], mmi_in.ports["o3"]],
        ports2=[mmi_out.ports["o3"], mmi_out.ports["o2"]],
        cross_section="strip",
        collision_check_layers=["WG"],
        internal_pivots=4,
    )
    return c


@gf.cell(tags=["routing"])
def sample_routing_playdough_obstacles_finetuned() -> gf.Component:
    """Finetuned playdough routing around a movable obstacle.

    Same layout as the manhattan-only version, but with gradient-based
    optimization that smooths the routes and respects minimum bend
    radius constraints.
    """
    _ensure_configured()

    c = gf.Component()

    mmi_in = c << gf.c.mmi1x2()
    mmi_out = c << gf.c.mmi1x2()
    mmi_out.dmove((120, 0))

    obs = c << gf.c.rectangle(size=(20, 15), layer="WG")
    obs.dmove((50, -5))

    route_bundle_playdough(
        c,
        ports1=[mmi_in.ports["o2"], mmi_in.ports["o3"]],
        ports2=[mmi_out.ports["o3"], mmi_out.ports["o2"]],
        cross_section="strip",
        collision_check_layers=["WG"],
        internal_pivots=4,
        lr=0.3,
        max_steps=1000,
        non_manhattan=5,
    )
    return c
