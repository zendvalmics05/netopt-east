"""
Correlated inventory pooling calculations.

σ_pool(j) = sqrt( sigma' Sigma_j sigma )
where Sigma_j is the correlation submatrix for nodes assigned to warehouse j.

Used in:
  - model.py objective (safety stock cost term)
  - frontier.py (cost breakdown at each service level)
  - Phase 3 correlation sensitivity experiment
"""

import numpy as np
import pandas as pd

def pooled_std_for_assignment(assignment: dict,        # wh_id -> [node_ids]
                              stds: pd.Series,          # node_id -> weekly std
                              corr: pd.DataFrame) -> dict:
    """
    Return {wh_id: correlated pooled std} for a given assignment.

    assignment: dict mapping warehouse_id to list of node_ids served.
    stds: pandas Series indexed by node_id.
    corr: full 40x40 correlation DataFrame.
    """
    result = {}
    for wh_id, node_list in assignment.items():
        if not node_list:
            result[wh_id] = 0.0
            continue
        s = stds.loc[node_list].values
        C = corr.loc[node_list, node_list].values
        result[wh_id] = float(np.sqrt(s @ C @ s))
    return result

def safety_stock_cost(pooled_stds: dict,
                      lead_times_weeks: dict,
                      z_alpha: float,
                      holding_cost_per_unit: float) -> float:
    """
    Total annual safety stock holding cost.

    SS_j = z_alpha × sigma_pool_j × sqrt(L_j)
    cost = SS_j × holding_cost_per_unit
    """
    total = 0.0
    for wh_id, sigma_pool in pooled_stds.items():
        L = lead_times_weeks[wh_id]
        ss = z_alpha * sigma_pool * np.sqrt(L)
        total += ss * holding_cost_per_unit
    return total

if __name__ == '__main__':
    # Unit tests and sanity checks for inventory.py
    nodes = pd.read_csv('data/processed/demand_nodes_anchored.csv')
    corr = pd.read_csv('data/processed/correlation_matrix.csv', index_col=0)
    stds = nodes.set_index('node_id')['demand_std_units_per_week']

    print("Running inventory.py verification tests...")

    # Test 1: Empty and single-node assignments
    k_id = nodes[nodes['city'] == 'Kolkata']['node_id'].values[0]
    h_id = nodes[nodes['city'] == 'Howrah']['node_id'].values[0]
    g_id = nodes[nodes['city'] == 'Guwahati']['node_id'].values[0]

    test_assignment = {
        'WH_Empty': [],
        'WH_Single': [k_id],
        'WH_Close': [k_id, h_id],
        'WH_Far': [k_id, g_id]
    }

    pooled = pooled_std_for_assignment(test_assignment, stds, corr)
    assert pooled['WH_Empty'] == 0.0, "Empty warehouse should have 0.0 pooled std"
    assert np.isclose(pooled['WH_Single'], stds.loc[k_id]), "Single node pooled std should equal its own std"
    print("✓ Empty and single-node assignment tests passed")

    # Test 2: Correlated pooling penalty test
    # Because Kolkata and Howrah have positive correlation, pooled std > independent sqrt(s1^2 + s2^2)
    indep_kh = np.sqrt(stds.loc[k_id]**2 + stds.loc[h_id]**2)
    assert pooled['WH_Close'] > indep_kh, "Positive correlation should increase pooled std above independent assumption"
    print(f"✓ Correlation pooling impact verified: Close nodes pooled std = {pooled['WH_Close']:.1f} vs Independent = {indep_kh:.1f}")

    # Test 3: Safety stock cost calculation
    lead_times = {'WH_Empty': 1/7, 'WH_Single': 1/7, 'WH_Close': 2/7, 'WH_Far': 4/7}
    z_alpha = 1.645  # 95% service level
    annual_holding_cost_rate = 0.25 * 90.0  # 25% of ₹90 SKU

    cost = safety_stock_cost(pooled, lead_times, z_alpha, annual_holding_cost_rate)
    assert cost > 0, "Safety stock cost should be strictly positive"
    print(f"✓ Safety stock cost calculated: ₹{cost:,.2f}")

    print("\nALL INVENTORY.PY VERIFICATION TESTS PASSED SUCCESSFULLY!")
