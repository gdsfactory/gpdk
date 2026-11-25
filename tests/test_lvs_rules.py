"""gflvs LVS rules for gpdk: each corpus layout extracts the expected devices (skipped without gflvs).

The layouts are the Elvis LVS corpus schematics in ``tests/lvs_corpus`` built with gpdk.
"""

from __future__ import annotations

from functools import cache
from pathlib import Path

import gdsfactory as gf
import pytest

gflvs = pytest.importorskip("gflvs")

import gdstk  # noqa: E402
from kfnetlist import morphnet  # noqa: E402

from gpdk import PDK, cells  # noqa: E402
from gpdk.lvs.rules import DEFAULT_LVS_CONFIG  # noqa: E402

CORPUS = Path(__file__).parent / "lvs_corpus"
# the fit accepts a 1e-3 XOR: its parameters agree with the drawn ones within a grid step (um)
FIT_TOLERANCE = 1e-3


@pytest.fixture(autouse=True)
def activate_pdk() -> None:
    """Activate gpdk: building its cells needs its cross-sections and layers."""
    PDK.activate()


def library_of(component: gf.Component, directory: Path) -> gdstk.Library:
    """*component* written to GDS and read back, without gdsfactory's ``$$$CONTEXT_INFO$$$`` cell."""
    gds_path = directory / f"{component.name}.gds"
    component.write_gds(gds_path)
    library = gdstk.read_gds(str(gds_path))
    library.remove(*[cell for cell in library.cells if cell.name.startswith("$$$")])
    return library


def extracted_devices(
    component: gf.Component, directory: Path
) -> dict[str, list[dict[str, float]]]:
    """The devices gflvs extracts from *component*'s layout: class name -> one parameter dict per device."""
    config = DEFAULT_LVS_CONFIG
    netlist, _, _ = gflvs.layout_to_netlist(
        library_of(component, directory),
        component.name,
        device_templates=config.device_templates,
        nettracer_config=config.netlist_tracer_config,
        electrical_device_extraction_config=config.electrical_device_extraction_config,
        waveguide_device_extraction_config=config.waveguide_device_extraction_config,
    )
    devices: dict[str, list[dict[str, float]]] = {}
    for circuit in netlist.circuits:
        for subcircuit in circuit.subcircuits:
            devices.setdefault(subcircuit.class_name, []).append(
                {
                    parameter.name: parameter.default_value.prefixed_value.double_value
                    for parameter in subcircuit.parameters
                }
            )
    return devices


@cache
def corpus_component(name: str) -> gf.Component:
    """The gpdk layout of the corpus schematic *name*."""
    PDK.activate()
    return gf.read.from_yaml(CORPUS / f"{name}.pic.yml")


# corpus layout -> extracted device classes and counts. The routes (straight, wire_corner, taper cells) and
# the rectangle are passthrough nets, the pad_array is its pads
CORPUS_DEVICE_COUNTS = [
    ("coupler_test", {"coupler": 1}),
    ("elec", {"pad": 4}),
    ("wire_crossing_yaml", {"pad": 6}),
    ("wire_crossing_yaml_shorted", {"pad": 7}),
]


@pytest.mark.parametrize(("name", "expected_counts"), CORPUS_DEVICE_COUNTS)
def test_corpus_layout_extracts_its_devices(
    name: str, expected_counts: dict[str, int], tmp_path: Path
) -> None:
    """Routes and rectangles are nets, a pad_array is its pads: only devices are extracted."""
    devices = extracted_devices(corpus_component(name), tmp_path)
    assert {
        class_name: len(found) for class_name, found in devices.items()
    } == expected_counts
    if name == "coupler_test":
        # the fit lands within a grid step of the drawn gap and length
        assert devices["coupler"][0] == pytest.approx(
            {"gap": 0.2, "length": 10.0}, abs=FIT_TOLERANCE
        )


def test_mmi1x2_fit_recovers_its_parameters(tmp_path: Path) -> None:
    """The mmi1x2 PCell fit returns the drawn length and width."""
    top = gf.Component("mmi1x2_top")
    top.add_ref(cells.mmi1x2(length_mmi=8.0, width_mmi=3.0))
    (mmi,) = extracted_devices(top, tmp_path)["mmi1x2"]
    assert mmi == pytest.approx(
        {"length_mmi": 8.0, "width_mmi": 3.0}, abs=FIT_TOLERANCE
    )


def test_parameters_are_compared(tmp_path: Path) -> None:
    """A reference mmi1x2 of another length fails LVS: no template is blackboxed."""
    top = gf.Component("mmi1x2_mismatch_top")
    top.add_ref(cells.mmi1x2(length_mmi=8.0, width_mmi=3.0))
    reference = morphnet.Netlist(name=top.name, top_circuit=top.name)
    circuit = morphnet.circuit(top.name)
    circuit.add(
        morphnet.subcircuit(
            "mmi",
            "mmi1x2",
            class_name="mmi1x2",
            parameters=[("length_mmi", 12.0), ("width_mmi", 3.0)],
        )
    )
    reference.add(circuit)
    ok, _, _, report = gflvs.lvs(
        reference,
        library_of(top, tmp_path),
        DEFAULT_LVS_CONFIG,
        topcell=top.name,
    )
    assert not ok
    assert "LVS/parameter_mismatch" in {item.category for item in report.items}


@pytest.mark.parametrize(
    ("reference_gap", "clean"), [(0.2, True), (0.25, False)], ids=["drawn", "other"]
)
def test_coupler_parameters_pass_or_fail_at_the_shipped_tolerance(
    reference_gap: float, clean: bool, tmp_path: Path
) -> None:
    """The default config passes the coupler its own fit (gap 0.1996 for 0.2) and fails a clearly different gap."""
    top = gf.Component(f"coupler_tolerance_{round(reference_gap * 100)}_top")
    top.add_ref(cells.coupler(gap=0.2, length=10.0))
    reference = morphnet.Netlist(name=top.name, top_circuit=top.name)
    circuit = morphnet.circuit(top.name)
    circuit.add(
        morphnet.subcircuit(
            "coupler",
            "coupler",
            class_name="coupler",
            parameters=[("gap", reference_gap), ("length", 10.0)],
        )
    )
    reference.add(circuit)
    ok, _, _, report = gflvs.lvs(
        reference,
        library_of(top, tmp_path),
        DEFAULT_LVS_CONFIG,
        topcell=top.name,
    )
    categories = {item.category for item in report.items}
    assert ok is clean
    assert ("LVS/parameter_mismatch" in categories) is (not clean)


def test_routing_cells_are_passthrough(tmp_path: Path) -> None:
    """Routing cells are nets: none of them is extracted as a device."""
    top = gf.Component("routing_cells_top")
    for index, cell in enumerate(
        (
            cells.straight(length=10),
            cells.bend_euler(),
            cells.taper(),
            cells.taper_electrical(),
            cells.rectangle(layer="M3"),
            cells.wire_corner(),
        )
    ):
        top.add_ref(cell).move((index * 1000, 0))
    assert extracted_devices(top, tmp_path) == {}


@pytest.mark.parametrize(
    "device_cell",
    [
        lambda: cells.straight_heater_metal(length=100),
        lambda: cells.straight_heater_meander(),
        lambda: cells.straight_heater_metal_undercut(),
    ],
    ids=[
        "straight_heater_metal",
        "straight_heater_meander",
        "straight_heater_metal_undercut",
    ],
)
def test_devices_named_like_routing_cells_are_not_passthrough(
    device_cell, request: pytest.FixtureRequest, tmp_path: Path
) -> None:
    """A heater sharing the ``straight`` name prefix is searched for devices, not skipped."""
    top = gf.Component(f"{request.node.callspec.id}_top")
    top.add_ref(device_cell())
    assert extracted_devices(top, tmp_path)
