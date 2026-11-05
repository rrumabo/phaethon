import numpy as np

def swing_equation(f_curr, p_pv, p_gfm, p_mech, p_load, p_trip, system_load_mw, H, f0):
    p_acc = p_mech + p_pv + p_gfm - p_load - p_trip
    rocof = (p_acc / system_load_mw) * (f0 / (2.0 * H))
    return rocof

def run_simulation(pv_online_mw, legacy_share, trip_mw=130, system_load_mw=1000, gfm_capacity_mw=40, gfm_enabled=True, seed=None):
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
    active_blocks = np.ones(n_blocks, dtype=bool)
    
    f = np.full(steps, f0)
    rocof = np.zeros(steps)
    
    p_mech = sync_gen
    p_load = system_load_mw
    ufls_stages = np.array([49.0, 48.7, 48.4, 48.1])
    ufls_triggered = np.zeros_like(ufls_stages, dtype=bool)

    for k in range(steps - 1):
        t_curr = k * dt
        p_trip = trip_mw if t_curr >= 1.0 else 0.0
        p_pv = np.sum(active_blocks) * p_block
        
        # 1. Υπολογισμός της ισχύος της μπαταρίας με βάση τη συχνότητα του τρέχοντος βήματος
        if gfm_enabled and t_curr >= 1.0:
            df = f0 - f[k]
            p_gfm = min(gfm_capacity_mw, max(0.0, df * (gfm_capacity_mw / 0.5)))
        else:
            p_gfm = 0.0

        for idx, thresh in enumerate(ufls_stages):
            if f[k] <= thresh and not ufls_triggered[idx]:
                p_load -= 0.10 * system_load_mw
                ufls_triggered[idx] = True
                
        # 2. RK4 Solver με ενσωματωμένη τη σταθερή ισχύ p_gfm για το συγκεκριμένο βήμα
        k1 = swing_equation(f[k], p_pv, p_gfm, p_mech, p_load, p_trip, system_load_mw, H, f0)
        k2 = swing_equation(f[k] + 0.5 * dt * k1, p_pv, p_gfm, p_mech, p_load, p_trip, system_load_mw, H, f0)
        k3 = swing_equation(f[k] + 0.5 * dt * k2, p_pv, p_gfm, p_mech, p_load, p_trip, system_load_mw, H, f0)
        k4 = swing_equation(f[k] + dt * k3, p_pv, p_gfm, p_mech, p_load, p_trip, system_load_mw, H, f0)
        
        rocof[k] = k1
        f[k+1] = f[k] + (dt / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)
        
        tripped = (f[k+1] <= f_limits) | (abs(rocof[k]) >= rocof_limits)
        active_blocks[tripped] = False
                    
        if f[k+1] < 47.5:
            f[k+1:] = 47.5
            break

    return {
        'tripped_mw': pv_online_mw - (np.sum(active_blocks) * p_block),
        'collapsed': f[-1] <= 47.5
    }