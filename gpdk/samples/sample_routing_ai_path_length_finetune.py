"""Length-matched routing with playdough finetuning.

Two 3-waveguide bundles are routed around obstacles, then
gradient-based finetuning matches path lengths across paired
routes (R0-R3, R1-R4, R2-R5) to sub-micron accuracy.
"""

import gdsfactory as gf
import jax
import playdough as pld

import gpdk

_SCALE = 2.0
_N_PORTS = 3
_PORT_INDICES = range(1, _N_PORTS + 1)
_MIDDLE_PORT = f"o1_{_N_PORTS // 2 + 1}_1"
_CONFIGURED = False


def _ensure_configured() -> None:
    global _CONFIGURED  # noqa: PLW0603
    if _CONFIGURED:
        return
    gpdk.PDK.activate()
    jax.config.update("jax_enable_x64", False)  # gpdk import enables x64 via SAX/klujax
    pld.config.BACKEND = "hlo"
    _CONFIGURED = True


def _build_scene():
    """Two 3-waveguide bundles with three rectangular obstacles."""
    route_xs = gf.cross_section.strip(width=0.5, radius=5.0, radius_min=5.0)
    waveguide = gf.c.straight(length=10.0 * _SCALE, cross_section=route_xs)

    b0_start_array = gf.components.array(
        waveguide, columns=1, rows=_N_PORTS, row_pitch=3.0 * _SCALE
    )
    b0_end_array = gf.components.array(
        waveguide, columns=1, rows=_N_PORTS, row_pitch=4.2 * _SCALE
    )
    b1_start_array = gf.components.array(
        waveguide, columns=1, rows=_N_PORTS, row_pitch=3.0 * _SCALE
    )
    b1_end_array = gf.components.array(
        waveguide, columns=1, rows=_N_PORTS, row_pitch=3.6 * _SCALE
    )

    c = gf.Component()
    b0_start = c << b0_start_array
    b0_end = c << b0_end_array
    b1_start = c << b1_start_array
    b1_end = c << b1_end_array
    b0_end.move((100.0 * _SCALE, 100.0 * _SCALE))

    obstacle = gf.components.rectangle(size=(100.0 * _SCALE, 10.0 * _SCALE))
    obs1 = c << obstacle
    obs2 = c << obstacle
    obs1.ymin = 40.0 * _SCALE
    obs2.xmin = 35.0 * _SCALE

    upper_obstacle = gf.components.rectangle(size=(50.0 * _SCALE, 20.0 * _SCALE))
    obs3 = c << upper_obstacle
    obs3.xmin = obs1.xmin + 15.0 * _SCALE
    b0_top_port_y = min(p.dcenter[1] for p in b0_end.ports.filter(orientation=180))
    obs3.ymin = b0_top_port_y - obs3.ysize / 2

    clearance = 12.0 * _SCALE
    top_center_x = (obs1.xmin + obs1.xmax) / 2
    top_pair_y = obs1.ymax + clearance
    bottom_right_x = obs2.xmax + 10.0 * _SCALE
    bottom_pair_y = obs2.ymax + clearance

    b1_start.move(
        (
            top_center_x - b1_start.ports[_MIDDLE_PORT].dcenter[0],
            top_pair_y - b1_start.ports[_MIDDLE_PORT].dcenter[1],
        )
    )
    b1_end.move(
        (
            bottom_right_x - b1_end.ports[_MIDDLE_PORT].dcenter[0],
            bottom_pair_y - b1_end.ports[_MIDDLE_PORT].dcenter[1],
        )
    )

    label_distance = 5.0 * _SCALE
    b0_start_ports = [b0_start.ports[f"o2_{i}_1"] for i in _PORT_INDICES]
    b0_end_ports = [b0_end.ports[f"o1_{i}_1"] for i in _PORT_INDICES]
    b1_start_ports = [b1_start.ports[f"o1_{i}_1"] for i in _PORT_INDICES]
    b1_end_ports = [b1_end.ports[f"o1_{i}_1"] for i in reversed(_PORT_INDICES)]

    for idx, port in enumerate(b0_start_ports + b1_start_ports):
        orientation = int(round(float(port.orientation or 0))) % 360
        offsets = {
            0: (-label_distance, 0.0),
            90: (0.0, -label_distance),
            180: (label_distance, 0.0),
            270: (0.0, label_distance),
        }
        dx, dy = offsets.get(orientation, (0.0, label_distance))
        x, y = port.dcenter
        c.add_label(f"R{idx}", position=(x + dx, y + dy), layer="TEXT")

    return (
        c,
        b0_start_ports,
        b0_end_ports,
        b1_start_ports,
        b1_end_ports,
        [obs1, obs2, obs3],
        route_xs,
    )


@gf.cell(tags=["routing"])
def sample_routing_ai_path_length_manhattan() -> gf.Component:
    """Manhattan-only 6-route bundle (before finetuning).

    Two 3-waveguide bundles are routed around three obstacles using
    the search-based manhattan initializer only. Compare with
    ``sample_routing_ai_path_length_finetune`` to see the effect
    of gradient-based length matching.
    """
    _ensure_configured()
    c, b0_sp, b0_ep, b1_sp, b1_ep, obstacles, xs = _build_scene()

    router = pld.add_route_bundle(
        c,
        [b0_sp, b1_sp],
        [b0_ep, b1_ep],
        obstacles=obstacles,
        cross_section=xs,
    )
    router.build_gds()
    return c


@gf.cell(tags=["routing"])
def sample_routing_ai_path_length_finetune() -> gf.Component:
    """Length-matched 6-route bundle with gradient finetuning.

    Two 3-waveguide bundles are routed around three obstacles.
    Routes are paired (R0-R3, R1-R4, R2-R5) for length matching.
    Finetuning adjusts pivot positions until paired routes match
    to sub-micron accuracy.
    """
    _ensure_configured()
    c, b0_sp, b0_ep, b1_sp, b1_ep, obstacles, xs = _build_scene()

    router = pld.add_route_bundle(
        c,
        [b0_sp, b1_sp],
        [b0_ep, b1_ep],
        obstacles=obstacles,
        cross_section=xs,
    )
    router.length_matching_groups = [[0, 3], [1, 4], [2, 5]]
    router.finetune(
        lr=0.2,
        max_steps=2000,
        non_manhattan=5,
        length_matching=15,
        manhattan_constrained=False,
    )
    router.build_gds()
    return c
