"""Closed-form cascade threshold, checked against the simulation.
 
Two conditions decide whether one unit trip collapses the grid:
 
  1. CASCADE: after the unit and the legacy PV trip, frequency falls faster
     than the modern inverters' RoCoF ride-through, so the modern PV trips too.
         l* = (2 H S r_m / f0 - dP) / PV
     l = legacy share, S = synchronous MVA online, r_m = modern RoCoF limit,
     dP = the first unit lost, PV = PV online. Cascade when l > l*.
 
  2. COLLAPSE: once all PV is lost, load shedding cannot hold frequency
     above 47.5 Hz. This happens when PV online exceeds a level P_c, found
     here by simulating the loss of the unit plus all PV at once.
 
Collapse = condition 1 AND condition 2.
 
Run from the repo root:  python -m experiments.run_threshold
Writes results/threshold.csv and results/threshold_map.png
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
 
import pv_cascade.model as model  # noqa: E402
from pv_cascade import Case, simulate, sync_mva  # noqa: E402
 
OUT = ROOT / "results"
OUT.mkdir(exist_ok=True)

F0 = 50.0  # nominal frequency
MODERN_ROCOF = 2.0      # Hz/s, modern ride-through
COLLAPSE_HZ = 47.5
SEEDS = 4
PV = list(range(300, 701, 25))
LEGACY = list(np.round(np.arange(0.0, 0.71, 0.02), 2))

# --------------------------------------------------------------------------------------------
# 1. Formula for the legacy share that will just push RoCoF to the modern limit.
# ---------------------------------------------------------------------------------------

def predicted_legacy_limit(c: Case, pv: float, modern_rocof: float = MODERN_ROCOF) -> float:
    """Largest legacy share that does NOT push RoCoF past the modern limit."""
    s = sync_mva(replace(c, pv_mw=pv))
    tolerable_loss = 2 * c.h_s * s * modern_rocof / F0   # MW that gives exactly r_m
    return (tolerable_loss - c.initial_loss_mw) / pv

# --------------------------------------------------------------------------------------------
# 2. The PV level above which a full cascade cannot be arrested
# ---------------------------------------------------------------------------------------

def nadir_after_full_loss(c: Case, pv: float) -> float:
    """Nadir when the unit and ALL PV are lost at t = 0 (PV blocks then cannot trip again)."""
    original = model.trip_settings
    model.trip_settings = lambda case, seed: (np.zeros(case.blocks), np.full(case.blocks, np.inf))
    try:
        r = simulate(replace(c, pv_mw=pv, initial_loss_mw=c.initial_loss_mw + pv), t_end=6.0)
    finally:
        model.trip_settings = original
    return r["nadir_hz"]
 
 
def collapse_pv_level(c: Case, lo: float = 200.0, hi: float = 800.0) -> float:
    """Bisection: smallest PV whose full loss drives the nadir below 47.5 Hz."""
    for _ in range(30):
        mid = 0.5 * (lo + hi)
        if nadir_after_full_loss(c, mid) < COLLAPSE_HZ:
            hi = mid
        else:
            lo = mid
    return hi

# ---------------------------------------------------------------------------
# 3. The simulation sweep
# ---------------------------------------------------------------------------
 
def sweep(c: Case) -> pd.DataFrame:
    rows = []
    for pv in PV:
        for leg in LEGACY:
            for seed in range(SEEDS):
                r = simulate(replace(c, pv_mw=float(pv), legacy_share=float(leg)), seed=seed, t_end=4.0)
                modern_mw = (1 - leg) * pv
                cascade = r["pv_tripped_final_mw"] > leg * pv + 0.5 * modern_mw
                rows.append({"pv_mw": pv, "legacy_share": leg, "seed": seed,
                             "cascade": cascade, "collapse": r["nadir_hz"] < COLLAPSE_HZ})
    return pd.DataFrame(rows).drop(columns="seed").groupby(["pv_mw", "legacy_share"]).mean().reset_index()
 
 
def first_share_where(g: pd.DataFrame, column: str) -> float | None:
    hit = g[g[column] >= 0.5]
    return float(hit["legacy_share"].min()) if len(hit) else None
 
 
# ---------------------------------------------------------------------------
# 4. Run, compare, plot
# ---------------------------------------------------------------------------
 
def main() -> None:
    c = Case()
    p_c = collapse_pv_level(c)
    mean = sweep(c)
 
    rows = []
    for pv, g in mean.groupby("pv_mw"):
        rows.append({"pv_mw": pv,
                     "predicted_legacy_limit": round(predicted_legacy_limit(c, pv), 3),
                     "simulated_cascade_share": first_share_where(g, "cascade"),
                     "simulated_collapse_share": first_share_where(g, "collapse"),
                     "predicted_collapse": pv > p_c})
    table = pd.DataFrame(rows)
    table.to_csv(OUT / "threshold.csv", index=False)
 
    pd.set_option("display.width", 200)
    print(f"P_c (PV above which a full cascade cannot be arrested): {p_c:.0f} MW\n")
    print(table.to_string(index=False))
 
    grid = mean.pivot(index="legacy_share", columns="pv_mw", values="collapse")
    fig, ax = plt.subplots(figsize=(8, 4.5))
    im = ax.imshow(grid.values, origin="lower", aspect="auto", cmap="Reds", vmin=0, vmax=1,
                   extent=[PV[0] - 12.5, PV[-1] + 12.5, LEGACY[0] - 0.01, LEGACY[-1] + 0.01])
    fig.colorbar(im, label="share of runs that collapse")
    pv_line = np.linspace(PV[0], PV[-1], 200)
    ax.plot(pv_line, [predicted_legacy_limit(c, p) for p in pv_line], "k-", lw=2,
            label="formula: cascade above this line")
    ax.axvline(p_c, color="k", ls="--", lw=1.5, label=f"P_c = {p_c:.0f} MW: collapse right of this line")
    ax.set_ylim(LEGACY[0], LEGACY[-1])
    ax.set_xlabel("distributed PV online at the moment of the trip (MW)")
    ax.set_ylabel("share of PV with legacy protection")
    ax.legend(loc="upper right", fontsize=8)
    fig.tight_layout()
    fig.savefig(OUT / "threshold_map.png", dpi=150)
    print("\nWrote results/threshold.csv and results/threshold_map.png")
 
 
if __name__ == "__main__":
    main()