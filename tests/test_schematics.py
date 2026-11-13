"""Validate cell metadata annotations against the real GDS cells.

Mirrors the intel PDK's ``tests/test_schematics.py``: every annotated gpdk
cell must

* declare a non-empty ``device_type`` that is a symbol type supported by the
  gdsfactoryplus Mosaic editor,
* declare only ports that exist on the built component,
* declare each port on the ``side`` matching the component's GDS port
  orientation (left=180, right=0, top=90, bottom=270),
* declare each port ``kind`` matching the component's GDS ``port_type``,
* list same-side ports clockwise-from-left (left bottom->top, right top->bottom,
  top left->right, bottom right->left),
* link SAX models whose SDict port names map onto the cell's own port names.
"""

from __future__ import annotations

import gdsfactory as gf
import pytest

from gpdk import PDK
from gpdk._schematic import _SIDE_ORIENTATION, _SYMBOL_ONLY

# Schematic symbol types supported by the gdsfactoryplus Mosaic editor
# (frontend/mosaic/src/main/nyancad/mosaic/common.cljc :: device-types).
MOSAIC_DEVICE_TYPES = {
    "pmos", "nmos", "npn", "pnp", "resistor", "capacitor", "inductor",
    "vsource", "isource", "diode", "led", "photodiode", "modulator",
    "ckt", "amp",
    "straight", "bend", "sbend", "taper", "transition",
    "terminator", "crossing", "ring-single", "ring-double", "spiral",
    "splitter-1x2", "coupler", "coupler-ring",
    "mmi-1x2", "mmi-2x2", "mzi-1x2", "mzi-2x2",
    "grating-coupler",
}  # fmt: skip


@pytest.fixture(autouse=True)
def activate_pdk() -> None:
    """Activate the gpdk PDK (building cells needs its cross-sections)."""
    PDK.activate()


def _annotated() -> list[str]:
    """Names of all annotated factories in the registry.

    gpdk's annotations target the short-named factories registered by
    ``gpdk.components`` (the ``gdsfactory.components`` factories are
    registered under module-mangled names), so the metadata registry can be
    queried directly.
    """
    return sorted(factory.name for factory in gf.kcl.factories.with_metadata())


ANNOTATED_CELLS = _annotated()

# Lower bound on annotated cells: catches the discovery silently returning an
# empty set, which would make all per-cell parametrized tests collect nothing.
# Bump when adding a large batch of annotated cells.
_MIN_ANNOTATED_CELLS = 47


def _factory(name: str):
    return gf.kcl.factories.get_by_name(name)


def _metadata(name: str):
    return _factory(name).get_metadata()


def _orientation_close(a: float, b: float) -> bool:
    return abs(((a - b + 180) % 360) - 180) < 1.0


def test_annotated_count() -> None:
    """The PDK exposes (at least) the expected number of annotated cells."""
    assert len(ANNOTATED_CELLS) >= _MIN_ANNOTATED_CELLS, (
        f"only {len(ANNOTATED_CELLS)} annotated cells discovered "
        f"(expected >= {_MIN_ANNOTATED_CELLS})"
    )


@pytest.mark.parametrize("name", ANNOTATED_CELLS)
def test_device_type_is_supported(name: str) -> None:
    """Every device_type is non-empty and a supported Mosaic device type."""
    device_type = _metadata(name).device_type
    assert device_type, f"{name}: empty device_type"
    assert device_type in MOSAIC_DEVICE_TYPES, (
        f"{name}: device_type {device_type!r} is not a supported Mosaic device type"
    )


@pytest.mark.parametrize("name", ANNOTATED_CELLS)
def test_ports_subset_of_component(name: str) -> None:
    """Declared metadata ports are a subset of the built component's ports."""
    declared = {p["name"] for p in _metadata(name).ports}
    component_ports = {p.name for p in _factory(name)().ports}
    missing = declared - component_ports
    assert not missing, (
        f"{name}: metadata declares ports not on component: {sorted(missing)} "
        f"(component: {sorted(component_ports)})"
    )


# Symbol-only cells (no model link) by short factory name.
SYMBOL_ONLY_CELLS = sorted(target.rsplit(".", 1)[-1] for target, *_ in _SYMBOL_ONLY)


@pytest.mark.parametrize("name", SYMBOL_ONLY_CELLS)
def test_symbol_only_ports_cover_component(name: str) -> None:
    """Symbol-only annotations declare exactly the built component's ports.

    A symbol-only cell claims to map one-to-one onto its Mosaic symbol, so a
    port missing from its annotation would be a missing pin on the symbol.
    """
    declared = {p["name"] for p in _metadata(name).ports}
    component_ports = {p.name for p in _factory(name)().ports}
    assert declared == component_ports, (
        f"{name}: metadata ports {sorted(declared)} differ from component "
        f"ports {sorted(component_ports)}"
    )


@pytest.mark.parametrize("name", ANNOTATED_CELLS)
def test_port_sides_match_gds(name: str) -> None:
    """Each declared side matches the real GDS port orientation."""
    ports = {p.name: p for p in _factory(name)().ports}
    for p in _metadata(name).ports:
        ap = ports.get(p["name"])
        assert ap is not None, f"{name}.{p['name']}: missing on the GDS component"
        want = _SIDE_ORIENTATION[p["side"]]
        assert p["orientation"] == want, (
            f"{name}.{p['name']}: declared orientation {p['orientation']} does "
            f"not match side {p['side']!r} ({want} deg)"
        )
        if ap.orientation is None:
            continue
        got = float(ap.orientation) % 360
        assert _orientation_close(got, want), (
            f"{name}.{p['name']}: declared {p['side']!r} ({want} deg) "
            f"but GDS orientation is {got:.1f} deg"
        )


@pytest.mark.parametrize("name", ANNOTATED_CELLS)
def test_port_kinds_match_gds(name: str) -> None:
    """Each declared kind matches the real GDS port_type."""
    ports = {p.name: p for p in _factory(name)().ports}
    for p in _metadata(name).ports:
        ap = ports.get(p["name"])
        assert ap is not None, f"{name}.{p['name']}: missing on the GDS component"
        assert p["kind"] == ap.port_type, (
            f"{name}.{p['name']}: declared kind {p['kind']!r} but GDS "
            f"port_type is {ap.port_type!r}"
        )


@pytest.mark.parametrize("name", ANNOTATED_CELLS)
def test_ports_clockwise_from_left(name: str) -> None:
    """Same-side ports are listed clockwise-from-left with consecutive order."""
    ports = {p.name: p for p in _factory(name)().ports}
    by_side: dict[str, list[dict]] = {}
    for p in _metadata(name).ports:
        by_side.setdefault(p["side"], []).append(p)
    for side, specs in by_side.items():
        orders = [p["order"] for p in specs]
        assert orders == list(range(len(specs))), (
            f"{name} side {side!r}: port order indices {orders} are not "
            f"consecutive from 0"
        )
        if len(specs) < 2:
            continue
        names = [p["name"] for p in specs]
        coords = [
            ports[nm].y if side in ("left", "right") else ports[nm].x for nm in names
        ]
        ascending = side in ("left", "top")
        ok = all(
            (a <= b + 1e-6) if ascending else (a >= b - 1e-6)
            for a, b in zip(coords, coords[1:])
        )
        assert ok, (
            f"{name} side {side!r}: metadata order {names} is not clockwise "
            f"(GDS coords {[round(c, 2) for c in coords]})"
        )


def _sax_entries():
    """(cell, entry) for every SAX model entry across annotated cells."""
    out = []
    for name in ANNOTATED_CELLS:
        for entry in _metadata(name).models:
            if entry.get("language") == "sax":
                out.append((name, entry))
    return out


SAX_ENTRIES = _sax_entries()


@pytest.mark.skipif(not SAX_ENTRIES, reason="no SAX model links yet")
@pytest.mark.parametrize("name,entry", SAX_ENTRIES, ids=[n for n, _ in SAX_ENTRIES])
def test_sax_model_link(name: str, entry: dict) -> None:
    """A SAX link resolves to a real model whose SDict ports map onto the cell.

    SAX binds ports by name (both the schematic-circuit and layout paths), so the
    model's SDict keys must be a subset of the cell's actual port names, and of the
    declared ``port_order``. This is the port-mapping invariant.
    """
    import importlib

    import jax.numpy as jnp

    # 1) name resolves in PDK.models and the module/qualname imports
    assert entry["name"] in PDK.models, (
        f"{name}: model {entry['name']!r} not in PDK.models"
    )
    module = importlib.import_module(entry["module"])
    assert hasattr(module, entry["qualname"]), (
        f"{name}: {entry['module']}.{entry['qualname']} missing"
    )

    # 2) the cell's ports cover port_order, which covers the model's SDict keys
    cell_ports = {p.name for p in _factory(name)().ports}
    port_order = set(entry["port_order"])
    assert port_order <= cell_ports, (
        f"{name}: port_order {sorted(port_order)} not a subset of cell ports "
        f"{sorted(cell_ports)}"
    )

    # 3) the declared model params map onto the cell's own parameters
    import inspect

    cell_params = set(inspect.signature(_factory(name)._f).parameters)
    extra_params = set(entry["params"]) - cell_params
    assert not extra_params, (
        f"{name}: model params {sorted(extra_params)} are not parameters of "
        f"the cell {sorted(cell_params)}"
    )

    model = PDK.models[entry["name"]]
    try:
        sdict = model(wl=jnp.asarray(1.55))
    except (TypeError, NotImplementedError):
        return  # composite/non-evaluable model; name+import already checked
    used = {k for pair in sdict for k in pair}
    extra = used - port_order
    assert not extra, (
        f"{name}: model {entry['name']} SDict uses {sorted(extra)} not in "
        f"port_order {sorted(port_order)}"
    )
    missing = used - cell_ports
    assert not missing, (
        f"{name}: model {entry['name']} SDict ports {sorted(missing)} are not "
        f"ports of the cell {sorted(cell_ports)} (SAX binds by name)"
    )


def _circulax_entries():
    """(cell, entry) for every circulax model entry across annotated cells."""
    out = []
    for name in ANNOTATED_CELLS:
        for entry in _metadata(name).models:
            if entry.get("language") == "circulax":
                out.append((name, entry))
    return out


CIRCULAX_ENTRIES = _circulax_entries()


@pytest.mark.skipif(not CIRCULAX_ENTRIES, reason="no circulax model links yet")
@pytest.mark.parametrize(
    "name,entry", CIRCULAX_ENTRIES, ids=[n for n, _ in CIRCULAX_ENTRIES]
)
def test_circulax_model_link(name: str, entry: dict) -> None:
    """A circulax link resolves to a real model whose ports map onto the cell."""
    circulax = pytest.importorskip("circulax")  # noqa: F841

    import importlib

    module = importlib.import_module(entry["module"])
    assert hasattr(module, entry["qualname"]), (
        f"{name}: {entry['module']}.{entry['qualname']} missing"
    )

    cell_ports = {p.name for p in _factory(name)().ports}
    port_order = set(entry["port_order"])
    assert port_order <= cell_ports, (
        f"{name}: port_order {sorted(port_order)} not a subset of cell ports "
        f"{sorted(cell_ports)}"
    )

    port_map = entry.get("port_map")
    if port_map is not None:
        assert set(port_map.keys()) <= port_order, (
            f"{name}: port_map keys {sorted(port_map.keys())} not a subset of "
            f"port_order {sorted(port_order)}"
        )
        model_cls = getattr(module, entry["qualname"])
        model_ports = set(model_cls.ports)
        assert set(port_map.values()) <= model_ports, (
            f"{name}: port_map values {sorted(port_map.values())} not a subset "
            f"of model ports {sorted(model_ports)}"
        )
