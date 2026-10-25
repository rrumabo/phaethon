# Companion: `src/pv_cascade/model.py`

## The docstring

The loop being tested: a unit trips, frequency falls, inverters with tight settings disconnect, the loss grows, frequency falls faster, more disconnect. Load shedding is the grid's last defence.

## `Case`

The assumed situation: 1,000 MW of load, the PV output at that moment, the share of PV with old (tight) protection, the 130 MW unit that trips, a 450 MW must-run floor for conventional plants, 0.8 MW per MVA of synchronous plant, the same governor values as `cy-gfm-inertia`, load that drops 1% per 1% of frequency, a 0.2 s window for measuring RoCoF, 200 PV blocks, and four load-shedding stages.

## `sync_mva`

Conventional plants cover what PV does not, but never less than the must-run floor. Dividing by 0.8 turns MW into MVA of spinning plant. More PV, less spinning plant, less inertia.

## `trip_settings`

For each of the 200 blocks, decide at random whether it is legacy (with probability `legacy_share`).
- Legacy: trips below about 49.5 Hz (a little spread around it), or if frequency falls faster than a random limit between 0.4 and 1.0 Hz/s.
- Modern: trips below 47.5 Hz or faster than 2 Hz/s.

## `simulate`

1 ms steps for 15 s.

- `block_mw`: each block's share of PV. `on`: which blocks are still connected.
- `m`: system inertia. `d`: how much load drops per unit of frequency.
- Each step:
  1. Record frequency.
  2. After the first 0.2 s, measure RoCoF over the last 0.2 s. Any connected block whose frequency or RoCoF limit is crossed disconnects and stays off.
  3. Each load-shedding stage fires once when frequency first falls below its threshold, removing 10% of load.
  4. Total loss = the tripped unit + PV that tripped - load shed.
  5. Update governors and frequency (swing equation).
- Returns the traces and a summary: lowest frequency, PV tripped, cascade multiplier (total loss / initial loss), load shed, spinning MVA online.
