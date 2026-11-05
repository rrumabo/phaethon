import os
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from src.pv_cascade import run_simulation

def main():
    print("Starting Cyprus 3-Scenario Architecture Simulation (Phaethon)...")
    
    config_path = "config.json"
    with open(config_path, "r") as f:
        cfg = json.load(f)
        
    pv_online_range = list(range(cfg["pv_online_min_mw"], cfg["pv_online_max_mw"] + 1, cfg["pv_online_step_mw"]))
    legacy_share_range = cfg["legacy_shares"]
    seeds = list(range(1, cfg["num_seeds"] + 1))
    
    os.makedirs("results", exist_ok=True)
    results = []
    
    scenarios = [
        {"name": "2026 Baseline (No BESS / No SC)", "gfm": False, "sc": False},
        {"name": "2027 GFM Only (No SC)", "gfm": True, "sc": False},
        {"name": "2027 Complete Defense (GFM + SC)", "gfm": True, "sc": True}
    ]
    
    for sc in scenarios:
        print(f"Running scenario: {sc['name']}")
        for pv in pv_online_range:
            for legacy in legacy_share_range:
                tripped_mws = []
                collapses = 0
                
                for seed in seeds:
                    sim = run_simulation(
                        pv_online_mw=pv,
                        legacy_share=legacy,
                        trip_mw=cfg["trip_mw"],
                        system_load_mw=cfg["system_load_mw"],
                        gfm_capacity_mw=cfg["gfm_capacity_mw"],
                        gfm_enabled=sc["gfm"],
                        sc_enabled=sc["sc"],
                        seed=seed
                    )
                    tripped_mws.append(sim['tripped_mw'])
                    if sim['collapsed']:
                        collapses += 1
                
                mean_tripped = np.mean(tripped_mws)
                collapse_rate = (collapses / len(seeds)) * 100
                
                results.append({
                    'Scenario': sc['name'],
                    'PV_Online_MW': pv,
                    'Legacy_Share': legacy,
                    'Mean_Tripped_MW': mean_tripped,
                    'Collapse_Rate_Pct': collapse_rate
                })
                
    df = pd.DataFrame(results)
    df.to_csv("results/sweep_results.csv", index=False)
    
    legacy_test = 0.2
    df_base = df[(df['Scenario'] == "2026 Baseline (No BESS / No SC)") & (df['Legacy_Share'] == legacy_test)]
    df_gfm = df[(df['Scenario'] == "2027 GFM Only (No SC)") & (df['Legacy_Share'] == legacy_test)]
    df_comp = df[(df['Scenario'] == "2027 Complete Defense (GFM + SC)") & (df['Legacy_Share'] == legacy_test)]
    
    # --- PLOT 1: PV Disconnection ---
    plt.figure(figsize=(10, 5))
    plt.plot(df_base['PV_Online_MW'], df_base['Mean_Tripped_MW'], 'r-o', label='2026 Baseline (No BESS/SC)', linewidth=2)
    plt.plot(df_gfm['PV_Online_MW'], df_gfm['Mean_Tripped_MW'], 'b-x', label='2027 GFM Only (No SC)', linewidth=2)
    plt.plot(df_comp['PV_Online_MW'], df_comp['Mean_Tripped_MW'], 'g-s', label='2027 Complete Defense (GFM+SC)', linewidth=2)
    plt.title(f"PV Cascade Disconnection (Legacy Share: {int(legacy_test*100)}%)", fontsize=12)
    plt.xlabel("Total Online PV Generation (MW)", fontsize=10)
    plt.ylabel("Mean Disconnected PV Power (MW)", fontsize=10)
    plt.grid(True, linestyle='--', alpha=0.5)
    plt.legend(fontsize=10)
    plt.savefig("results/pv_disconnection_comparison.png", dpi=300, bbox_inches='tight')
    plt.close()
    
    # --- PLOT 2: Grid Collapse Rate ---
    plt.figure(figsize=(10, 5))
    plt.plot(df_base['PV_Online_MW'], df_base['Collapse_Rate_Pct'], 'r-o', label='2026 Baseline (No BESS/SC)', linewidth=2)
    plt.plot(df_gfm['PV_Online_MW'], df_gfm['Collapse_Rate_Pct'], 'b-x', label='2027 GFM Only (No SC)', linewidth=2)
    plt.plot(df_comp['PV_Online_MW'], df_comp['Collapse_Rate_Pct'], 'g-s', label='2027 Complete Defense (GFM+SC)', linewidth=2)
    plt.title(f"Grid Blackout Risk Analysis (Legacy Share: {int(legacy_test*100)}%)", fontsize=12)
    plt.xlabel("Total Online PV Generation (MW)", fontsize=10)
    plt.ylabel("Grid Collapse Rate (%)", fontsize=10)
    plt.grid(True, linestyle='--', alpha=0.5)
    plt.legend(fontsize=10)
    plt.savefig("results/grid_blackout_comparison.png", dpi=300, bbox_inches='tight')
    plt.close()
    
    print("3-Scenario simulation successful. Plots saved in results/ folder.")

if __name__ == "__main__":
    main()