"""Pack."""

import gdsfactory as gf

from gpdk.cells.texts import text


@gf.cell
def sample3_grid():
    t1 = text("1")
    t2 = text("2")
    t3 = text("3")
    t4 = text("4")
    t5 = text("5")
    t6 = text("6")

    return gf.grid([t1, t2, t3, t4, t5, t6], shape=(2, 3), spacing=(10, 10))
