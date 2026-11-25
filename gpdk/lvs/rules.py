"""gflvs LVS rules for the generic PDK (gpdk).

Usage::

    import gflvs
    from gpdk.lvs.rules import DEFAULT_LVS_CONFIG

    ok, extracted, l2n, report = gflvs.lvs(
        netlist, lib, DEFAULT_LVS_CONFIG, topcell=component.name
    )

Pass ``topcell``: an empty one picks gdsfactory's ``$$$CONTEXT_INFO$$$`` cell.

What is recognised:

* ``pad``: an electrical device, its ``e1``..``e4`` ports being one terminal, as the pad is one polygon on
  ``M3``. A ``pad_array`` is not a device: it places ``pad`` cells, each one extracted as a ``pad``.
* ``coupler`` and ``mmi1x2``: waveguide devices, fitted to the gpdk PCell (parameters compared, never skipped).
* Passthrough cells (``PASSTHROUGH_DEVICE_CLASS_NAMES``): the routing cells of optical and electrical routes
  and the ``rectangle`` metal, see below. gflvs matches these as lowercase cell-name *prefixes*, so each one
  includes the first letter of the generated parameter suffix to leave the devices that share a function-name
  prefix out. Passthrough: ``straight_L*``, ``bend_euler_R*``, ``taper_L*``, ``taper_electrical_L*``,
  ``wire_corner_CS*`` and ``rectangle_S*``. Not passthrough: ``straight_heater_*``, ``straight_pn*``,
  ``straight_pin*``, ``straight_all_angle``, ``straight_array``, ``bend_euler_s``, ``bend_euler180``,
  ``taper_adiabatic``, ``taper_strip_to_*``, ``wire_corner45``, ``wire_corner_sections``,
  ``rectangle_with_slits`` and ``rectangles``.

Scope caveats of the passthrough, to carry into the spec: any ``straight_L*``/``bend_euler_R*``/``taper_L*`` cell
is a net whatever its layers, and every ``taper_electrical`` and ``rectangle`` is too, so a ``rectangle`` drawn on
``WG`` is a waveguide net element rather than a device. A device cell with a function name outside the list above
is searched for devices, not skipped.

Decisions, from the Elvis corpus (``coupler_test``, ``elec``, ``wire_crossing_yaml(_shorted)``):

* ``pad_array``: no template. It draws no polygon of its own, so it is left to its ``pad`` children and the
  reference netlist lists its pads as ``pad`` devices, not one ``pad_array`` device.
* ``rectangle``: no template. A ``rectangle`` is plain metal on a drawing layer: a net shape the tracer follows,
  not a device (the pad template would otherwise extract it as a ``pad``).
* Routing components: the layout's routing cells (``straight``, ``wire_corner``, ``taper``, ...) are
  passthrough cells. A reference netlist must carry only devices: build it dropping the routing instances the
  way gdsfactoryplus does for Elvis (``check/lvs.py:_routing_component_names``, the cell names of the
  ``purpose == "routing"`` instances of the layout) and the schematic ``rectangle`` instances.
"""

from __future__ import annotations

from collections.abc import Callable

import gdstk
from gflvs import (
    LVS_EQUIVALENT_TERMINALS_PROPERTY,
    ElectricalDeviceExtractionConfig,
    LvsConfig,
    NetlistTracerConfig,
    WaveguideDeviceExtractionConfig,
)
from gflvs.gflvs_schema import (
    DeviceParameterTemplate,
    DeviceTemplate,
    DeviceTerminalTemplate,
    DeviceTerminalType,
    LayerGds,
    LayerOperation,
    LayerRef,
)

from gpdk import cells
from gpdk.tech import LAYER

LayerKey = tuple[int, int]

WG: LayerKey = (LAYER.WG.layer, LAYER.WG.datatype)
M3: LayerKey = (LAYER.M3.layer, LAYER.M3.datatype)

# kfactory requires even widths in dbu: generated PCells snap their parameters to this grid
PARAMETER_GRID = 0.002

# The PCell fit lands within a grid step of the drawn value (gap 0.1996 for 0.2), which gflvs's default relative
# parameter tolerance (1e-3) rejects. 1 % accepts every fit and still rejects a drawn value that differs by more.
PARAMETER_RELATIVE_TOLERANCE = 0.01

# Cell-name prefixes, lowercase (gflvs lowercases the cell name before matching): they include the first
# parameter letter of the routing cells' generated names (``straight_L10_...``, ``bend_euler_RNone_...``) so that
# the devices sharing the function-name prefix are not swallowed: ``straight_heater_*``, ``straight_pn*``,
# ``bend_euler_s``, ``taper_strip_to_ridge``, ``rectangle_with_slits``, ...
PASSTHROUGH_DEVICE_CLASS_NAMES: tuple[str, ...] = (
    "straight_l",
    "bend_euler_r",
    "taper_l",
    "taper_electrical_l",
    "wire_corner_cs",
    "rectangle_s",
)


def _layer_op(layer: LayerKey) -> LayerOperation:
    return LayerOperation(
        layer_ref_left=LayerRef(layer=LayerGds(layer=layer[0], datatype=layer[1]))
    )


def _snap(value: float) -> float:
    return round(round(value / PARAMETER_GRID) * PARAMETER_GRID, 6)


def _to_gdstk_cell(component: object) -> gdstk.Cell:
    """The polygons of a gdsfactory *component* in a flat gdstk cell."""
    cell = gdstk.Cell(str(component.name))  # type: ignore[attr-defined]
    for layer_key, polygons in component.get_polygons_points(by="tuple").items():  # type: ignore[attr-defined]
        layer, datatype = layer_key
        cell.add(
            *(
                gdstk.Polygon(points.tolist(), int(layer), int(datatype))
                for points in polygons
            )
        )
    return cell


def coupler_cell(gap: float, length: float) -> gdstk.Cell:
    """The gpdk ``coupler`` PCell for the fit search."""
    return _to_gdstk_cell(cells.coupler(gap=_snap(gap), length=_snap(length)))


def mmi1x2_cell(length_mmi: float, width_mmi: float) -> gdstk.Cell:
    """The gpdk ``mmi1x2`` PCell for the fit search."""
    return _to_gdstk_cell(
        cells.mmi1x2(length_mmi=_snap(length_mmi), width_mmi=_snap(width_mmi))
    )


PCELL_GENERATORS: dict[str, Callable[..., gdstk.Cell]] = {
    "coupler": coupler_cell,
    "mmi1x2": mmi1x2_cell,
}

PAD_TEMPLATE = DeviceTemplate(
    device_name="pad",
    device_class_name="pad",
    device_terminal_template=[
        DeviceTerminalTemplate(
            terminal_name="e1",
            terminal_type=DeviceTerminalType.DEVICE_TERMINAL_TYPE_PIN,
            layer_composed_op=_layer_op(M3),
        )
    ],
    # the pad ports e1..e4 are the one M3 polygon
    properties={LVS_EQUIVALENT_TERMINALS_PROPERTY: "e1,e2,e3,e4"},
)
COUPLER_TEMPLATE = DeviceTemplate(
    device_name="coupler",
    device_class_name="coupler",
    device_parameter_template=[
        DeviceParameterTemplate(name="gap", param_bound_min=0.1, param_bound_max=1.0),
        DeviceParameterTemplate(
            name="length", param_bound_min=1.0, param_bound_max=100.0
        ),
    ],
)
MMI1X2_TEMPLATE = DeviceTemplate(
    device_name="mmi1x2",
    device_class_name="mmi1x2",
    device_parameter_template=[
        DeviceParameterTemplate(
            name="length_mmi", param_bound_min=2.0, param_bound_max=20.0
        ),
        DeviceParameterTemplate(
            name="width_mmi", param_bound_min=2.0, param_bound_max=8.0
        ),
    ],
)

DEVICE_TEMPLATES: list[DeviceTemplate] = [
    PAD_TEMPLATE,
    COUPLER_TEMPLATE,
    MMI1X2_TEMPLATE,
]


def build_lvs_config() -> LvsConfig:
    """Build the gpdk LvsConfig."""
    return LvsConfig(
        parameter_relative_tolerance=PARAMETER_RELATIVE_TOLERANCE,
        device_templates=DEVICE_TEMPLATES,
        netlist_tracer_config=NetlistTracerConfig(
            galvanic_drawing_layers=frozenset({M3}),
            waveguide_drawing_layers=frozenset({WG}),
            passthrough_device_class_names=PASSTHROUGH_DEVICE_CLASS_NAMES,
        ),
        electrical_device_extraction_config=ElectricalDeviceExtractionConfig(
            galvanic_drawing_layers=frozenset({M3}),
        ),
        waveguide_device_extraction_config=WaveguideDeviceExtractionConfig(
            pcell_generators=PCELL_GENERATORS,
            waveguide_layers=frozenset({WG}),
        ),
    )


DEFAULT_LVS_CONFIG = build_lvs_config()
