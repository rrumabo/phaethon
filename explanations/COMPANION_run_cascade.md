# Companion: `experiments/run_cascade.py`

## Settings

5 random seeds (each seed gives a different random assignment of legacy settings), PV from 150 to 700 MW in steps of 50, legacy share from 0% to 60%. `COLLAPSE_HZ = 47.5`: below this even modern inverters disconnect, so the event is treated as a system collapse.

## `sweep`

Every PV level x legacy share x seed: simulate the 130 MW trip and record the lowest frequency, PV tripped, load shed, and whether it collapsed. Saves every run to `results/sweep.csv`, then averages over seeds.

## `critical`

For each PV level, the smallest legacy share at which at least half the runs collapse. Empty if none do. Saved to `results/critical.csv`.

## `plot_map`

A heat map: horizontal = PV online, vertical = legacy share, colour = share of PV that tripped. The sharp edge between dark and bright is the threshold. Saved to `results/cascade_map.png`.

## `plot_event`

500 MW of PV online, legacy share 0%, 20%, 40%: frequency (top) and PV tripped (bottom) over time. Saved to `results/event.png`.

## Main block

Prints the PV-tripped table, the collapse table and the critical shares, then draws both plots.
