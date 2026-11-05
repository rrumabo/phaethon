import numpy as np

def swing_equation(f_curr, p_pv, p_gfm, p_gfl, p_mech, p_load, p_trip, system_load_mw, H, f0):
    p_acc = p_mech + p_pv + p_gfm + p_gfl - p_load - p_trip
    return (p_acc / system_load_mw) * (f0 / (2.0 * H))

def run_simulation(pv_online_mw, legacy_share, trip_mw=130, system_load_mw=650, gfm_capacity_mw=120, gfm_enabled=True, seed=None):
    if seed is not None and not np.isnan(seed):
        np.random.seed(int(seed))
        
    f0 = 50.0
    dt = 0.01
    steps = int(10.0 / dt)
    
    sync_gen = system_load_mw - pv_online_mw
    H_base = max(4.0 * (sync_gen / system_load_mw), 0.5)
    
    n_blocks = 200
    p_block = pv_online_mw / n_blocks
    is_legacy = np.random.rand(n_blocks) < legacy_share
    
    f_limits = np.where(is_legacy, np.random.uniform(49.4, 49.6, n_blocks), 47.5)
    rocof_limits = np.where(is_legacy, np.random.uniform(0.4, 1.0, n_blocks), 2.0)
    
    trip_counters = np.zeros(n_blocks)
    trip_allowed_steps = np.where(is_legacy, 5, 20)
    active_blocks = np.ones(n_blocks, dtype=bool)
    
    f = np.full(steps, f0)
    rocof = np.zeros(steps)
    
    p_mech = sync_gen
    p_load = system_load_mw
    ufls_stages = np.array([49.0, 48.7, 48.4, 48.1])
    ufls_triggered = np.zeros_like(ufls_stages, dtype=bool)
    
    gfl_capacity_mw = 150.0  
    gfl_deadband = 0.2       
    gfl_delay_steps = int(0.20 / dt)  
    rocof_ffr_threshold = 1.0  
    
    Kp = 120.0  
    Ki = 15.0   
    integral_error = 0.0
    p_gfl_arr = np.zeros(steps)
    
    # Advanced Parameters: SoC Tracking & VSM
    soc_gfm = 0.50
    soc_gfl = 0.50
    gfm_energy_mwh = 240.0
    gfl_energy_mwh = 300.0
    soc_floor = 0.05
    
    J_vsm = 2.0  
    D_vsm = 40.0 
    p_gfm_vsm = 0.0

    for k in range(steps - 1):
        t_curr = k * dt
        p_trip = trip_mw if t_curr >= 1.0 else 0.0
        p_pv = np.sum(active_blocks) * p_block
        
        # 1. Grid-Forming VSM Control Loop with SoC Tracking
        if gfm_enabled and t_curr >= 1.0 and soc_gfm > soc_floor:
            df = f0 - f[k]
            d_p_gfm = (df * D_vsm - p_gfm_vsm) / J_vsm
            p_gfm_vsm += d_p_gfm * dt
            p_gfm = min(gfm_capacity_mw, max(0.0, p_gfm_vsm))
            soc_gfm -= (p_gfm * (dt / 3600.0)) / gfm_energy_mwh
        else:
            p_gfm = 0.0

        # 2. Grid-Following FFR with RoCoF Override and SoC Tracking
        if t_curr >= 1.0 and soc_gfl > soc_floor:
            if abs(rocof[max(0, k-1)]) >= rocof_ffr_threshold:
                df_direct = f0 - f[k]
                p_gfl_arr[k] = min(gfl_capacity_mw, max(0.0, df_direct * (gfl_capacity_mw / 0.4)))
            elif k > gfl_delay_steps:
                delayed_f = f[k - gfl_delay_steps]
                df_delayed = f0 - delayed_f
                if df_delayed > gfl_deadband:
                    error = df_delayed - gfl_deadband
                    integral_error += error * dt
                    p_gfl_arr[k] = min(gfl_capacity_mw, max(0.0, (Kp * error) + (Ki * integral_error)))
                else:
                    p_gfl_arr[k] = 0.0
            else:
                p_gfl_arr[k] = 0.0
            soc_gfl -= (p_gfl_arr[k] * (dt / 3600.0)) / gfl_energy_mwh
        else:
            p_gfl_arr[k] = 0.0

        # 3. Adaptive UFLS Coordination Loop
        p_bess_total = p_gfm + p_gfl_arr[k]
        p_deficit = p_trip + (pv_online_mw - p_pv)
        bess_support_ratio = p_bess_total / max(1.0, p_deficit)
        
        for idx, thresh in enumerate(ufls_stages):
            if f[k] <= thresh and not ufls_triggered[idx]:
                # If BESS covers > 70% of the mismatch, reduce load shed stage by half
                shed_multiplier = 0.5 if bess_support_ratio > 0.70 else 1.0
                p_load -= (0.10 * shed_multiplier) * system_load_mw
                ufls_triggered[idx] = True
                
        # Total System Inertia (Physical + Emulated VSM Virtual Inertia)
        H_total = H_base + (J_vsm if p_gfm > 0.0 else 0.0)
                
        # RK4 Solver Core
        k1 = swing_equation(f[k], p_pv, p_gfm, p_gfl_arr[k], p_mech, p_load, p_trip, system_load_mw, H_total, f0)
        k2 = swing_equation(f[k] + 0.5 * dt * k1, p_pv, p_gfm, p_gfl_arr[k], p_mech, p_load, p_trip, system_load_mw, H_total, f0)
        k3 = swing_equation(f[k] + 0.5 * dt * k2, p_pv, p_gfm, p_gfl_arr[k], p_mech, p_load, p_trip, system_load_mw, H_total, f0)
        k4 = swing_equation(f[k] + dt * k3, p_pv, p_gfm, p_gfl_arr[k], p_mech, p_load, p_trip, system_load_mw, H_total, f0)
        
        rocof[k] = k1
        f[k+1] = f[k] + (dt / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)
        
        out_of_bounds = (f[k+1] <= f_limits) | (abs(rocof[k]) >= rocof_limits)
        trip_counters[out_of_bounds] += 1
        trip_counters[~out_of_bounds] = 0  
        
        active_blocks[trip_counters >= trip_allowed_steps] = False
                    
        if f[k+1] < 47.5:
            f[k+1:] = 47.5
            active_blocks[:] = False  
            break

    return {
        'tripped_mw': pv_online_mw - (np.sum(active_blocks) * p_block),
        'collapsed': f[-1] <= 47.5
    }