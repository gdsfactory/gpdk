"""Scaling benchmark for 3D bundle routing on a 1xN optical switch tree.

Sweeps `noutputs` for `switch_nxn_with_fiber_array`, times the routing pass,
and writes:

  results/benchmark_switch_3d/results.csv
  results/benchmark_switch_3d/npads_vs_time.png
  results/benchmark_switch_3d/switch_{n}.gds  (one per size)

Run:
    python gpdk/samples/benchmark_switch_3d.py --sizes 2,4,8,16,32
"""

from __future__ import annotations

import argparse
import csv
import time
from pathlib import Path

import gdsfactory as gf

import gpdk  # noqa: F401 — PDK activation side-effect


def _run_one(noutputs: int):
    from gpdk.samples.test_1x16_switch import switch_nxn_with_fiber_array

    gf.clear_cache()
    t0 = time.perf_counter()
    c = switch_nxn_with_fiber_array(noutputs=noutputs)
    elapsed = time.perf_counter() - t0

    npads = sum(1 for p in c.ports if p.name.startswith("e"))
    return c, elapsed, npads


def main() -> None:
    gpdk.PDK.activate()
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--sizes",
        default="2,4,8,16,32",
        help="Comma-separated output counts (default: 2,4,8,16,32)",
    )
    parser.add_argument(
        "--outdir",
        default="results/benchmark_switch_3d",
        help="Where to write CSV/PNG/GDS.",
    )
    args = parser.parse_args()

    sizes = [int(s) for s in args.sizes.split(",") if s]
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, float | int | str]] = []
    for n in sizes:
        print(f"\n=== noutputs={n} ===")
        c, elapsed, npads = _run_one(n)
        c.write_gds(str(outdir / f"switch_{n}.gds"), with_metadata=False)
        rows.append({"noutputs": n, "npads": npads, "time_s": round(elapsed, 3)})
        print(f"  npads={npads}  time={elapsed:.2f}s")

    csv_path = outdir / "results.csv"
    with csv_path.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nWrote {csv_path}")

    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(7, 5))
        xs = [r["npads"] for r in rows]
        ax.plot(xs, [r["time_s"] for r in rows], "o-")
        ax.set_xscale("log", base=2)
        ax.set_yscale("log")
        ax.set_xlabel("number of pads (nets routed)")
        ax.set_ylabel("routing time [s]")
        ax.set_title("3D bundle routing scaling — switch_nxn_with_fiber_array")
        ax.grid(True, which="both", alpha=0.3)
        fig.tight_layout()
        png_path = outdir / "npads_vs_time.png"
        fig.savefig(png_path, dpi=150)
        plt.close(fig)
        print(f"Wrote {png_path}")
    except Exception as exc:  # pragma: no cover
        print(f"[WARN] matplotlib plot skipped: {exc}")


if __name__ == "__main__":
    main()
