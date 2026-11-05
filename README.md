# Phaethon: Cyprus Grid Frequency Stability Simulation

This repository contains a single bus frequency stability model modeled after the isolated electrical grid of Cyprus. It simulates cascading disconnections of distributed photovoltaic (PV) inverters following a generation contingency (unit trip) and evaluates mitigation via Grid-Forming (GFM) Battery Energy Storage Systems (BESS).

## Problem Statement

In isolated island systems like Cyprus, high renewable energy penetration displace traditional synchronous generators, severely lowering system inertia. During high PV generation hours, a large conventional unit trip triggers a steep frequency drop (**High RoCoF**). 

This model tracks how:
1. **Legacy PV Inverters** trip early due to strict over/under-frequency and RoCoF protection settings.
2. The resulting loss of PV power creates a secondary power deficit, accelerating grid collapse.
3. **Under-Frequency Load Shedding (UFLS)** stages deploy to arrest the drop before an all-out blackout occurs (< 47.5 Hz).

The simulation incorporates a **Grid-Forming BESS framework (inspired by the upcoming Cyprus TSO 40MW Athalassa installation)** to demonstrate how fast frequency response stabilizes the system.

## Repository Structure

```text
phaethon/
│
├── src/
│   └── pv_cascade/
│       ├── __init__.py
│       └── model.py         # Frequency swing equation & inverter protections
│
├── experiments/
│   └── run_cascade.py       # Sensitivity sweep comparing 2026 vs 2027 grid setups
│
├── config.json              # Simulation parameters and sweep ranges
├── requirements.txt
└── README.md
```

## Model Assumptions

- **Base Load & Contingency:** Midday system load is set at 1000 MW. A 130 MW generation trip occurs at $t = 1.0$s.
- **Dynamic Inertia:** System inertia ($H$) scales linearly with remaining online conventional generation.
- **PV Fleet Allocation:** Divided into 200 independent blocks.
  - **Legacy Blocks:** Randomly trip between 49.4 Hz and 49.6 Hz, or at RoCoF thresholds between 0.4 and 1.0 Hz/s.
  - **Modern Blocks:** Fault Ride-Through (FRT) enabled, remaining connected down to 47.5 Hz and up to 2.0 Hz/s.
- **UFLS Blocks:** Four load-shedding stages (10% system load each) triggered at 49.0, 48.7, 48.4, and 48.1 Hz.
- **GFM Battery:** A 40 MW grid-forming injector using droop control with a sub-second response time.

## Setup and Running

Install dependencies:
```bash
pip install -r requirements.txt
```

Run the sensitivity sweep:
```bash
PYTHONPATH=. python3 -m experiments.run_cascade
```

The script runs two distinct scenarios:
1. **2026 Grid Case (Without Battery):** The current unbuffered state of the Cyprus grid.
2. **2027 Grid Case (With GFM Battery):** The upcoming grid reinforcement featuring the 40 MW BESS infrastructure.

Outputs are saved as raw numbers in `results/sweep_results.csv` and visualized in `results/cascade_comparison.png`.