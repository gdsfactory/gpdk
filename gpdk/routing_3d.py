"""3D (multi-layer) electrical bundle routing for the gpdk PDK.

Wraps ``doroutes.multilayer.route_batch_multilayer`` so it can be invoked as a
gdsfactory ``routing_strategy`` from schematic-driven layout YAMLs.
"""

from __future__ import annotations

import logging
import time
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any

import gdsfactory as gf
from doroutes.multilayer import (
    MetalLayerSpec,
    PortGeometry,
    RouteNetSpec,
    RoutingConfig,
    route_batch_multilayer,
)
from doroutes.multilayer.engine_multinet import _precompute_port_geometries

from gpdk.cells.vias import via_stack


# Older doroutes builds don't accept stats_sink on route_batch_multilayer.
# Feature-test once so route_bundle_3d stays compatible with both.
def _route_batch_supports_stats_sink() -> bool:
    import inspect

    try:
        sig = inspect.signature(route_batch_multilayer)
    except (TypeError, ValueError):
        return False
    return "stats_sink" in sig.parameters


_ROUTE_BATCH_STATS_SINK = _route_batch_supports_stats_sink()

__all__ = [
    "GPDK_CONFIG",
    "BundleRouter3D",
    "route_bundle_3d",
    "via_m2_m3",
    "active_stats_sink",
]

# Benchmark/profiling hook. When a caller sets this ContextVar (e.g. via
# ``active_stats_sink.set({})`` in a benchmark harness), ``route_bundle_3d``
# also writes stage timings into that dict — even when invoked indirectly
# through a ``@gf.cell``-wrapped component factory that can't forward the
# ``stats_sink`` kwarg without busting its cache key.
active_stats_sink: ContextVar[dict[str, Any] | None] = ContextVar(
    "active_stats_sink", default=None
)

logger = logging.getLogger(__name__)


@gf.cell
def via_m2_m3(width: float = 11.0, length: float = 11.0) -> gf.Component:
    """Via transition between M2 and M3 for 3D electrical routing."""
    return via_stack(size=(width, length), layers=("M2", "MTOP"), vias=("via2", None))


GPDK_CONFIG = RoutingConfig(
    metal_layers=(
        MetalLayerSpec(
            layer_tuple=(45, 0),  # M2
            preferred_direction="h",
            min_width=10.0,
            min_via_pad=11.0,
            below_cut_layer=None,
            pitch=20.0,
            spacing=5.0,
        ),
        MetalLayerSpec(
            layer_tuple=(49, 0),  # M3
            preferred_direction="v",
            min_width=10.0,
            min_via_pad=11.0,
            below_cut_layer=(43, 0),  # VIA2
            pitch=20.0,
            spacing=5.0,
        ),
    ),
    via_factory=via_m2_m3,
    # The factory's width/length specify the full metal landing; its via-cut
    # enclosure is already inside that footprint.
    via_metal_enclosure_add=0.0,
)


@dataclass(frozen=True)
class BundleRouter3D:
    """3D bundle routing with one routing configuration and router grid.

    ``route`` draws every net of a bundle through
    ``doroutes.multilayer.route_batch_multilayer``; each routed net becomes
    its own two-port child cell whose ``a``/``b`` ports abut the device ports.

    Attributes:
        config: RoutingConfig (metal layers, via factory, port access).
        grid_unit: Router grid resolution in microns.
        clearance: Clearance from obstacles in microns.
        layers_to_avoid: Layers treated as full obstacles.
        debug: Pass through to the router for verbose logging.
    """

    config: RoutingConfig = GPDK_CONFIG
    grid_unit: float = 10.0
    clearance: float = 5.0
    layers_to_avoid: tuple[tuple[int, int], ...] = ((45, 0), (49, 0))
    debug: bool = False

    @staticmethod
    def nets(
        ports1: list[gf.Port], ports2: list[gf.Port], net_prefix: str = "e"
    ) -> list[RouteNetSpec]:
        """Pair up the bundle's ports as ``RouteNetSpec``s named ``<prefix><i>``."""
        if len(ports1) != len(ports2):
            raise ValueError(
                f"ports1 ({len(ports1)}) and ports2 ({len(ports2)}) must have equal length"
            )
        return [
            RouteNetSpec(
                name=f"{net_prefix}{i}",
                start=p1,
                stop=p2,
                port_name_prefix=f"{net_prefix}{i}",
            )
            for i, (p1, p2) in enumerate(zip(ports1, ports2))
        ]

    @staticmethod
    def derive_width(
        geom_cache: dict[tuple[int, int], PortGeometry],
        nets: list[RouteNetSpec],
        dbu: float,
        fallback: float = 10.0,
    ) -> float:
        """Derive a bundle routing width from port geometry.

        Takes the per-net min longest-extent, then the min across nets.
        """
        per_net: list[float] = []
        for net in nets:
            longest_pair: list[float] = []
            for port in (net.start, net.stop):
                key = (int(port.dcenter[0] / dbu), int(port.dcenter[1] / dbu))
                geom = geom_cache.get(key)
                if geom:
                    longest_pair.append(
                        max(geom.orig_extent_x_um, geom.orig_extent_y_um)
                    )
            if len(longest_pair) == 2:
                per_net.append(min(longest_pair))
        return min(per_net) if per_net else fallback

    def port_geometries(
        self, component: gf.Component, nets: list[RouteNetSpec], width: float | None
    ) -> dict[tuple[int, int], PortGeometry]:
        """Metal geometry under every port of ``nets`` (keyed by port centre, dbu)."""
        return _precompute_port_geometries(
            component, nets, self.config, width=width or 1.0
        )

    def route(
        self,
        component: gf.Component,
        ports1: list[gf.Port],
        ports2: list[gf.Port],
        *,
        width: float | None = None,
        net_prefix: str = "e",
        require_all: bool = False,
        stats_sink: dict[str, Any] | None = None,
    ) -> list[str]:
        """Route the bundle onto ``component``; return the names of unrouted nets.

        Args:
            component: The Component to draw into.
            ports1: Start ports.
            ports2: Stop ports.
            width: Routing width. If None, derived from port geometry.
            net_prefix: Prefix used for generated RouteNetSpec names.
            require_all: If True, raise when a net cannot be routed.
            stats_sink: Optional dict populated with per-phase timings and counts
                (``active_stats_sink`` is written too when set).
        """
        nets = self.nets(ports1, ports2, net_prefix)
        if not nets:
            return []
        sinks = [s for s in (stats_sink, active_stats_sink.get()) if s is not None]

        def record(key: str, value: Any) -> None:
            for s in sinks:
                s[key] = value

        t_pre = time.perf_counter()
        geom_cache = self.port_geometries(component, nets, width)
        record("t_precompute_geom", time.perf_counter() - t_pre)
        effective_width = (
            width
            if width is not None
            else self.derive_width(geom_cache, nets, component.kcl.dbu)
        )

        rust_stats: dict[str, Any] = {}
        batch_kwargs: dict[str, Any] = dict(
            nets=nets,
            config=self.config,
            grid_unit=self.grid_unit,
            width=effective_width,
            dynamic_width=False,
            layers_to_avoid=list(self.layers_to_avoid),
            clearance=self.clearance,
            geom_cache=geom_cache,
            debug=self.debug,
        )
        if _ROUTE_BATCH_STATS_SINK:
            batch_kwargs["stats_sink"] = rust_stats
        t0 = time.perf_counter()
        _, failed, _ = route_batch_multilayer(component, **batch_kwargs)
        elapsed = time.perf_counter() - t0
        failed_names = list(failed)
        record("t_rust_batch", elapsed)
        for key in ("t_rust_grid_s", "t_rust_grt_s", "t_rust_drt_s", "t_rust_total_s"):
            if key in rust_stats:
                record(key, rust_stats[key])
        record("n_routed", len(nets) - len(failed_names))
        record("n_nets", len(nets))
        logger.info(
            "routed %d/%d nets in %.2fs",
            len(nets) - len(failed_names),
            len(nets),
            elapsed,
        )
        if failed_names and require_all:
            raise RuntimeError(f"3D routing failed for nets: {failed_names}")
        return failed_names


def route_bundle_3d(
    component: gf.Component,
    ports1: list[gf.Port],
    ports2: list[gf.Port],
    *,
    config: RoutingConfig | None = None,
    grid_unit: float = 10.0,
    width: float | None = None,
    clearance: float = 5.0,
    layers_to_avoid: tuple[tuple[int, int], ...] = ((45, 0), (49, 0)),
    net_prefix: str = "e",
    require_all: bool = False,
    debug: bool = False,
    stats_sink: dict[str, Any] | None = None,
    **_ignored: Any,  # gdsfactory's routing_strategy may pass extra kwargs (e.g. cross_section); accept and drop.
) -> list[Any]:
    """Route a bundle of electrical nets with 3D (multi-layer) routing.

    Signature matches gdsfactory's routing_strategy contract
    (component + ports1 + ports2) so it can be used directly from
    ``.pic.yml`` schematic files registered in ``PDK.routing_strategies``.
    See ``BundleRouter3D.route`` for the arguments.

    Returns:
        Empty list. The routing is drawn directly on ``component``; this
        matches the return shape of ``add_bundle_astar`` used by the
        existing ``route_astar`` strategy.
    """
    BundleRouter3D(
        config=config or GPDK_CONFIG,
        grid_unit=grid_unit,
        clearance=clearance,
        layers_to_avoid=layers_to_avoid,
        debug=debug,
    ).route(
        component,
        ports1,
        ports2,
        width=width,
        net_prefix=net_prefix,
        require_all=require_all,
        stats_sink=stats_sink,
    )
    return []
