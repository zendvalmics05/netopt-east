"""
Correlation sensitivity: how spatial demand correlation erodes the
square-root pooling benefit.

Method: rebuild the correlation matrix at each rho_0 level, re-solve the
MILP at alpha=95%, record the safety stock cost and total pooling benefit.

Pooling benefit metric:
    benefit(rho) = 1 - SS_pooled(rho) / SS_no_pooling
where SS_no_pooling = sum of individual node safety stocks (each node
holds its own stock, no warehouse pooling).

Expected result (the insight):
    rho_0=0.0  → benefit ~60-70%  (textbook square-root law)
    rho_0=0.3  → benefit ~45-55%
    rho_0=0.6  → benefit ~30-40%
    rho_0=1.0  → benefit ~0-10%   (no pooling benefit, as theory predicts)
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import pandas as pd
import numpy as np
from src.data.correlation import build_correlation_matrix
from src.optimization.model import solve_network_design

RHO_LEVELS = [0.0, 0.3, 0.6, 1.0]

def no_pooling_safety_stock(nodes, z_alpha=1.645, holding_per_unit=22.5):
    """
    Baseline: every node holds its own safety stock.
    SS_i = z * sigma_i * sqrt(lead_time_i / 7), lead_time_i = current plant-to-node days.
    Use a representative lead time of 5 days for all nodes (documented assumption).
    """
    lead_weeks = 5 / 7
    ss_per_node = z_alpha * nodes['demand_std_units_per_week'] * np.sqrt(lead_weeks)
    return ss_per_node.sum() * holding_per_unit

def run_correlation_sensitivity(nodes, warehouses, transport_costs,
                                n_scenarios=50, verbose=True) -> pd.DataFrame:
    rows = []
    ss_no_pool = no_pooling_safety_stock(nodes)

    for rho_0 in RHO_LEVELS:
        if verbose:
            print(f"\n{'='*55}")
            print(f"Re-solving with rho_0 = {rho_0}")
            print(f"{'='*55}")

        # Rebuild correlation matrix at this level
        corr = build_correlation_matrix(nodes, rho_0=rho_0, d_0=200.0)

        # Solve
        result = solve_network_design(
            nodes, warehouses, transport_costs, corr,
            service_level=0.95,
            n_scenarios=n_scenarios,
            verbose=verbose,
        )

        if result is None:
            continue

        # Pooled safety stock from the solution
        ss_pooled = result['inventory']['safety_stock'].sum() if len(result['inventory']) else 0.0
        ss_pooled_cost = ss_pooled * 0.25 * 90  # 0.25 * 90 = 22.5 holding cost per unit/yr

        benefit_pct = 100 * (1 - ss_pooled_cost / ss_no_pool)

        rows.append({
            'rho_0': rho_0,
            'total_cost': result['total_annual_cost'],
            'safety_stock_units': ss_pooled,
            'safety_stock_cost': ss_pooled_cost,
            'pooling_benefit_pct': benefit_pct,
            'open_warehouses': ','.join(result['open_warehouses']),
        })

    return pd.DataFrame(rows)

if __name__ == '__main__':
    nodes = pd.read_csv('data/processed/demand_nodes_anchored.csv')
    whs = pd.read_csv('data/processed/candidate_warehouses.csv')
    costs = pd.read_csv('data/processed/transport_costs.csv')

    results = run_correlation_sensitivity(nodes, whs, costs)
    results.to_csv('data/processed/correlation_sensitivity.csv', index=False)

    print("\n" + "="*55)
    print("CORRELATION SENSITIVITY - Pooling benefit vs. correlation")
    print("="*55)
    print(results[['rho_0', 'safety_stock_cost',
                   'pooling_benefit_pct', 'open_warehouses']].to_string(index=False))
    print("="*55)
    print("\nINSIGHT: Spatial correlation erodes the square-root pooling benefit.")
    if (results['rho_0'] == 0.0).any():
        print(f"At rho_0=0.0: {results.loc[results['rho_0']==0.0, 'pooling_benefit_pct'].values[0]:.1f}% reduction")
    if (results['rho_0'] == 1.0).any():
        print(f"At rho_0=1.0: {results.loc[results['rho_0']==1.0, 'pooling_benefit_pct'].values[0]:.1f}% reduction")
