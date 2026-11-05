import os
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from src.pv_cascade import run_simulation

def main():
    print("Starting Cyprus Grid Cascade Simulation (Phaethon)...")
    
    config_path = "config.json"
    if not os.path.exists(config_path):
        print(f"Error: {config_path} not found.")
        return
        
    with open(config_path, "r") as f:
        cfg = json.load(f)
        
    pv_online_range = list(range(cfg["pv_online_min_mw"], cfg["pv_online_max_mw"] + 1, cfg["pv_online_step_mw"]))
    legacy_share_range = cfg["legacy_shares"]
    seeds = list(range(1, cfg["num_seeds"] + 1))
    
    os.makedirs("results", exist_ok=True)
    results = []
    
    for gfm_status in [False, True]:
        gfm_label = "Future Grid (2027)" if gfm_status else "Current Grid (2026)"
        print(f"Running scenario: {gfm_label}")
        
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
                        gfm_enabled=gfm_status,
                        seed=seed
                    )
                    tripped_mws.append(sim['tripped_mw'])
                    if sim['collapsed']:
                        collapses += 1
                
                mean_tripped = np.mean(tripped_mws)
                collapse_rate = (collapses / len(seeds)) * 100
                
                print(f"PV: {pv}MW | Legacy: {int(legacy*100)}% | Collapse: {collapse_rate:.0f}%")
                
                results.append({
                    'GFM_Enabled': gfm_status,
                    'PV_Online_MW': pv,
                    'Legacy_Share': legacy,
                    'Mean_Tripped_MW': mean_tripped,
                    'Collapse_Rate_Pct': collapse_rate
                })
                
    df = pd.DataFrame(results)
    df.to_csv("results/sweep_results.csv", index=False)
    
    legacy_test = 0.2
    df_no_gfm = df[(df['GFM_Enabled'] == False) & (df['Legacy_Share'] == legacy_test)]
    df_with_gfm = df[(df['GFM_Enabled'] == True) & (df['Legacy_Share'] == legacy_test)]
    
    # --- PLOT 1: PV Disconnection Power ---
    plt.figure(figsize=(10, 5))
    plt.plot(df_no_gfm['PV_Online_MW'], df_no_gfm['Mean_Tripped_MW'], 'r-o', label='Current Grid (2026 - Without Battery)', linewidth=2)
    plt.plot(df_with_gfm['PV_Online_MW'], df_with_gfm['Mean_Tripped_MW'], 'g-s', label='Future Grid (2027 - With GFM + FFR Control)', linewidth=2)
    plt.title(f"PV Disconnection Cascade (Legacy Share: {int(legacy_test*100)}%)", fontsize=12)
    plt.xlabel("Total Online PV Generation (MW)", fontsize=10)
    plt.ylabel("Mean Disconnected PV Power (MW)", fontsize=10)
    plt.grid(True, linestyle='--', alpha=0.5)
    plt.legend(fontsize=10)
    plt.savefig("results/pv_disconnection_comparison.png", dpi=300, bbox_inches='tight')
    plt.close()
    
    # --- PLOT 2: Grid Collapse Rate (Blackout Risk) ---
    plt.figure(figsize=(10, 5))
    plt.plot(df_no_gfm['PV_Online_MW'], df_no_gfm['Collapse_Rate_Pct'], 'r-o', label='Current Grid (2026 - Without Battery)', linewidth=2)
    plt.plot(df_with_gfm['PV_Online_MW'], df_with_gfm['Collapse_Rate_Pct'], 'g-s', label='Future Grid (2027 - With GFM + FFR Control)', linewidth=2)
    plt.title(f"Grid Blackout Risk Analysis (Legacy Share: {int(legacy_test*100)}%)", fontsize=12)
    plt.xlabel("Total Online PV Generation (MW)", fontsize=10)
    plt.ylabel("Grid Collapse Rate (%)", fontsize=10)
    plt.grid(True, linestyle='--', alpha=0.5)
    plt.legend(fontsize=10)
    plt.savefig("results/grid_blackout_comparison.png", dpi=300, bbox_inches='tight')
    plt.close()
    
    print("Simulation complete. Both plots generated successfully in results/ folder.")

if __name__ == "__main__":
    main()