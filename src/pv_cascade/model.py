"""Can distributed PV tripping turn a single unit loss into a cascade?

A unit trips -> frequency falls -> PV inverters whose protection settings are
tight disconnect -> more power is lost -> frequency falls further -> more trip.

Frequency: one-bus swing equation with governors (same form as cy-gfm-inertia).
PV: split into K equal blocks; each block has its own trip settings:
  - legacy blocks: under-frequency trip near 49.5 Hz and a RoCoF trip drawn
    between 0.4 and 1.0 Hz/s (old protection settings);
  - modern blocks: ride through to 47.5 Hz and 2 Hz/s.
A tripped block stays off for the rest of the event.
Under-frequency load shedding (UFLS) disconnects 10% of load at each of four
assumed stages (49.0, 48.7, 48.4, 48.1 Hz) to arrest the fall.

More PV online also means fewer synchronous units, so less inertia.
All values are assumptions, not measured Cyprus settings.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

F0 = 50.0


@dataclass
class Case:
    load_mw: float = 1000.0         # midday demand
    pv_mw: float = 400.0            # distributed PV output at the moment of the event
    legacy_share: float = 0.3       # share of PV with legacy (tight) protection
    initial_loss_mw: float = 130.0  # the unit that trips first
    must_run_mw: float = 450.0      # conventional output never goes below this
    power_factor: float = 0.8       # MW per MVA of synchronous plant online
    h_s: float = 4.0
    r_gov: float = 0.05
    t_gov_s: float = 6.0
    d_load_pu: float = 1.0          # load damping: 1% load drop per 1% frequency drop
    rocof_window_s: float = 0.2     # protection measures RoCoF over this window
    blocks: int = 200
    # under-frequency load shedding: (threshold Hz, share of load shed), assumed stages
    ufls: tuple = ((49.0, 0.10), (48.7, 0.10), (48.4, 0.10), (48.1, 0.10))


def sync_mva(c: Case) -> float:
    """Synchronous MVA online: conventional output (at least must-run) / power factor."""
    return max(c.load_mw - c.pv_mw, c.must_run_mw) / c.power_factor


def trip_settings(c: Case, seed: int) -> tuple[np.ndarray, np.ndarray]:
    """Per-block under-frequency (Hz) and RoCoF (Hz/s) trip thresholds."""
    rng = np.random.default_rng(seed)
    legacy = rng.random(c.blocks) < c.legacy_share
    f_trip = np.where(legacy, rng.normal(49.5, 0.05, c.blocks), 47.5)
    rocof_trip = np.where(legacy, rng.uniform(0.4, 1.0, c.blocks), 2.0)
    return f_trip, rocof_trip


def simulate(c: Case, seed: int = 0, t_end: float = 15.0, dt: float = 1e-3) -> dict:
    """Integrate the event; return frequency trace, PV tripped over time, and summary."""
    f_trip, rocof_trip = trip_settings(c, seed)
    block_mw = c.pv_mw / c.blocks
    on = np.ones(c.blocks, dtype=bool)
    s = sync_mva(c)
    m = 2 * c.h_s * s
    d = c.d_load_pu * c.load_mw
    w = pm = 0.0
    n, lag = int(t_end / dt), int(c.rocof_window_s / dt)
    f = np.empty(n)
    tripped_mw = np.empty(n)
    stage_done = [False] * len(c.ufls)
    shed_mw = 0.0
    for k in range(n):
        f_hz = F0 * (1 + w)
        f[k] = f_hz
        if k >= lag:
            rocof = (f[k] - f[k - lag]) / c.rocof_window_s
            trip_now = on & ((f_hz < f_trip) | (-rocof > rocof_trip))
            on &= ~trip_now
        for i, (thr, share) in enumerate(c.ufls):
            if not stage_done[i] and f_hz < thr:
                stage_done[i] = True
                shed_mw += share * c.load_mw
        pv_lost = (c.blocks - on.sum()) * block_mw
        tripped_mw[k] = pv_lost
        loss = c.initial_loss_mw + pv_lost - shed_mw
        dw = (pm - d * w - loss) / m
        pm += dt * (-pm - (s / c.r_gov) * w) / c.t_gov_s
        w += dt * dw
    return {"t": np.arange(n) * dt, "f": f, "pv_tripped_mw": tripped_mw,
            "nadir_hz": float(f.min()), "pv_tripped_final_mw": float(tripped_mw[-1]),
            "cascade_multiplier": float((c.initial_loss_mw + tripped_mw[-1]) / c.initial_loss_mw),
            "load_shed_mw": float(shed_mw), "sync_mva": s}
