# Hand-written electrical cells live inside the generated cells/ package

gpdk's `cells/` package is otherwise generated from gdsfactory core by `.github/generate_cells.py`, and the drift tests required gpdk to equal core exactly. To demonstrate electronic-photonic tooling we added cells core does not have: `nch`, `pch`, `cmim`, `cmom`, `res_poly`, `res_metal` and `straight_pn_ribbed`. They are faithful ports of gf180mcu, IHP SG13G2 and 45spclo cells. We added them as hand-written modules inside `gpdk/cells/` (`mos.py`, `capacitor.py`, `resistor.py`, `modulator.py`). The generator re-exports them from `__init__.py` through its `HAND_WRITTEN` allow-list but never writes or checks them. The drift guards were relaxed from "gpdk == core" to "core ⊆ gpdk, unchanged". The same applies to layers and stack levels: the new devices need layers such as ACTIVE, POLY, NWELL, MIM and the resistor markers, and stack levels for them and for the doping layers.

## Consequences

- If core later adds a cell with one of these names, the tier-A signature test fails for that name. Fix it by renaming the hand-written cell.
- The drift guards still catch a core layer, stack level or view that gpdk changes or drops. They no longer catch something gpdk adds.
