"""Store paths."""

__all__ = ["PATH"]

import pathlib

module = pathlib.Path(__file__).parent.absolute()
repo = module.parent


class Path:
    """Paths used by the gpdk package."""

    module = module
    repo = repo
    gds = module / "gds"
    klayout = module / "klayout"

    lyp = klayout / "layers.lyp"
    lyt = klayout / "tech.lyt"
    lyp_yaml = module / "layers.yaml"


PATH = Path()
