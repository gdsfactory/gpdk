"""Cell metadata annotations for gpdk cells.

Registers kfactory factory-metadata providers (``gf.kcl.metadata_for``) for
every gpdk cell that has a SAX model in ``gpdk.models``: a Mosaic *device
type* (symbol), classification *tags*, a list of *ports* whose declared
``side`` matches the cell's real GDS port orientation (left=180, right=0,
top=90, bottom=270) and whose order is clockwise-from-left within each side,
and the SAX model link.

Targeted metadata registration requires the cell factories to exist, so this
module imports ``gpdk.cells`` first and must not be imported *by* the
component modules (``gpdk/__init__`` imports it last).

Targets are **fully-qualified** factory names (``<module>.<function>``), not
bare cell names. gpdk cells use plain ``@gf.cell``, so they register under
short, unmangled names, and a bare target raises ``ValueError: Ambiguous
factory name ...`` as soon as anything else registers that same short name in
``gf.kcl``. A FQN resolves to exactly one definition site and cannot collide.

Each provider ignores the cell's call ``**kwargs`` and always emits the same
fixed metadata: it is a snapshot of the cell built with its *default*
arguments. Overriding port-affecting kwargs at call time (e.g.
``port_names``/``port_types``/``cross_section``) can produce a component whose
ports diverge from this snapshot. That is acceptable for schematic-capture
(symbols are placed and parametrized in the editor, not derived from a
specific GDS call), and ``tests/test_schematics.py`` validates the
default-argument build.

SAX model links (``metadata.models``) point at ``gpdk.models``: SAX binds
ports by name (both the schematic-circuit and layout paths) and
``sax.circuit`` resolves models by cell name, so each linked cell has a model
in ``PDK.models`` keyed by the cell name whose SDict port keys are the cell's
own port names. ``straight_heater_metal`` also has a model but is a
``functools.partial`` of ``straight_heater_metal_undercut`` (no registered
factory of its own), so only the base cell is annotated.
"""

from __future__ import annotations

from collections.abc import Callable

import gdsfactory as gf

import gpdk.cells  # noqa: F401  # cells must be registered before annotating

# side -> outward GDS port orientation in degrees
_SIDE_ORIENTATION = {
    "left": 180,
    "right": 0,
    "top": 90,
    "bottom": 270,
}

# port "kind" -> cross-section hint for the port stub. Kinds without an entry
# (e.g. the vertical fiber ports of grating couplers) get no hint.
_PORT_CROSS_SECTION = {
    "optical": "strip",
    "electrical": "metal_routing",
}

# valid port kinds: the gdsfactory port_type values used by gpdk cells
_PORT_KINDS = {"optical", "electrical", "vertical_te", "vertical_tm"}

# dotted path of the SAX models module referenced by sax_model() entries
_MODULE = "gpdk.models"

# dotted path of the circulax active models module
_ACTIVE_MODULE = "gpdk.models.active"


def _port_specs(ports: list[dict]) -> list[dict]:
    """Expand the compact port declarations into full ``PortSpec`` dicts."""
    specs: list[dict] = []
    seen_sides: dict[str, int] = {}
    for port in ports:
        side = port["side"]
        if side not in _SIDE_ORIENTATION:
            raise ValueError(
                f"port {port['name']!r}: unknown side {side!r} "
                f"(expected one of {sorted(_SIDE_ORIENTATION)})"
            )
        kind = port["kind"]
        if kind not in _PORT_KINDS:
            raise ValueError(
                f"port {port['name']!r}: unknown kind {kind!r} "
                f"(expected one of {sorted(_PORT_KINDS)})"
            )
        order = seen_sides.get(side, 0)
        seen_sides[side] = order + 1
        spec = {
            "name": port["name"],
            "kind": kind,
            "side": side,
            "orientation": _SIDE_ORIENTATION[side],
            "order": order,
        }
        cross_section = _PORT_CROSS_SECTION.get(kind)
        if cross_section is not None:
            spec["cross_section"] = cross_section
        specs.append(spec)
    return specs


def sax_model(
    name: str,
    module: str,
    port_order: list[str],
    qualname: str | None = None,
    params: dict[str, str] | None = None,
) -> dict:
    """Build a SAX model entry for ``metadata.models``."""
    return {
        "language": "sax",
        "name": name,
        "module": module,
        "qualname": qualname or name,
        "port_order": port_order,
        "params": params or {},
    }


def circulax_model(
    name: str,
    module: str,
    port_order: list[str],
    qualname: str | None = None,
    params: dict[str, str] | None = None,
    port_map: dict[str, str] | None = None,
    defaults: dict[str, float] | None = None,
) -> dict:
    """Build a circulax model entry for ``metadata.models``."""
    entry: dict = {
        "language": "circulax",
        "name": name,
        "module": module,
        "qualname": qualname or name,
        "port_order": port_order,
        "params": params or {},
    }
    if port_map is not None:
        entry["port_map"] = port_map
    if defaults is not None:
        entry["defaults"] = defaults
    return entry


# ---------------------------------------------------------------------------
# Per-cell metadata annotations (device_type, tags, ports verified against the GDS)
# ---------------------------------------------------------------------------


@gf.kcl.metadata_for("gpdk.cells.waveguides.straight")
def straight_metadata() -> dict:
    return {
        "device_type": "straight",
        "tags": ["waveguide"],
        "ports": _port_specs(
            [
                {"name": "o1", "side": "left", "kind": "optical"},
                {"name": "o2", "side": "right", "kind": "optical"},
            ]
        ),
        "models": [
            sax_model("straight", _MODULE, ["o1", "o2"], params={"length": "length"})
        ],
    }


@gf.kcl.metadata_for("gpdk.cells.bends.bend_euler")
def bend_euler_metadata() -> dict:
    return {
        "device_type": "bend",
        "tags": ["bend", "euler"],
        "ports": _port_specs(
            [
                {"name": "o1", "side": "left", "kind": "optical"},
                {"name": "o2", "side": "top", "kind": "optical"},
            ]
        ),
        # No param mapping: the bend's optical length is derived from its
        # path (exposed via the component info dictionary), not a cell kwarg.
        "models": [sax_model("bend_euler", _MODULE, ["o1", "o2"])],
    }


@gf.kcl.metadata_for("gpdk.cells.bends.bend_s")
def bend_s_metadata() -> dict:
    return {
        "device_type": "sbend",
        "tags": ["bend", "sbend"],
        "ports": _port_specs(
            [
                {"name": "o1", "side": "left", "kind": "optical"},
                {"name": "o2", "side": "right", "kind": "optical"},
            ]
        ),
        # No param mapping: the s-bend's optical length is derived from its
        # path (exposed via the component info dictionary), not a cell kwarg.
        "models": [sax_model("bend_s", _MODULE, ["o1", "o2"])],
    }


@gf.kcl.metadata_for("gpdk.cells.waveguides.wire_corner")
def wire_corner_metadata() -> dict:
    return {
        "device_type": "ckt",
        "tags": ["wire", "corner"],
        "ports": _port_specs(
            [
                {"name": "e1", "side": "left", "kind": "electrical"},
                {"name": "e2", "side": "top", "kind": "electrical"},
            ]
        ),
        "models": [sax_model("wire_corner", _MODULE, ["e1", "e2"])],
    }


@gf.kcl.metadata_for("gpdk.cells.tapers.taper")
def taper_metadata() -> dict:
    return {
        "device_type": "taper",
        "tags": ["taper"],
        "ports": _port_specs(
            [
                {"name": "o1", "side": "left", "kind": "optical"},
                {"name": "o2", "side": "right", "kind": "optical"},
            ]
        ),
        "models": [
            sax_model("taper", _MODULE, ["o1", "o2"], params={"length": "length"})
        ],
    }


@gf.kcl.metadata_for("gpdk.cells.tapers.taper_strip_to_ridge")
def taper_strip_to_ridge_metadata() -> dict:
    return {
        "device_type": "transition",
        "tags": ["taper", "transition", "rib"],
        "ports": _port_specs(
            [
                {"name": "o1", "side": "left", "kind": "optical"},
                {"name": "o2", "side": "right", "kind": "optical"},
            ]
        ),
        "models": [
            sax_model(
                "taper_strip_to_ridge",
                _MODULE,
                ["o1", "o2"],
                params={"length": "length"},
            )
        ],
    }


@gf.kcl.metadata_for("gpdk.cells.mmis.mmi1x2")
def mmi1x2_metadata() -> dict:
    return {
        "device_type": "mmi-1x2",
        "tags": ["mmi", "1x2"],
        "ports": _port_specs(
            [
                {"name": "o1", "side": "left", "kind": "optical"},
                {"name": "o2", "side": "right", "kind": "optical"},
                {"name": "o3", "side": "right", "kind": "optical"},
            ]
        ),
        "models": [sax_model("mmi1x2", _MODULE, ["o1", "o2", "o3"])],
    }


@gf.kcl.metadata_for("gpdk.cells.mmis.mmi2x2")
def mmi2x2_metadata() -> dict:
    return {
        "device_type": "mmi-2x2",
        "tags": ["mmi", "2x2"],
        "ports": _port_specs(
            [
                {"name": "o1", "side": "left", "kind": "optical"},
                {"name": "o2", "side": "left", "kind": "optical"},
                {"name": "o3", "side": "right", "kind": "optical"},
                {"name": "o4", "side": "right", "kind": "optical"},
            ]
        ),
        "models": [sax_model("mmi2x2", _MODULE, ["o1", "o2", "o3", "o4"])],
    }


@gf.kcl.metadata_for("gpdk.cells.couplers.coupler")
def coupler_metadata() -> dict:
    return {
        "device_type": "coupler",
        "tags": ["coupler", "directional"],
        "ports": _port_specs(
            [
                {"name": "o1", "side": "left", "kind": "optical"},
                {"name": "o2", "side": "left", "kind": "optical"},
                {"name": "o3", "side": "right", "kind": "optical"},
                {"name": "o4", "side": "right", "kind": "optical"},
            ]
        ),
        "models": [
            sax_model(
                "coupler",
                _MODULE,
                ["o1", "o2", "o3", "o4"],
                params={"length": "length", "gap": "gap"},
            )
        ],
    }


@gf.kcl.metadata_for("gpdk.cells.couplers.coupler_ring")
def coupler_ring_metadata() -> dict:
    return {
        "device_type": "coupler-ring",
        "tags": ["coupler", "ring"],
        "ports": _port_specs(
            [
                {"name": "o1", "side": "left", "kind": "optical"},
                {"name": "o2", "side": "top", "kind": "optical"},
                {"name": "o3", "side": "top", "kind": "optical"},
                {"name": "o4", "side": "right", "kind": "optical"},
            ]
        ),
        "models": [
            sax_model(
                "coupler_ring",
                _MODULE,
                ["o1", "o2", "o3", "o4"],
                params={"gap": "gap", "radius": "radius", "length_x": "length_x"},
            )
        ],
    }


@gf.kcl.metadata_for("gpdk.cells.waveguides.crossing")
def crossing_metadata() -> dict:
    return {
        "device_type": "crossing",
        "tags": ["crossing"],
        "ports": _port_specs(
            [
                {"name": "o1", "side": "left", "kind": "optical"},
                {"name": "o2", "side": "top", "kind": "optical"},
                {"name": "o3", "side": "right", "kind": "optical"},
                {"name": "o4", "side": "bottom", "kind": "optical"},
            ]
        ),
        "models": [sax_model("crossing", _MODULE, ["o1", "o2", "o3", "o4"])],
    }


@gf.kcl.metadata_for("gpdk.cells.grating_couplers.grating_coupler_elliptical")
def grating_coupler_elliptical_metadata() -> dict:
    return {
        "device_type": "grating-coupler",
        "tags": ["grating-coupler", "elliptical"],
        "ports": _port_specs(
            [
                {"name": "o1", "side": "left", "kind": "optical"},
                {"name": "o2", "side": "right", "kind": "vertical_te"},
            ]
        ),
        "models": [sax_model("grating_coupler_elliptical", _MODULE, ["o1", "o2"])],
    }


@gf.kcl.metadata_for("gpdk.cells.grating_couplers.grating_coupler_rectangular")
def grating_coupler_rectangular_metadata() -> dict:
    return {
        "device_type": "grating-coupler",
        "tags": ["grating-coupler", "rectangular"],
        "ports": _port_specs(
            [
                {"name": "o1", "side": "left", "kind": "optical"},
                {"name": "o2", "side": "right", "kind": "vertical_te"},
            ]
        ),
        "models": [sax_model("grating_coupler_rectangular", _MODULE, ["o1", "o2"])],
    }


@gf.kcl.metadata_for("gpdk.cells.waveguides.straight_heater_metal_undercut")
def straight_heater_metal_undercut_metadata() -> dict:
    # 2 optical ports plus two 4-sided electrical via stacks (l_* at the
    # input, r_* at the output); same-side ports all sit at the same
    # coordinate, so within-side order follows the logical o/l/r grouping.
    return {
        "device_type": "ckt",
        "tags": ["heater", "undercut"],
        "ports": _port_specs(
            [
                {"name": "o1", "side": "left", "kind": "optical"},
                {"name": "l_e1", "side": "left", "kind": "electrical"},
                {"name": "r_e1", "side": "left", "kind": "electrical"},
                {"name": "l_e2", "side": "top", "kind": "electrical"},
                {"name": "r_e2", "side": "top", "kind": "electrical"},
                {"name": "o2", "side": "right", "kind": "optical"},
                {"name": "l_e3", "side": "right", "kind": "electrical"},
                {"name": "r_e3", "side": "right", "kind": "electrical"},
                {"name": "r_e4", "side": "bottom", "kind": "electrical"},
                {"name": "l_e4", "side": "bottom", "kind": "electrical"},
            ]
        ),
        "models": [
            sax_model(
                "straight_heater_metal_undercut",
                _MODULE,
                [
                    "o1",
                    "o2",
                    "l_e1",
                    "l_e2",
                    "l_e3",
                    "l_e4",
                    "r_e1",
                    "r_e2",
                    "r_e3",
                    "r_e4",
                ],
                params={"length": "length"},
            ),
            circulax_model(
                "thermal_heater",
                _ACTIVE_MODULE,
                ["o1", "o2", "l_e1", "r_e1"],
                params={"length_um": "length"},
                port_map={
                    "o1": "opt_in",
                    "o2": "opt_out",
                    "l_e1": "ele_P",
                    "r_e1": "ele_N",
                },
            ),
        ],
    }


@gf.kcl.metadata_for("gpdk.cells.detectors.ge_detector_straight_si_contacts")
def ge_detector_straight_si_contacts_metadata() -> dict:
    return {
        "device_type": "photodiode",
        "tags": ["detector", "germanium"],
        "ports": _port_specs(
            [
                {"name": "o1", "side": "left", "kind": "optical"},
                {"name": "top", "side": "right", "kind": "electrical"},
                {"name": "bot", "side": "right", "kind": "electrical"},
            ]
        ),
        "models": [
            circulax_model(
                "ge_photodetector",
                _ACTIVE_MODULE,
                ["o1", "top", "bot"],
                port_map={
                    "o1": "opt_in",
                    "top": "ele_P",
                    "bot": "ele_N",
                },
            ),
        ],
    }


@gf.kcl.metadata_for("gpdk.cells.rings.ring_single_pn")
def ring_single_pn_metadata() -> dict:
    return {
        "device_type": "ring-single",
        "tags": ["ring", "modulator", "pn"],
        "ports": _port_specs(
            [
                {"name": "o1", "side": "left", "kind": "optical"},
                {"name": "gnd", "side": "top", "kind": "electrical"},
                {"name": "sig", "side": "top", "kind": "electrical"},
                {"name": "o2", "side": "right", "kind": "optical"},
                {"name": "heater_gnd", "side": "bottom", "kind": "electrical"},
                {"name": "heater_sig", "side": "bottom", "kind": "electrical"},
            ]
        ),
        "models": [
            circulax_model(
                "ring_modulator",
                _ACTIVE_MODULE,
                ["o1", "o2", "sig", "gnd"],
                params={"radius": "radius"},
                port_map={
                    "o1": "opt_in",
                    "o2": "opt_out",
                    "sig": "ele_P",
                    "gnd": "ele_N",
                },
            ),
        ],
    }


@gf.kcl.metadata_for("gpdk.cells.rings.ring_double_pn")
def ring_double_pn_metadata() -> dict:
    return {
        "device_type": "ring-double",
        "tags": ["ring", "modulator", "pn", "add-drop"],
        "ports": _port_specs(
            [
                {"name": "o1", "side": "left", "kind": "optical"},
                {"name": "o4", "side": "left", "kind": "optical"},
                {"name": "htr_bot_sig", "side": "top", "kind": "electrical"},
                {"name": "htr_top_gnd", "side": "top", "kind": "electrical"},
                {"name": "htr_bot_gnd", "side": "top", "kind": "electrical"},
                {"name": "htr_top_sig", "side": "top", "kind": "electrical"},
                {"name": "o3", "side": "right", "kind": "optical"},
                {"name": "o2", "side": "right", "kind": "optical"},
            ]
        ),
        # The current gdsfactory ring_double_pn exposes only heater electrical
        # ports (no PN-junction sig/gnd ports), so the add-drop circulax model
        # (which requires those PN ports) is not linked.
        "models": [],
    }


# ---------------------------------------------------------------------------
# Symbol-only annotations
#
# Cells without a SAX model of their own whose ports map one-to-one onto a
# Mosaic symbol (same port names, sides, and kinds as the annotated base cell
# above) and whose device is what the symbol depicts. They get a device type
# and ports but no model link. Each port list must cover *all* of the cell's
# ports; tests/test_schematics.py enforces that against the built default cell.
# ---------------------------------------------------------------------------

_LEFT_RIGHT = [
    {"name": "o1", "side": "left", "kind": "optical"},
    {"name": "o2", "side": "right", "kind": "optical"},
]

_LEFT_TOP = [
    {"name": "o1", "side": "left", "kind": "optical"},
    {"name": "o2", "side": "top", "kind": "optical"},
]

_1X2 = [
    {"name": "o1", "side": "left", "kind": "optical"},
    {"name": "o2", "side": "right", "kind": "optical"},
    {"name": "o3", "side": "right", "kind": "optical"},
]

_2X2 = [
    {"name": "o1", "side": "left", "kind": "optical"},
    {"name": "o2", "side": "left", "kind": "optical"},
    {"name": "o3", "side": "right", "kind": "optical"},
    {"name": "o4", "side": "right", "kind": "optical"},
]

# coupler_bent: o2 sits below o1 on the left, o4 below o3 on the right
_2X2_BENT = [
    {"name": "o2", "side": "left", "kind": "optical"},
    {"name": "o1", "side": "left", "kind": "optical"},
    {"name": "o3", "side": "right", "kind": "optical"},
    {"name": "o4", "side": "right", "kind": "optical"},
]

# ring_double: through bus o1 -> o2 at the bottom, drop bus o3 -> o4 at the
# top
_RING_DOUBLE = [
    {"name": "o1", "side": "left", "kind": "optical"},
    {"name": "o3", "side": "left", "kind": "optical"},
    {"name": "o4", "side": "right", "kind": "optical"},
    {"name": "o2", "side": "right", "kind": "optical"},
]

_CROSSING = [
    {"name": "o1", "side": "left", "kind": "optical"},
    {"name": "o2", "side": "top", "kind": "optical"},
    {"name": "o3", "side": "right", "kind": "optical"},
    {"name": "o4", "side": "bottom", "kind": "optical"},
]

_GRATING_TE = [
    {"name": "o1", "side": "left", "kind": "optical"},
    {"name": "o2", "side": "right", "kind": "vertical_te"},
]

_TERMINATOR = [
    {"name": "o1", "side": "left", "kind": "optical"},
]

# (fully-qualified factory name, device type, tags, ports)
_SYMBOL_ONLY: list[tuple[str, str, list[str], list[dict]]] = [
    # bends
    ("gpdk.cells.bends.bend_circular", "bend", ["bend", "circular"], _LEFT_TOP),
    ("gpdk.cells.bends.bend_euler_s", "sbend", ["bend", "sbend", "euler"], _LEFT_RIGHT),
    ("gpdk.cells.bends.bend_s_offset", "sbend", ["bend", "sbend"], _LEFT_RIGHT),
    # tapers and transitions
    ("gpdk.cells.tapers.taper_parabolic", "taper", ["taper", "parabolic"], _LEFT_RIGHT),
    ("gpdk.cells.tapers.taper_adiabatic", "taper", ["taper", "adiabatic"], _LEFT_RIGHT),
    ("gpdk.cells.tapers.taper_cross_section", "transition", ["taper", "transition"], _LEFT_RIGHT),
    ("gpdk.cells.tapers.taper_strip_to_ridge_trenches", "transition", ["taper", "transition", "rib"], _LEFT_RIGHT),
    ("gpdk.cells.tapers.taper_sc_nc", "transition", ["taper", "transition", "nitride"], _LEFT_RIGHT),
    ("gpdk.cells.tapers.taper_nc_sc", "transition", ["taper", "transition", "nitride"], _LEFT_RIGHT),
    # rings
    ("gpdk.cells.rings.ring_single", "ring-single", ["ring", "single"], _LEFT_RIGHT),
    ("gpdk.cells.rings.ring_single_bend_coupler", "ring-single", ["ring", "single", "bend-coupler"], _LEFT_RIGHT),
    ("gpdk.cells.rings.ring_double", "ring-double", ["ring", "double", "add-drop"], _RING_DOUBLE),
    # spirals and delay lines
    ("gpdk.cells.spirals.spiral_double", "spiral", ["spiral", "delay"], _LEFT_RIGHT),
    ("gpdk.cells.spirals.spiral_racetrack", "spiral", ["spiral", "racetrack", "delay"], _LEFT_RIGHT),
    ("gpdk.cells.spirals.delay_snake", "spiral", ["delay", "snake"], _LEFT_RIGHT),
    ("gpdk.cells.spirals.delay_snake2", "spiral", ["delay", "snake"], _LEFT_RIGHT),
    # terminators
    ("gpdk.cells.filters.terminator", "terminator", ["terminator"], _TERMINATOR),
    # couplers
    ("gpdk.cells.couplers.coupler_straight", "coupler", ["coupler", "directional"], _2X2),
    ("gpdk.cells.couplers.coupler_adiabatic", "coupler", ["coupler", "adiabatic"], _2X2),
    ("gpdk.cells.couplers.coupler_full", "coupler", ["coupler", "directional"], _2X2),
    ("gpdk.cells.couplers.coupler_bent", "coupler", ["coupler", "bent"], _2X2_BENT),
    # crossings
    ("gpdk.cells.waveguides.crossing_etched", "crossing", ["crossing", "etched"], _CROSSING),
    ("gpdk.cells.waveguides.crossing_linear_taper", "crossing", ["crossing", "taper"], _CROSSING),
    # MMIs
    ("gpdk.cells.mmis.mmi1x2_with_sbend", "mmi-1x2", ["mmi", "1x2", "sbend"], _1X2),
    ("gpdk.cells.mmis.mmi_tapered", "mmi-1x2", ["mmi", "1x2", "tapered"], _1X2),
    ("gpdk.cells.mmis.mmi2x2_with_sbend", "mmi-2x2", ["mmi", "2x2", "sbend"], _2X2),
    # grating couplers
    ("gpdk.cells.grating_couplers.grating_coupler_elliptical_trenches", "grating-coupler", ["grating-coupler", "elliptical", "trenches"], _GRATING_TE),
    ("gpdk.cells.grating_couplers.grating_coupler_elliptical_arbitrary", "grating-coupler", ["grating-coupler", "elliptical"], _GRATING_TE),
    ("gpdk.cells.grating_couplers.grating_coupler_elliptical_lumerical", "grating-coupler", ["grating-coupler", "elliptical"], _GRATING_TE),
    ("gpdk.cells.grating_couplers.grating_coupler_rectangular_arbitrary", "grating-coupler", ["grating-coupler", "rectangular"], _GRATING_TE),
]  # fmt: skip


def _symbol_only_provider(
    device_type: str, tags: list[str], ports: list[dict]
) -> Callable[[], dict]:
    def provider() -> dict:
        return {
            "device_type": device_type,
            "tags": list(tags),
            "ports": _port_specs(ports),
            "models": [],
        }

    return provider


for _target, _device_type, _tags, _ports in _SYMBOL_ONLY:
    gf.kcl.metadata_for(_target, _symbol_only_provider(_device_type, _tags, _ports))
