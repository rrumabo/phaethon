# cy-pv-trip-cascade

**Question.** When a large unit trips at a sunny hour, how many distributed PV inverters disconnect because of their own protection settings, and when does that turn one trip into a system wide collapse?

**Why Cyprus and why now.** In the 2025 Iberian blackout, renewable plants disconnected below their required thresholds and more than 2.5 GW was lost in about 50 seconds ([pv magazine on the ENTSO-E report](https://www.pv-magazine.com/2026/03/23/entso-e-report-finds-systemic-failures-behind-2025-iberian-blackout/)). In South Australia in 2016, nine wind farms tripped on repeated voltage dips and the state went dark. A 2017 study of the Cyprus grid found a 2030 case where a cascade started from small PV systems tripping ([JRC workshop](https://smart-networks-energy-transition.ec.europa.eu/sites/default/files/documents/events/regional_workshops/south-eastern_region/Grid-Integration-of-Variable-RES-in-Cyprus-Chondrogiannis.pdf)).

**What is already funded.** KIOS's INVERGE works on a single inverter that supports the grid during faults. The **aggregate** question — thousands of inverters with mixed settings, coupled through frequency — was not found in any active Cyprus project. This is the least-covered of the five ideas.

## Model

```
unit trips -> frequency falls -> legacy PV trips -> bigger loss -> faster fall -> more PV trips
```

- One-bus frequency model with governors and four load-shedding stages (10% of load each at 49.0, 48.7, 48.4, 48.1 Hz).
- 1,000 MW midday load; a 130 MW unit trips. More PV online means fewer synchronous units, so less inertia.
- PV split into 200 blocks. **Legacy** blocks trip near 49.5 Hz or at a rate of change of frequency (RoCoF) between 0.4 and 1.0 Hz/s. **Modern** blocks ride through to 47.5 Hz and 2 Hz/s.
- Collapse: frequency below 47.5 Hz. Every value is an assumption, not a measured Cyprus setting.

## First results (5 seeds per cell, `python -m experiments.run_cascade`)

PV that tripped (MW) after a 130 MW unit trip:

| Legacy share \\ PV online | 300 MW | 400 MW | 450 MW | 500 MW | 600 MW |
| --- | --- | --- | --- | --- | --- |
| 0% | 0 | 0 | 0 | 0 | 0 |
| 10% | 26 | 35 | 39 | 44 | **266** |
| 20% | 52 | 70 | 79 | **331** | **600** |
| 30% | 83 | **164** | **450** | **500** | **600** |

Collapse (frequency below 47.5 Hz) in all runs at 500 MW PV or more once the legacy share reaches 20%, and in 40% of runs at 600 MW PV with only 10% legacy.

1. **The response is not gradual.** Below a threshold, only the legacy share trips. Above it, the whole PV fleet trips, modern units included: the legacy trips make frequency fall faster than the modern units' 2 Hz/s ride-through. The jump from 97 MW to 450 MW tripped across 350 to 450 MW of PV (30% legacy) has the shape of a bifurcation.
2. **The threshold moves with two things a regulator can set:** how much PV is allowed online at once, and how many inverters still have legacy settings. At 20% legacy, about 500 MW of PV is the edge; with no legacy units, nothing cascades in this model.
3. **Load shedding saves some cases, not all.** At 450 MW PV and 30% legacy, all PV trips but shedding holds frequency above 47.5 Hz; at 500 MW it does not.

**Verdict so far.** "A single unit trip can cascade through distributed PV in an isolated grid" — survives in this model. "Retrofitting legacy settings removes it" — survives in this model, which is the Iberia and South Australia lesson. Both rest on assumed settings: the real share of legacy inverters in Cyprus is the number that decides it.

## What would kill these results

- The real Cyprus inverter fleet may have few legacy settings; the national connection rules and their dates decide this.
- One bus: no voltage dips, which in reality trip inverters near the fault first (South Australia's mechanism).
- Modern ride-through set at 2 Hz/s; a higher real limit would stop the cascade earlier.

## Next steps

1. Find the Cyprus inverter rules by year of installation (DSO connection requirements) and estimate the legacy share.
2. Add a voltage-dip trigger by location (needs a network model; PowerFactory).
3. Add the grid-forming battery from `cy-gfm-inertia` and test whether 40 MW moves the threshold.
4. Write the mean-field version: tripped share x = F(frequency(x)); its fixed points and saddle-node give the threshold analytically.

## Layout

```
src/pv_cascade/model.py         frequency model with PV protection and load shedding
experiments/run_cascade.py      PV x legacy-share sweep, writes results/
explanations/                   plain-language walkthrough of every code file
```

Run from the repo root: `pip install -r requirements.txt` then `python -m experiments.run_cascade` (about a minute).
