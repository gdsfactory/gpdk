"""Write one markdown page per PDK cell for the docs site."""

from __future__ import annotations

import pathlib

import gpdk

OUT = pathlib.Path(__file__).parent.parent / "docs" / "cells.md"


def main() -> None:
    """Render the cell reference page."""
    gpdk.PDK.activate()
    lines = ["# Cells\n"]
    for name in sorted(gpdk.PDK.cells):
        lines.append(f"## {name}\n")
        lines.append(f"::: gpdk.cells.{name}\n")
    OUT.parent.mkdir(exist_ok=True, parents=True)
    OUT.write_text("\n".join(lines))
    print(f"wrote {OUT} with {len(gpdk.PDK.cells)} cells")


if __name__ == "__main__":
    main()
