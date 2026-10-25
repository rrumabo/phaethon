"""Sweep PV output x share of legacy protection; find where a 130 MW trip cascades.

Run from the repo root:  python -m experiments.run_cascade
Writes results/sweep.csv, results/critical.csv, results/cascade_map.png, results/event.png
"""
from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pv_cascade import Case, simulate  # noqa: E402

OUT = ROOT / "results"
OUT.mkdir(exist_ok=True)
SEEDS = 5
PV = list(range(150, 701, 50))
LEGACY = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6]
COLLAPSE_HZ = 47.5   # below this even modern inverters trip: treat as system collapse


def sweep() -> pd.DataFrame:
    rows = []
    for pv in PV:
        for leg in LEGACY:
            for seed in range(SEEDS):
                r = simulate(replace(Case(), pv_mw=float(pv), legacy_share=leg), seed=seed)
                rows.append({"pv_mw": pv, "legacy_share": leg, "seed": seed,
                             "nadir_hz": r["nadir_hz"], "pv_tripped_mw": r["pv_tripped_final_mw"],
                             "load_shed_mw": r["load_shed_mw"], "collapse": r["nadir_hz"] < COLLAPSE_HZ})
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "sweep.csv", index=False)
    return df.drop(columns="seed").groupby(["pv_mw", "legacy_share"]).mean().reset_index()


def critical(mean: pd.DataFrame) -> pd.DataFrame:
    """For each PV level, the smallest legacy share at which most runs collapse."""
    rows = []
    for pv, g in mean.groupby("pv_mw"):
        bad = g[g["collapse"] >= 0.5]
        rows.append({"pv_mw": pv, "critical_legacy_share": float(bad["legacy_share"].min()) if len(bad) else None})
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "critical.csv", index=False)
    return df


def plot_map(mean: pd.DataFrame) -> None:
    grid = mean.pivot(index="legacy_share", columns="pv_mw", values="pv_tripped_mw")
    frac = grid.values / np.array(grid.columns, dtype=float)[None, :]
    fig, ax = plt.subplots(figsize=(8, 4))
    im = ax.imshow(frac, origin="lower", aspect="auto", cmap="viridis", vmin=0, vmax=1,
                   extent=[PV[0] - 25, PV[-1] + 25, -0.05, 0.65])
    fig.colorbar(im, label="share of PV that tripped")
    ax.set_xlabel("distributed PV online at the moment of the trip (MW)")
    ax.set_ylabel("share of PV with legacy protection")
    fig.tight_layout()
    fig.savefig(OUT / "cascade_map.png", dpi=140)


def plot_event() -> None:
    fig, ax = plt.subplots(2, 1, figsize=(9, 6), sharex=True)
    for leg in [0.0, 0.2, 0.4]:
        r = simulate(replace(Case(), pv_mw=500.0, legacy_share=leg))
        ax[0].plot(r["t"], r["f"], label=f"legacy share {leg:.0%}")
        ax[1].plot(r["t"], r["pv_tripped_mw"], label=f"legacy share {leg:.0%}")
    ax[0].set_ylabel("frequency (Hz)")
    ax[1].set_ylabel("PV tripped (MW)")
    ax[1].set_xlabel("seconds after the 130 MW trip, 500 MW PV online")
    ax[0].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT / "event.png", dpi=140)


if __name__ == "__main__":
    pd.set_option("display.width", 200)
    mean = sweep()
    table = mean.pivot(index="legacy_share", columns="pv_mw", values="pv_tripped_mw").round(0)
    print(f"PV tripped (MW, mean of {SEEDS} seeds) after a 130 MW unit trip; rows = legacy share, columns = PV online (MW)\n")
    print(table.to_string())
    print("\nCollapse (nadir below 47.5 Hz), share of runs:\n")
    print(mean.pivot(index="legacy_share", columns="pv_mw", values="collapse").round(1).to_string())
    print("\nCritical legacy share by PV level:\n")
    print(critical(mean).to_string(index=False))
    plot_map(mean)
    plot_event()
    print("\nWrote results/sweep.csv, results/critical.csv, results/cascade_map.png, results/event.png")
