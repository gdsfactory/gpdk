# PEX rules (gfpex)

`gpdk/pex/rules.py` holds the default [gfpex](https://github.com/doplaydo/gf-pex) parasitic-extraction techfile
for gpdk: drawn layers, LVS computed layers, the process stack and the resistance / capacitance tables.
GDS pairs and heights come from `gpdk.layer_map.LAYER` and `gpdk.layer_stack.LAYER_STACK`, so the rules follow the PDK.

```python
from gpdk.pex.rules import DEFAULT_PEX_RULES_CONFIG  # a gfpex.gfpex.Techfile
```

gfpex is an optional, private dependency; `gpdk` itself imports without it.

gfpex is private: installing it needs read access to `doplaydo/gf-pex`, git authenticated for github.com
(for example `gh auth login && gh auth setup-git`) and a Rust toolchain to build it.

## Provenance tags

Every number in `rules.py` carries one of these tags:

| Tag | Meaning |
|-----|---------|
| `FOUNDRY` | stated by a foundry document (none: gpdk is generic) |
| `DERIVED` | computed from PDK values (parallel plate C = 8.854·k/t, Rs = ρ/t, ...) |
| `ASSUMED` | borrowed from the closest open PDK (gf-pex `gfpexconfg/gf180mcuD.py`) or literature |
| `PALACE-FIT` | fitted with gf-pex `benchmarks/palace_benchmark.py` |

Palace-fit values are pending (`TODO(palace)` in `rules.py`); fringe, sidewall and side-overlap values are
gf180mcuD template values or analytic estimates until then.

## Tests

```bash
uv pip install gfpex networkx "kfnetlist @ git+https://github.com/gdsfactory/kfnetlist"  # gfpex is private
make test-pex
```

CI runs the same tests through the manual `Test PEX rules with gfpex` workflow, which needs the `GFPEX_TOKEN` secret.
