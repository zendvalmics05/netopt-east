"""
Monte Carlo evaluation of the optimal network.

IMPORTANT distinction from Phase 2:
  Phase 2 scenarios were INSIDE the MILP (SAA chance constraints, S=50).
  This module evaluates the FIXED optimal network under Monte Carlo scenarios.
  No re-optimization of warehouse locations — we measure how the chosen network performs.

Outputs:
  - Cost distribution (mean, std, percentiles)
  - Service level distribution (fraction of scenarios meeting demand)
  - Network stability
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import pandas as pd
import numpy as np
from src.optimization.scenarios import generate_scenarios
from src.optimization.model import solve_network_design

def evaluate_fixed_network(nodes, warehouses, transport_costs, corr_matrix,
                           open_wh, n_scenarios=10, seed=42):
    """
    Evaluate a fixed warehouse set under Monte Carlo scenarios.

    For each scenario:
      1. Perturb demand (via correlated multipliers)
      2. Perturb transport costs +/-15%
      3. Perturb lead times +/-3 days
      4. Re-optimize FLOWS only (warehouses fixed to open_wh)
      5. Record total cost + whether all demand was met

    Returns DataFrame with one row per scenario.
    """
    rng = np.random.default_rng(seed)

    # Generate demand scenarios (same machinery as Phase 2)
    demand_mults = generate_scenarios(nodes, corr_matrix, n_scenarios, seed=seed)

    # Restrict warehouses to the open set for flow re-optimization
    wh_open = warehouses[warehouses['warehouse_id'].isin(open_wh)].copy()

    results = []
    for s in range(n_scenarios):
        print(f"  Scenario {s + 1}/{n_scenarios}...")

        # Perturb demand
        scen_nodes = nodes.copy()
        scen_nodes['demand_mean_units_per_week'] = (
            nodes['demand_mean_units_per_week'] * demand_mults[s]
        ).round()
        scen_nodes['demand_std_units_per_week'] = (
            scen_nodes['demand_mean_units_per_week'] * nodes['demand_cv']
        )

        # Perturb transport costs +/-15%
        scen_costs = transport_costs.copy()
        cost_mult = rng.uniform(0.85, 1.15, size=len(scen_costs))
        scen_costs['cost_per_unit'] = (scen_costs['cost_per_unit'] * cost_mult).round(2)

        # Perturb lead times +/-3 days (integer, min 1)
        scen_whs = wh_open.copy()
        lt_noise = rng.integers(-3, 4, size=len(scen_whs))
        scen_whs['lead_time_from_plant_days'] = np.maximum(
            1, scen_whs['lead_time_from_plant_days'] + lt_noise
        )

        # Re-solve with fixed warehouse set (fast: binaries fixed, only flows)
        result = solve_network_design(
            scen_nodes, scen_whs, scen_costs, corr_matrix,
            service_level=0.95, n_scenarios=20,   # S=20 for fast flow evaluation
            max_iterations=1,                      # no fixed-point needed for eval
            verbose=False,
        )

        if result:
            results.append({
                'scenario': s,
                'total_cost': result['total_annual_cost'],
                'inventory_cost': result['inventory_cost'],
                'transport_cost': result['transport_cost'],
                'all_demand_met': True,   # CP-SAT enforces demand fulfillment
                'demand_multiplier_mean': demand_mults[s].mean(),
            })
        else:
            results.append({
                'scenario': s,
                'total_cost': np.nan,
                'inventory_cost': np.nan,
                'transport_cost': np.nan,
                'all_demand_met': False,
                'demand_multiplier_mean': demand_mults[s].mean(),
            })

    return pd.DataFrame(results)

def mc_summary(mc_df: pd.DataFrame) -> dict:
    """Headline statistics for the report."""
    valid = mc_df.dropna(subset=['total_cost'])
    return {
        'n_scenarios': len(mc_df),
        'n_feasible': len(valid),
        'mean_cost': valid['total_cost'].mean() if len(valid) else np.nan,
        'std_cost': valid['total_cost'].std() if len(valid) else np.nan,
        'cv_cost': (valid['total_cost'].std() / valid['total_cost'].mean()) if len(valid) else np.nan,
        'p5': valid['total_cost'].quantile(0.05) if len(valid) else np.nan,
        'p50': valid['total_cost'].quantile(0.50) if len(valid) else np.nan,
        'p95': valid['total_cost'].quantile(0.95) if len(valid) else np.nan,
        'feasibility_rate': len(valid) / len(mc_df) if len(mc_df) else 0.0,
    }

if __name__ == '__main__':
    nodes = pd.read_csv('data/processed/demand_nodes_anchored.csv')
    whs = pd.read_csv('data/processed/candidate_warehouses.csv')
    costs = pd.read_csv('data/processed/transport_costs.csv')
    corr = pd.read_csv('data/processed/correlation_matrix.csv', index_col=0)

    # Get optimal network at 95% (base case)
    print("Finding base optimal network...")
    base = solve_network_design(nodes, whs, costs, corr,
                                service_level=0.95, n_scenarios=50, verbose=False)
    open_wh = base['open_warehouses']
    print(f"Evaluating fixed network: {open_wh}")

    # Run initial smoke test with 10 scenarios as requested
    N_TEST_SCENARIOS = 500
    print(f"\nRunning test Monte Carlo simulation with {N_TEST_SCENARIOS} scenarios...")
    mc = evaluate_fixed_network(nodes, whs, costs, corr, open_wh, n_scenarios=N_TEST_SCENARIOS)
    mc.to_csv('data/processed/mc_results_test10.csv', index=False)

    stats = mc_summary(mc)
    print("\n" + "="*55)
    print(f"MONTE CARLO SUMMARY ({N_TEST_SCENARIOS} test scenarios, fixed network)")
    print("="*55)
    for k, v in stats.items():
        if isinstance(v, float):
            print(f"  {k:.<20} {v:,.4f}" if v < 10 else f"  {k:.<20} ₹{v:,.0f}")
        else:
            print(f"  {k:.<20} {v}")
    print("="*55)
