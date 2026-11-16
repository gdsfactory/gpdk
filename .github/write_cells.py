"""Write the PDK cell reference with rendered layout previews."""

from __future__ import annotations

import inspect
import pathlib
from collections.abc import Callable

import matplotlib

matplotlib.use("Agg")

import gdsfactory as gf
import matplotlib.pyplot as plt

import gpdk

OUT = pathlib.Path(__file__).parent.parent / "docs" / "cells.md"


def write_cell_image(
    cell: Callable[..., gf.Component | gf.ComponentAllAngle], image_path: pathlib.Path
) -> None:
    """Render a cell and its ports without modifying the cached component."""
    # A fresh parent also supports all-angle cells, whose plot() returns no figure.
    component = gf.Component()
    reference = component.create_vinst(cell())
    component.add_ports(reference.ports)
    component.draw_ports()
    figure = component.plot(return_fig=True)
    try:
        figure.savefig(image_path, bbox_inches="tight", pad_inches=0, dpi=80)
    finally:
        plt.close(figure)


def main() -> None:
    """Render the cell reference page."""
    gpdk.PDK.activate()
    image_dir = OUT.parent / "cells_images"
    image_dir.mkdir(exist_ok=True, parents=True)
    for image_path in image_dir.glob("*.png"):
        image_path.unlink()
    lines = ["# Cells\n"]
    for name, cell in sorted(gpdk.PDK.cells.items()):
        lines.append(f"## {name}\n")
        lines.append(f"::: gpdk.cells.{name}\n")
        try:
            inspect.signature(cell).bind()
        except TypeError:
            lines.append("A layout preview requires explicit arguments.\n")
            continue
        print(f"Rendering {name}", flush=True)
        image_path = image_dir / f"{name}.png"
        try:
            write_cell_image(cell, image_path)
        except Exception as error:
            print(f"Could not render {name}: {error}", flush=True)
            image_path.unlink(missing_ok=True)
            lines.append("A layout preview is unavailable for this cell.\n")
            continue
        lines.append(
            f"![Layout of {name}](cells_images/{name}.png){{ loading=lazy }}\n"
        )
    OUT.parent.mkdir(exist_ok=True, parents=True)
    OUT.write_text("\n".join(lines))
    print(f"wrote {OUT} with {len(gpdk.PDK.cells)} cells")


if __name__ == "__main__":
    main()
