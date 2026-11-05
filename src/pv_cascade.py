import numpy as np

def swing_equation(p_acc, system_load_mw, H, f0):
    return (p_acc / system_load_mw) * (f0 / (2.0 * H))

def run_simulation(pv_online_mw, legacy_share, trip_mw=130, system_load_mw=650, gfm_capacity_mw=120, gfm_enabled=True, sc_enabled=True, seed=None):
    if seed is not None and not np.isnan(seed):
        np.random.seed(int(seed))
        
    f0 = 50.0
    dt = 0.01
    steps = int(10.0 / dt)
    t = np.arange(steps) * dt
    
    # 5 Κόμβοι: 0=Βασιλικός, 1=Λεμεσός, 2=Αθαλάσσα, 3=Δεκέλεια, 4=Πάφος
    load_distribution = np.array([0.05, 0.25, 0.40, 0.15, 0.15])
    node_loads = system_load_mw * load_distribution
    
    sync_gen_total = system_load_mw - pv_online_mw
    H_thermal = max(4.0 * (sync_gen_total / system_load_mw), 0.5)
    H_sc = 1.5 if sc_enabled else 0.0
    
    # Ρεαλιστικοί συντελεστές γραμμών μεταφοράς Κύπρου (MW/Hz)
    K_ij = np.array([
        [0.0, 80.0, 50.0, 40.0, 30.0],
        [80.0, 0.0, 60.0, 20.0, 50.0],
        [50.0, 60.0, 0.0, 70.0, 30.0],
        [40.0, 20.0, 70.0, 0.0, 15.0],
        [30.0, 50.0, 30.0, 15.0, 0.0]
    ])
    
    n_blocks = 200
    p_block = pv_online_mw / n_blocks
    is_legacy = np.random.rand(n_blocks) < legacy_share
    
    block_nodes = np.random.choice([0, 1, 2, 3, 4], size=n_blocks, p=[0.05, 0.15, 0.15, 0.25, 0.40])
    f_limits = np.where(is_legacy, np.random.uniform(49.4, 49.6, n_blocks), 47.5)
    rocof_limits = np.where(is_legacy, np.random.uniform(0.4, 1.0, n_blocks), 2.0)
    
    trip_counters = np.zeros(n_blocks)
    trip_allowed_steps = np.where(is_legacy, 5, 20)
    active_blocks = np.ones(n_blocks, dtype=bool)
    
    f_nodes = np.full((5, steps), f0)
    rocof_nodes = np.zeros((5, steps))
    
    p_mech_dist = sync_gen_total * np.array([0.80, 0.0, 0.0, 0.20, 0.0]) 
    p_load = node_loads.copy()
    ufls_stages = np.array([49.0, 48.7, 48.4, 48.1])
    ufls_triggered = np.zeros((5, len(ufls_stages)), dtype=bool)
    
    gfl_capacity_mw = 150.0  
    gfl_deadband = 0.2       
    gfl_delay_steps = int(0.20 / dt)  
    rocof_ffr_threshold = 1.0  
    
    Kp = 120.0  
    Ki = 15.0   
    integral_error = 0.0
    p_gfm_vsm = 0.0
    J_vsm = 2.0  
    D_vsm = 40.0 
    collapsed = False

    for k in range(steps - 1):
        p_trip = trip_mw if t[k] >= 1.0 else 0.0
        
        current_node_pv = np.zeros(5)
        for n in range(5):
            current_node_pv[n] = np.sum(active_blocks & (block_nodes == n)) * p_block
            
        if gfm_enabled and t[k] >= 1.0:
            df_ath = f0 - f_nodes[2, k]
            d_p_gfm = (df_ath * D_vsm - p_gfm_vsm) / J_vsm
            p_gfm_vsm += d_p_gfm * dt
            p_gfm = min(gfm_capacity_mw, max(0.0, p_gfm_vsm))
        else:
            p_gfm = 0.0

        p_gfl = 0.0
        if t[k] >= 1.0:
            if abs(rocof_nodes[4, max(0, k-1)]) >= rocof_ffr_threshold:
                df_paf = f0 - f_nodes[4, k]
                p_gfl = min(gfl_capacity_mw, max(0.0, df_paf * (gfl_capacity_mw / 0.4)))
            elif k > gfl_delay_steps:
                delayed_f = f_nodes[4, k - gfl_delay_steps]
                df_delayed = f0 - delayed_f
                if df_delayed > gfl_deadband:
                    error = df_delayed - gfl_deadband
                    integral_error += error * dt
                    p_gfl = min(gfl_capacity_mw, max(0.0, (Kp * error) + (Ki * integral_error)))
                    
        p_flow = np.zeros(5)
        for i in range(5):
            for j in range(5):
                if i != j:
                    p_flow[i] += K_ij[i, j] * (f_nodes[j, k] - f_nodes[i, k])

        for n in range(5):
            for idx, thresh in enumerate(ufls_stages):
                if f_nodes[n, k] <= thresh and not ufls_triggered[n, idx]:
                    p_load[n] -= 0.10 * node_loads[n]
                    ufls_triggered[n, idx] = True

        # --- FIX: Απομόνωση ρητών SCALARS με τους δείκτες [0] έως [4] ---
        # 0: Βασιλικός (Trip)
        H0 = max(H_thermal * 0.8, 0.5)
        p_acc0 = p_mech_dist[0] + current_node_pv[0] - p_load[0] - p_trip + p_flow[0]
        rocof_nodes[0, k] = swing_equation(p_acc0, system_load_mw, H0, f0)
        f_nodes[0, k+1] = f_nodes[0, k] + rocof_nodes[0, k] * dt
        
        # 1: Λεμεσός
        H1 = 0.5
        p_acc1 = p_mech_dist[1] + current_node_pv[1] - p_load[1] + p_flow[1]
        rocof_nodes[1, k] = swing_equation(p_acc1, system_load_mw, H1, f0)
        f_nodes[1, k+1] = f_nodes[1, k] + rocof_nodes[1, k] * dt
        
        # 2: Αθαλάσσα (GFM)
        H2 = 0.5 + (J_vsm if p_gfm > 0.0 else 0.0)
        p_acc2 = p_mech_dist[2] + current_node_pv[2] + p_gfm - p_load[2] + p_flow[2]
        rocof_nodes[2, k] = swing_equation(p_acc2, system_load_mw, H2, f0)
        f_nodes[2, k+1] = f_nodes[2, k] + rocof_nodes[2, k] * dt
        
        # 3: Δεκέλεια (Thermal + SC)
        H3 = max(H_thermal * 0.2, 0.5) + H_sc
        p_acc3 = p_mech_dist[3] + current_node_pv[3] - p_load[3] + p_flow[3]
        rocof_nodes[3, k] = swing_equation(p_acc3, system_load_mw, H3, f0)
        f_nodes[3, k+1] = f_nodes[3, k] + rocof_nodes[3, k] * dt
        
        # 4: Πάφος (GFL)
        H4 = 0.5
        p_acc4 = p_mech_dist[4] + current_node_pv[4] + p_gfl - p_load[4] + p_flow[4]
        rocof_nodes[4, k] = swing_equation(p_acc4, system_load_mw, H4, f0)
        f_nodes[4, k+1] = f_nodes[4, k] + rocof_nodes[4, k] * dt

        for i in range(n_blocks):
            if active_blocks[i]:
                node_idx = block_nodes[i]
                if f_nodes[node_idx, k+1] <= f_limits[i] or abs(rocof_nodes[node_idx, k]) >= rocof_limits[i]:
                    trip_counters[i] += 1
                else:
                    trip_counters[i] = 0
                    
                if trip_counters[i] >= trip_allowed_steps[i]:
                    active_blocks[i] = False

        if np.any(f_nodes[:, k+1] < 47.5):
            collapsed = True
            active_blocks[:] = False
            break

    return {
        'tripped_mw': pv_online_mw - (np.sum(active_blocks) * p_block),
        'collapsed': collapsed
    }