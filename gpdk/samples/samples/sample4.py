"""Pack."""

import gdsfactory as gf
import numpy as np

from gpdk.cells.shapes import ellipse


@gf.cell
def sample4_pack():
    rng = np.random.default_rng()
    ellipses = [ellipse(radii=tuple(rng.random(2) * n + 2)) for n in range(80)]
    bins = gf.pack(
        ellipses,  # Must be a list or tuple of Components
        spacing=4,  # Minimum distance between adjacent shapes
        aspect_ratio=(1, 1),  # Shape of the box
        max_size=(500, 500),  # Limits the size into which the shapes will be packed
        density=1.05,  # Values closer to 1 pack tighter but require more computation
        sort_by_area=True,  # Pre-sorts the shapes by area
    )
    return bins[0]
