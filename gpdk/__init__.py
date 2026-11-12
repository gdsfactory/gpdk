"""Generic PDK for gdsfactory."""

from functools import lru_cache

from gdsfactory.get_factories import get_cells
from gdsfactory.pdk import Pdk

from gpdk import (
    _schematic,  # noqa: F401  # registers cell metadata annotations
    cells,
    config,
    models,
    tech,
)
from gpdk.config import PATH
from gpdk.models import get_models
from gpdk.simulation_settings import materials_index
from gpdk.tech import (
    LAYER,
    LAYER_CONNECTIVITY,
    LAYER_STACK,
    LAYER_VIEWS,
    GenericConstants,
    cross_sections,
    layer_transitions,
    routing_strategies,
)

__version__ = "0.0.1"

_cells = get_cells([cells])
_containers = get_cells([cells.containers])
_cells = {name: cell for name, cell in _cells.items() if name not in _containers}


@lru_cache
def get_pdk() -> Pdk:
    """Return the generic PDK."""
    return Pdk(
        name="gpdk",
        version=__version__,
        cells=_cells,
        containers=_containers,
        cross_sections=cross_sections,
        layers=LAYER,
        layer_stack=LAYER_STACK,
        layer_views=LAYER_VIEWS,
        layer_transitions=layer_transitions,
        materials_index=materials_index,
        constants=GenericConstants(),
        connectivity=LAYER_CONNECTIVITY,
        routing_strategies=routing_strategies,
        models=get_models(),
    )


def activate_pdk() -> None:
    """Activate the generic PDK."""
    get_pdk().activate()


PDK = get_pdk()

__all__ = [
    "LAYER",
    "LAYER_STACK",
    "LAYER_VIEWS",
    "PATH",
    "PDK",
    "activate_pdk",
    "cells",
    "config",
    "get_pdk",
    "models",
    "tech",
]
