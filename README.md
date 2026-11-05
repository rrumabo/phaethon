# Phaethon: Multi-Node Cyprus Grid Stability & Control Simulation

This repository contains a 5-node isolated power system simulation modeled after the transmission network of Cyprus. It analyzes the risk of cascading distributed photovoltaic (PV) disconnections following a severe generation contingency (unit trip) and evaluates structural mitigation strategies through Grid-Forming (GFM) BESS, Grid-Following (GFL) BESS, and Synchronous Condensers.

## Transmission Network & Grid Layout

The framework moves beyond single-bus approximations, separating the Cyprus 132/220 kV grid into 5 distinct geographical nodes based on real-world load centers and generation hubs:

1. **Node 0: Vasilikos (South) -** The primary conventional generation center. This node hosts the 130 MW contingency trip (Vasilikos Unit 5).
2. **Node 1: Limassol (South-West) -** A heavy industrial and commercial load center.
3. **Node 2: Athalassa (Center/Nicosia) -** The main residential load center, hosting the utility-scale 120 MW Grid-Forming BESS defense.
4. **Node 3: Dhekelia (East/Larnaca) -** Secondary generation hub, hosting the 30 MVar Synchronous Condenser for physical inertia injection.
5. **Node 4: Paphos (West) -** High distributed PV penetration area, hosting the commercial Grid-Following BESS fleet.

All nodes are interconnected through transmission line power flows modeled via real-world synchronizing power coefficients (\(K_{ij}\)).

## Coordinated Defense Architecture

This project evaluates the multi-tier defense scheme currently deployed or planned by Cyprus power authorities (TSO-Cyprus, CERA, and EAC):

- **Physical Inertia Base (Synchronous Condenser):** Replicates the retrofitting of legacy thermal units at Dhekelia. It provides instantaneous physical spinning mass inertia (\(H_{sc} = 1.5\)) to damp the sub-second spatial RoCoF wavefront shocks before power electronics can react.
- **Digital Virtual Inertia (Grid-Forming VSM BESS):** A 120 MW centralized asset at Athalassa emulating a rotating machine mass via Virtual Synchronous Machine (VSM) loops.
- **Fast Frequency Response (Grid-Following Fleet):** A 150 MW private commercial battery array at Paphos utilizing an automated RoCoF derivative trigger (|RoCoF| ≥ 1.0 Hz/s) to bypass native telemetry and phase-locked loop (PLL) tracking latencies.
- **Inverter Fault Ride-Through (FRT):** Models physical inverter protections (20% Legacy with 50 ms trip thresholds vs 80% Modern with 200 ms FRT timers).

## Repository Layout

```text
phaethon/
│
├── src/
│   └── pv_cascade.py        # 5-node swing equations, power flows, and BESS/SC controls
│
├── experiments/
│   └── run_cascade.py       # Automated 3-scenario sensitivity sweep execution script
│
├── results/                 # Output performance metrics and comparative charts
│   ├── sweep_results.csv
│   ├── pv_disconnection_comparison.png
│   └── grid_blackout_comparison.png
│
├── config.json              # Operational variables (TSO-Cyprus 650 MW Spring/Autumn layout)
├── requirements.txt
└── README.md
```

## Mathematical Implementation

The multi-node differential state equations are solved simultaneously using a 4th-Order Runge-Kutta (RK4) integration solver operating at an explicit time step of $dt = 0.01$ seconds. This prevents numerical propagation and truncation errors, accurately capturing the interaction between network power flows, localized breaker timers, and sub-second battery control loops.

## Execution and Validation

To set up the local environment and run the automated multi-scenario sweep:

```bash
pip install -r requirements.txt
PYTHONPATH=. python3 -m experiments.run_cascade
```

The script automatically executes and compares **3 distinct scenarios**:
1. **2026 Baseline:** High PV penetration without storage arrays or synchronous condensers.
2. **2027 GFM Only:** Digital storage protection assets online, but without the Dhekelia spinning mass.
3. **2027 Complete Defense:** Coordinated configuration integrating both the GFM/GFL BESS fleet and the active Synchronous Condenser.

Outputs are compiled into `results/` showcasing how physical inertia and coordinated fast frequency responses drop structural system blackout risk to 0% across high renewable operational envelopes.