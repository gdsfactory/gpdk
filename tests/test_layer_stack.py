"""Tests for the layer stack material tokens."""

from gpdk.layer_stack import get_layer_stack, get_process
from gpdk.simulation_settings import (
    SIMULATION_SETTINGS_LUMERICAL_FDTD,
    materials_index,
)


def test_layer_stack_material_tokens() -> None:
    """Every layer's material token matches gpdk's lowercase convention."""
    layer_stack = get_layer_stack()

    assert {name: level.material for name, level in layer_stack.layers.items()} == {
        "substrate": "si",
        "box": "sio2",
        "core": "si",
        "shallow_etch": "si",
        "deep_etch": "si",
        "clad": "sio2",
        "slab150": "si",
        "slab90": "si",
        "nitride": "sin",
        "ge": "ge",
        "undercut": "air",
        "via_contact": "Aluminum",
        "metal1": "Aluminum",
        "heater": "TiN",
        "via1": "Aluminum",
        "metal2": "Aluminum",
        "via2": "Aluminum",
        "metal3": "Aluminum",
        "active": "si",
        "poly": "si",
        "mim": "TiN",
        "n": "si",
        "p": "si",
        "np": "si",
        "pp": "si",
        "npp": "si",
        "ppp": "si",
        "nwell": "si",
    }


def test_layer_stack_material_tokens_serialize() -> None:
    """Serialized layer stack uses lowercase material tokens."""
    serialized_layers = get_layer_stack().model_dump()["layers"]

    assert serialized_layers["core"]["material"] == "si"
    assert serialized_layers["box"]["material"] == "sio2"
    assert serialized_layers["nitride"]["material"] == "sin"


def test_process_material_tokens() -> None:
    """Process steps use the canonical material tokens."""
    process_materials = {
        step.name: step.material for step in get_process() if hasattr(step, "material")
    }

    assert process_materials == {
        "strip_etch": "silicon",
        "slab_etch": "silicon",
        "viac_metallization": "Aluminum",
        "viac_etch": "Aluminum",
        "deposit_cladding": "Oxide",
    }


def test_material_registries_include_canonical_optical_tokens() -> None:
    """Material registries include the canonical optical tokens."""
    canonical_optical_materials = {"si", "sio2", "sin"}

    assert canonical_optical_materials <= set(materials_index)
    assert canonical_optical_materials <= set(
        SIMULATION_SETTINGS_LUMERICAL_FDTD.material_name_to_lumerical
    )
    assert SIMULATION_SETTINGS_LUMERICAL_FDTD.background_material == "sio2"
