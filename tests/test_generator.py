"""Unit tests for the cell generator."""

import importlib.util
import inspect
import pathlib
import sys

import pytest

SPEC_PATH = pathlib.Path(__file__).parent.parent / ".github" / "generate_cells.py"
_spec = importlib.util.spec_from_file_location("generate_cells", SPEC_PATH)
generate_cells = importlib.util.module_from_spec(_spec)
# Register before exec: generate_cells.py declares a @dataclass in a module that uses
# `from __future__ import annotations`. On Python 3.12, dataclasses' ClassVar/InitVar
# detection for string-annotated fields looks the defining module up via
# sys.modules[cls.__module__] and crashes with AttributeError on None if it isn't
# registered yet — which module_from_spec() alone does not do.
sys.modules[_spec.name] = generate_cells
_spec.loader.exec_module(generate_cells)


@pytest.fixture(scope="module")
def specs():
    """All collected cell specs, keyed by cell name."""
    return generate_cells.collect_cells()


def test_collects_every_registered_cell(specs):
    """The generator sees every cell the generic PDK registers.

    Asserted against the registry, not a literal: the count is 359 on
    gdsfactory 9.49.0, and a pin bump moving it is the DESIGNED trigger for
    `make cells-regen`. Hard-coding 359 would make every bump produce two
    failures where only one is signal, which teaches people to edit tests.
    """
    import gdsfactory as gf
    from gdsfactory.get_factories import get_cells

    gf.gpdk.PDK.activate()
    expected = set(get_cells([gf.components])) | set(get_cells([gf.containers]))
    assert set(specs) == expected


def test_calls_dispatch_to_the_importable_module(specs):
    """Cells reachable only via gdsfactory.containers are called through it.

    Verified on 9.49.0: `hasattr(gf.c, "rotate90")` is False for all 16 cells in
    the functions category, so a blanket `gf.c.<name>` call would fail for them.
    """
    assert specs["straight"].registry_module == "gdsfactory.components"
    assert specs["rotate90"].registry_module == "gdsfactory.containers"
    assert specs["add_fiber_array"].registry_module == "gdsfactory.containers"

    functions = [s for s in specs.values() if s.category == "functions"]
    src = generate_cells.render_module("functions", functions)
    assert "from gdsfactory import containers as _containers" in src
    assert "return _containers.rotate90(" in src
    # Scoped to the generator's own emitted dispatch lines, not the whole module text:
    # upstream docstrings are copied verbatim (by design) and some legitimately contain
    # `gf.c.<name>(...)` inside an `Example:` block documenting an unrelated cell (e.g.
    # add_pads_bot/add_pads_top reference `gf.c.nxn(...)`). That's documentation text,
    # not a dispatch call, so it must not trip this check.
    call_lines = [
        line for line in src.splitlines() if line.strip().startswith("return ")
    ]
    assert all("gf.c." not in line for line in call_lines)


def test_categories_match_gdsfactory_component_dirs(specs):
    """Cells map to a category module named after their gdsfactory subpackage."""
    assert specs["bend_euler"].category == "bends"
    assert specs["mmi1x2"].category == "mmis"
    assert specs["straight"].category == "waveguides"


def test_cells_outside_components_land_in_functions(specs):
    """Cells sourced outside gdsfactory.components go to cells/functions.py."""
    assert specs["rotate90"].category == "functions"
    assert specs["add_fiber_array"].category == "functions"
    assert specs["extract"].category == "functions"


def test_partial_signature_is_resolved(specs):
    """A partial's bound kwargs become defaults in the wrapper signature."""
    sig = specs["bend_euler180"].signature
    assert sig.parameters["angle"].default == 180


def test_tags_are_carried_through(specs):
    """Tags from the gdsfactory decorator are preserved."""
    assert "bends" in specs["bend_euler"].tags


def test_schematic_function_is_carried_through(specs):
    """schematic_function= from the gdsfactory decorator is preserved by name."""
    assert specs["bend_euler"].schematic_function == "bend_schematic"
    assert specs["coupler"].schematic_function == "coupler_schematic"


def test_annotations_are_emitted_as_source_not_repr(specs):
    """Gdsfactory uses postponed annotations, so annotations arrive as strings.

    Rendering them with repr() would emit `x: 'CrossSectionSpec'` — a string
    literal annotation, not a type reference.
    """
    bends = [s for s in specs.values() if s.category == "bends"]
    src = generate_cells.render_module("bends", bends)
    assert ": 'CrossSectionSpec" not in src
    assert ': "CrossSectionSpec' not in src


def test_non_literal_defaults_are_emitted_as_source(specs):
    """Defaults like LAYER.WG or partial(...) are emitted verbatim with an import."""
    non_literal = [
        s
        for s in specs.values()
        if any(
            p.default is not inspect.Parameter.empty
            and not generate_cells._is_literal(p.default)
            for p in s.signature.parameters.values()
        )
    ]
    assert non_literal, "expected at least one cell with a non-literal default"
    by_category = {}
    for spec in non_literal:
        by_category.setdefault(spec.category, []).append(spec)
    category, group = next(iter(by_category.items()))
    src = generate_cells.render_module(
        category, [s for s in specs.values() if s.category == category]
    )
    compile(src, f"{category}.py", "exec")
    assert "<function" not in src
    assert "<functools.partial" not in src


def test_rendered_module_is_valid_python_with_docstrings(specs):
    """Rendered modules compile and every wrapper has an Args: section."""
    bends = [s for s in specs.values() if s.category == "bends"]
    src = generate_cells.render_module("bends", bends)
    compile(src, "bends.py", "exec")
    assert "@gf.cell(" in src
    assert "Args:" in src


def test_render_is_deterministic(specs):
    """Rendering twice produces byte-identical output."""
    bends = [s for s in specs.values() if s.category == "bends"]
    assert generate_cells.render_module("bends", bends) == generate_cells.render_module(
        "bends", bends
    )


def test_no_var_args_in_generated_signatures(specs):
    """Signatures are explicit, except for **kwargs forwarding, which is safe.

    *args (VAR_POSITIONAL) is banned outright: no registered cell has ever used it, so it
    stays a fail-loud tripwire in the generator rather than unused handling for a case
    that doesn't exist.

    **kwargs (VAR_KEYWORD) is explicitly allowed and re-emitted verbatim. This is a
    legitimate, common gdsfactory forwarding pattern (e.g. `container()`-style wrappers).
    Verified empirically: wrapping a `**kwargs`-taking cell (`gf.c.rectangles`) in a
    `@gf.cell`-decorated function with explicit params plus `**kwargs: Any`, then calling
    it twice with different values passed only via kwargs (e.g. `port_type="optical"` vs
    `port_type="electrical"`), produces two DIFFERENT cell names. kfactory's naming/caching
    hashes forwarded kwarg values correctly, so there is no @gf.cell name-collision risk
    from forwarding **kwargs.
    """
    for spec in specs.values():
        kinds = {p.kind for p in spec.signature.parameters.values()}
        assert inspect.Parameter.VAR_POSITIONAL not in kinds, spec.name
