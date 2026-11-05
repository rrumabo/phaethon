# Phaethon: Cyprus Grid Frequency Stability & Control Simulation

This repository contains a single-bus isolated power system simulation modeled after the electrical grid of Cyprus. It analyzes the risk of cascading distributed photovoltaic (PV) disconnections following a severe generation contingency (unit trip) and evaluates structural mitigation strategies through Grid-Forming (GFM) and Grid-Following (GFL) Battery Energy Storage Systems (BESS).

## Control Architecture & The Power of Coordination

The primary objective of this framework is to demonstrate that grid stability under high renewable penetration is fundamentally a **control problem**, not merely a capacity issue. 

When a large conventional generator trips in an unbuffered, low-inertia grid:
1. Frequency decays violently (**High RoCoF**), threatening immediate system collapse.
2. Sensitive **Legacy PV Inverters** trip rapidly within milliseconds, expanding the power deficit.
3. Traditional **Grid-Following (GFL) Private BESS** are too slow, blinded by communication delays and Phase-Locked Loop (PLL) filtering during the transient sub-second window.

This project implements a multi-tier control defense scheme to arrest the decline and coordinate different grid assets:

- **First Line of Defense (Grid-Forming BESS):** Simulates a fast-acting 120 MW GFM facility (modeled after the upcoming Cyprus TSO installation). It provides instantaneous virtual inertia and fast frequency response (droop control) directly into the swing equation, breaking the initial steep RoCoF.
- **Advanced Second Line of Defense (Fast Frequency Response - FFR Control):** Equips the 150 MW private/commercial GFL BESS fleet with an intelligent RoCoF trigger. If the controller detects an extreme derivative (|RoCoF| ≥ 1.0 Hz/s) in the first 50ms, it bypasses its native 200ms telemetry delay and activates a high-gain Proportional-Integral (PI) FFR loop to inject massive stabilization power.
- **Inverter Ride-Through Logic (Trip Timers):** Rather than modeling immediate block disconnections on instant threshold breaches, the simulation replicates physical hardware filtering. Legacy blocks trip inside a tight 50ms window, while Modern units leverage Fault Ride-Through (FRT) delay profiles (200ms), remaining online if the GFM/FFR control action successfully recovers the grid frequency during the transient state.

## Repository Structure

```text
phaethon/
│
├── src/
│   └── pv_cascade.py        # System swing equation, RK4 solver, and multi-tier controls
│
├── experiments/
│   └── run_cascade.py       # Sensitivity sweep and dynamic multi-plot execution script
│
├── results/                 # Dynamic performance metrics and comparative charts
│   ├── sweep_results.csv
│   ├── pv_disconnection_comparison.png
│   └── grid_blackout_comparison.png
│
├── config.json              # Operational constants and sweep boundaries
├── requirements.txt
└── README.md
```

## Mathematical Framework & Solvers

The system dynamics are solved using a high-precision **4th-Order Runge-Kutta (RK4) integration method**, tracking continuous state updates across a 0.01-second time step ($dt$). This mathematical resolution avoids the heavy numerical propagation errors of simple Euler approximations, capturing sub-second interactive transients between the primary unit trip, the immediate GFM virtual inertia injection, and fast-acting FFR steps.

## System Configuration (`config.json`)

The setup models a critical Cyprus TSO spring/autumn seasonal operation scenario characterized by high PV generation and minimum conventional base load:
- **Midday System Load:** 650 MW
- **Generation Contingency:** 130 MW (Simulating an instantaneous loss of Vasilikos Unit 5)
- **GFM Utility Asset:** 120 MW
- **Private GFL Fleet Capacity:** 150 MW
- **Renewable Sweep:** Iterative testing across a 200 MW to 500 MW online PV envelope.

## Setup and Execution

To set up your local environment and run the automated multi-scenario sensitivity analysis:

```bash
pip install -r requirements.txt
PYTHONPATH=. python3 -m experiments.run_cascade
```

The execution automatically outputs two discrete validation charts under `results/`:
1. `grid_blackout_comparison.png`: Showcases how the advanced control loop slashes the ultimate grid blackout risk down to 0% across high renewable load zones.
2. `pv_disconnection_comparison.png`: Visualizes the specific stabilization window where coordinated BESS action shields modern FRT inverters, preserving vital bulk generation online.