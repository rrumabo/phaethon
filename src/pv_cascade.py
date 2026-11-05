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
    H = max(4.0 * (sync_gen / system_load_mw), 0.5)
    
    n_blocks = 200
    p_block = pv_online_mw / n_blocks
    is_legacy = np.random.rand(n_blocks) < legacy_share
    
    f_limits = np.where(is_legacy, np.random.uniform(49.4, 49.6, n_blocks), 47.5)
    rocof_limits = np.where(is_legacy, np.random.uniform(0.4, 1.0, n_blocks), 2.0)
    
    # Χρονόμετρο για κάθε block (πόσα βήματα παραμένει εκτός ορίων)
    trip_counters = np.zeros(n_blocks)
    # Τα legacy tripάρουν σε 50ms (5 βήματα), τα modern σε 200ms (20 βήματα)
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

    for k in range(steps - 1):
        t_curr = k * dt
        p_trip = trip_mw if t_curr >= 1.0 else 0.0
        p_pv = np.sum(active_blocks) * p_block
        
        if gfm_enabled and t_curr >= 1.0:
            df = f0 - f[k]
            p_gfm = min(gfm_capacity_mw, max(0.0, df * (gfm_capacity_mw / 0.5)))
        else:
            p_gfm = 0.0

        if t_curr >= 1.0:
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
        else:
            p_gfl_arr[k] = 0.0

        for idx, thresh in enumerate(ufls_stages):
            if f[k] <= thresh and not ufls_triggered[idx]:
                p_load -= 0.10 * system_load_mw
                ufls_triggered[idx] = True
                
        k1 = swing_equation(f[k], p_pv, p_gfm, p_gfl_arr[k], p_mech, p_load, p_trip, system_load_mw, H, f0)
        k2 = swing_equation(f[k] + 0.5 * dt * k1, p_pv, p_gfm, p_gfl_arr[k], p_mech, p_load, p_trip, system_load_mw, H, f0)
        k3 = swing_equation(f[k] + 0.5 * dt * k2, p_pv, p_gfm, p_gfl_arr[k], p_mech, p_load, p_trip, system_load_mw, H, f0)
        k4 = swing_equation(f[k] + dt * k3, p_pv, p_gfm, p_gfl_arr[k], p_mech, p_load, p_trip, system_load_mw, H, f0)
        
        rocof[k] = k1
        f[k+1] = f[k] + (dt / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)
        
        # Υλοποίηση χρονοκαθυστέρησης στις προστασίες (Trip Timers)
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