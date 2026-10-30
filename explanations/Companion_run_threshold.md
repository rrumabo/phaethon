 # Companion: run_threshold.py in plain language

## The question
`run_cascade.py` found, by brute-force simulation, where one unit trip turns
into a collapse. This script asks whether that boundary can be written down
as a formula, and checks the formula against the simulation.

## The idea in two steps
A collapse needs two things to go wrong, one after the other.

**Step 1: the cascade.** The unit trips. Frequency starts to fall. The legacy
inverters see it first (they trip near 49.5 Hz or at a RoCoF of 0.4 to
1.0 Hz/s), and within about 0.2 s almost all of them are gone. Now the grid
has lost the unit plus the legacy PV. Frequency falls faster. If it falls
faster than 2 Hz/s, the modern inverters' RoCoF limit, they trip too. Then all
the PV is gone.

How fast frequency falls right after a loss is fixed by the swing equation:

    RoCoF = f0 × (power lost) / (2 × H × S)

Here f0 = 50 Hz, H = inertia constant (4 s), and S = synchronous MVA online.
Set RoCoF equal to the modern limit r_m and solve for the power lost. That
gives the largest loss the modern inverters ride through:

    tolerable loss = 2 × H × S × r_m / f0

The loss is the unit (dP = 130 MW) plus the legacy PV (l × PV). So the modern
PV trips when

    dP + l × PV > tolerable loss,  i.e.  l > l* = (2 H S r_m / f0 − dP) / PV

That is the formula.

**Worked example.** PV = 500 MW. Conventional plants then make 1000 − 500 =
500 MW, which is above the 450 MW must-run, so S = 500 / 0.8 = 625 MVA.
Tolerable loss = 2 × 4 × 625 × 2 / 50 = 200 MW. The unit already takes 130 MW,
so the legacy PV may take at most 70 MW: l* = 70 / 500 = 0.14. If more than 14%
of the 500 MW has legacy settings, the whole fleet trips.

**Step 2: can load shedding catch it?** After a full cascade the grid has lost
130 MW + all the PV. Load shedding removes up to 40% of load. If the PV online
is large enough, that is still not enough and frequency goes below 47.5 Hz.
That PV level is P_c. It has no neat formula because load shedding is a
staircase, so the script finds it by simulation.

## Block by block

**Header and imports.** Loads the existing model from `src/pv_cascade`. Sets
the constants: 50 Hz, 2 Hz/s modern limit, 47.5 Hz collapse line, 4 seeds, PV
from 300 to 700 MW in 25 MW steps, legacy share from 0 to 0.7 in 0.02 steps.

**`predicted_legacy_limit(c, pv)`.** The formula. It works out S for this PV
level (using `sync_mva`, which applies the must-run floor), computes the
tolerable loss, takes away the unit, and divides by PV.

**`nadir_after_full_loss(c, pv)`.** Runs the existing simulation with the unit
and all the PV lost at t = 0. To stop the PV from being counted twice, it
temporarily replaces the trip settings with ones that can never fire
(0 Hz and infinite RoCoF), then puts the original back. Returns the lowest
frequency reached.

**`collapse_pv_level(c)`.** Bisection: halves the interval 200 to 800 MW thirty
times, keeping the half where the nadir crosses 47.5 Hz. The answer is P_c.

**`sweep(c)`.** For every PV level, legacy share and seed, runs the real event
(4 s is enough; the nadir comes at about 2 s). Records two things:
- cascade: did more than half of the modern PV trip?
- collapse: did frequency go below 47.5 Hz?
Then averages over the seeds.

**`first_share_where(g, column)`.** For one PV level, the smallest legacy share
at which at least half the runs cascade (or collapse).

**`main()`.** Computes P_c, runs the sweep, and builds the comparison table:
formula against simulation, at every PV level. Saves it to
`results/threshold.csv`. Draws the map: red = share of runs that collapse,
solid line = the formula, dashed line = P_c. Saves `results/threshold_map.png`.

## What it found
- P_c = 451 MW.
- Collapse happens exactly where both conditions hold. Below 451 MW nothing
  collapses at any legacy share (load shedding catches every cascade). Above
  it, the collapse boundary equals the cascade boundary at every PV level.
- The formula sits below the simulated boundary by 0.01 to 0.08 in legacy
  share. It is never above it. So it errs on the safe side: it warns slightly
  early.

| PV (MW) | formula l* | simulated cascade | simulated collapse |
|---|---|---|---|
| 450 | 0.20 | 0.28 | none |
| 500 | 0.14 | 0.18 | 0.18 |
| 550 | 0.09 | 0.12 | 0.12 |
| 600 | 0.08 | 0.10 | 0.10 |
| 700 | 0.07 | 0.08 | 0.08 |

## Why the formula warns early
It uses the RoCoF right at the moment of loss. In the simulation the modern
inverters see the RoCoF a few tenths of a second later, measured over a 0.2 s
window. By then load damping and the governors have started to push back,
so the real fall is a little slower. The gap is largest around 425 to 475 MW,
where S is still changing with PV.

## What it means
The legacy share in Cyprus is not public. The formula turns that unknown into
the output: for each PV level it gives the largest legacy share the grid can
tolerate. Whoever does know the real share (the DSO, the regulator) can read
the answer straight off the line.

It also names every lever, because each one appears in the formula:
- r_m, the modern RoCoF ride-through. Raising it from 2 to 3 Hz/s lifts l* at
  600 MW from 0.08 to 0.23 (simulation: between 0.25 and 0.3).
- S, the synchronous MVA, set by the must-run level. More must-run means more
  inertia and a higher l*.
- dP, the largest unit. A smaller largest unit leaves more room.
- l itself, by retrofitting legacy settings.

## What it does not show
- Every number is still the model's assumption, not a Cyprus measurement.
- One bus. No voltage dips, which trip inverters near a fault first.
- The modern limit is the same 2 Hz/s for every inverter, so the cascade is a
  sharp jump. With a spread of real settings it would be a smoother fold.
- P_c depends on the assumed load-shedding stages.