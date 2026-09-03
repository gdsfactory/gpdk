"""Technology definitions for the generic PDK."""

from gdsfactory import Pdk
from gdsfactory.gpdk.layer_map import LAYER
from gdsfactory.gpdk.layer_stack import LAYER_STACK

LAYER_VIEWS = None
cross_sections: dict[str, object] = {}
routing_strategies: dict[str, object] = {}
cells: dict[str, object] = {}

PDK = Pdk(
    name="gpdk",
    cells=cells,
    layers=LAYER,
    layer_stack=LAYER_STACK,
    cross_sections=cross_sections,
    routing_strategies=routing_strategies,
    layer_views=LAYER_VIEWS,
)

__all__ = [
    "LAYER",
    "LAYER_STACK",
    "LAYER_VIEWS",
    "cross_sections",
    "routing_strategies",
    "PDK",
]
