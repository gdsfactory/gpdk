"""Drift guards.

Tier A guards gpdk against gdsfactory's component set and survives the later stage where
core drops its own generic PDK. Tier B compares gpdk's copied technology against
``gdsfactory.gpdk`` and is deliberately temporary: when core removes that module these
tests skip themselves. The migration at that point is to DELETE tier B, not to fix it.
"""

import filecmp
import functools
import pathlib

import pytest

import gpdk

gf_gpdk = pytest.importorskip("gdsfactory.gpdk", reason="tier B: core dropped its gpdk")

GF_ROOT = pathlib.Path(gf_gpdk.__file__).parent
GF_KLAYOUT = GF_ROOT.parent / "generic_tech" / "klayout"


def test_layer_map_matches_core():
    """Tier B: every layer name and (layer, datatype) pair matches core."""
    ours = {layer.name: (layer.layer, layer.datatype) for layer in gpdk.tech.LAYER}
    theirs = {layer.name: (layer.layer, layer.datatype) for layer in gf_gpdk.LAYER}
    assert ours == theirs


def test_layer_stack_matches_core():
    """Tier B: layer stack level names and thicknesses match core."""
    ours = {
        name: (level.thickness, level.zmin)
        for name, level in gpdk.tech.LAYER_STACK.layers.items()
    }
    theirs = {
        name: (level.thickness, level.zmin)
        for name, level in gf_gpdk.LAYER_STACK.layers.items()
    }
    assert ours == theirs


def test_layer_views_yaml_is_byte_identical_to_core():
    """Tier B: layers.yaml is an unmodified copy of core's layer_views.yaml."""
    assert filecmp.cmp(gpdk.PATH.lyp_yaml, GF_ROOT / "layer_views.yaml", shallow=False)


def test_layers_lyp_is_byte_identical_to_core():
    """Tier B: layers.lyp is an unmodified copy of core's."""
    assert filecmp.cmp(gpdk.PATH.lyp, GF_KLAYOUT / "layers.lyp", shallow=False)


def test_tier_a_cell_coverage_matches_gdsfactory():
    """Tier A: gpdk wraps exactly the cells gdsfactory registers.

    This guard survives the later stage where core drops @cell from gf.components:
    the plain functions remain in gf.components, and they are what gpdk decorates.
    """
    import gdsfactory as gf
    from gdsfactory.get_factories import get_cells

    core = set(get_cells([gf.components])) | set(get_cells([gf.containers]))
    ours = set(gpdk.PDK.cells)
    assert ours == core


def _is_literal_comparable(value: object) -> bool:
    """True if ``value`` has a meaningful equality beyond identity.

    ``functools.partial`` objects have no custom ``__eq__``, so two independently
    constructed partials with identical func/args/keywords are never ``==``. gpdk's
    generated wrappers necessarily build their own partial instances at gpdk's
    module-load time, distinct objects from whatever core built at its own
    module-load time, even when the wrapper is a completely faithful re-emission.
    Skip default-value comparison for those; everything else compares normally.
    """
    return not isinstance(value, functools.partial)


def _annotation_str(annotation: object) -> str:
    """Normalize an annotation to its ``from __future__ import annotations`` string form.

    Every generated wrapper module uses that future import, so its annotations are
    already plain strings (e.g. ``"float | None"``). Core modules that do *not* use it
    carry live objects (e.g. the class ``float``, or a ``TypeAliasType`` like ``Size``)
    for the same conceptual annotation. ``inspect.formatannotation`` renders a live
    object the same way Python's own future-annotations stringification would; a
    string annotation is already in that form and is returned unchanged.
    """
    import inspect

    return (
        annotation
        if isinstance(annotation, str)
        else inspect.formatannotation(annotation)
    )


def _kind_ok(core_kind: object, wrapper_kind: object) -> bool:
    """Accept the one parameter-kind asymmetry ``functools.partial`` derivation forces.

    Some core cells are themselves registered as ``functools.partial(base, angle=180)``
    (e.g. ``bend_circular180``, ``mzi1x2``, ``grating_coupler_te``). ``inspect.signature``
    on such a partial promotes the bound parameter, and every parameter after it, to
    ``KEYWORD_ONLY`` -- that ``*`` is an artifact of how partials are introspected, not an
    author-written ``*`` in any ``def``. The generated wrapper flattens the partial into a
    plain ``def`` with the bound value as an explicit default, so those parameters come
    back as ``POSITIONAL_OR_KEYWORD``. gpdk is strictly more permissive here (any call
    valid against core is still valid against the wrapper), so this one direction of
    mismatch is accepted; any other kind difference (VAR_POSITIONAL, VAR_KEYWORD,
    POSITIONAL_ONLY, or the reverse direction) is still treated as real drift.
    """
    import inspect

    return core_kind == wrapper_kind or (
        core_kind is inspect.Parameter.KEYWORD_ONLY
        and wrapper_kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
    )


def test_tier_a_signatures_match_gdsfactory():
    """Tier A: each wrapper's signature matches the gdsfactory function it wraps.

    Compared structurally (per-parameter name/kind/annotation, and default only when
    both defaults are literal-comparable) rather than via ``Signature.__eq__``, for two
    reasons, both rooted in ``functools.partial``:

    1. A handful of core cells (e.g. ``add_fiber_array``, ``ring_double_pn``, ``awg``)
       have a parameter whose *default value* is a ``functools.partial`` instance.
       ``functools.partial`` has no custom ``__eq__``, so two independently-constructed
       partial instances with identical func/args/keywords are never ``==``, even though
       the wrapper faithfully re-emits the same partial call.
    2. Some core cells *are themselves* a ``functools.partial`` of a base cell with one
       or more keywords bound (e.g. ``bend_circular180 == partial(bend_circular,
       angle=180)``). ``inspect.signature`` promotes the bound parameter and everything
       after it to ``KEYWORD_ONLY`` for such partials; see ``_kind_ok`` above.

    Annotations are compared via ``_annotation_str`` rather than raw ``!=`` because the
    generated wrapper modules use ``from __future__ import annotations`` (annotations are
    plain strings) while some core modules do not (annotations are live objects); the two
    representations must be normalized before comparison or every parameter would report
    as a false mismatch.

    This still catches real drift: added/removed/renamed/reordered params, wrong
    annotation, wrong literal default, or any parameter-kind change other than the one
    partial-derived asymmetry called out above.
    """
    import inspect

    import gdsfactory as gf
    from gdsfactory.get_factories import get_cells

    core = {**get_cells([gf.components]), **get_cells([gf.containers])}
    mismatched = []
    for name, func in core.items():
        core_params = list(inspect.signature(func).parameters.values())
        wrapper_params = list(
            inspect.signature(gpdk.PDK.cells[name]).parameters.values()
        )
        if len(core_params) != len(wrapper_params):
            mismatched.append(name)
            continue
        for core_param, wrapper_param in zip(core_params, wrapper_params):
            if core_param.name != wrapper_param.name:
                mismatched.append(name)
                break
            if not _kind_ok(core_param.kind, wrapper_param.kind):
                mismatched.append(name)
                break
            if _annotation_str(core_param.annotation) != _annotation_str(
                wrapper_param.annotation
            ):
                mismatched.append(name)
                break
            if (
                _is_literal_comparable(core_param.default)
                and _is_literal_comparable(wrapper_param.default)
                and core_param.default != wrapper_param.default
            ):
                mismatched.append(name)
                break
    assert not mismatched
