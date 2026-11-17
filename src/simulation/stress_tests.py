"""
Event-driven stress tests for NETOPT-EAST.

Each event modifies the input data in a specific, documented way,
re-solves, and quantifies the impact.

Events:
  1. COVID demand shock      — 3-week essentials spike (+40%), 4-week drop (-25%)
  2. NH-19 highway closure   — +5 days lead time, +50% cost on affected lanes
  3. Warehouse failure       — force-close largest warehouse, re-solve
  4. Fuel price spike        — +40% all transport costs
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import pandas as pd
import numpy as np
from src.optimization.model import solve_network_design

def event_covid_shock(nodes, warehouses, transport_costs, corr_matrix):
    """
    COVID-style demand shock.
    Design: demand multiplier 1.4 for weeks 1-3, 0.75 for weeks 4-7, 1.0 after.
    For the annual model: apply a single 'shock week' representative demand
    multiplier of 1.15 annualized (documented simplification), OR run the
    multi-week profile through the scenario machinery.

    Simplified implementation: scale annual demand by the weighted average
    of the shock profile: (3×1.4 + 4×0.75 + 45×1.0) / 52 ≈ 1.02 annual,
    but with much higher variance. We model this as mean × 1.02, CV × 1.5.
    """
    shocked = nodes.copy()
    shocked['demand_mean_units_per_week'] *= 1.02
    shocked['demand_std_units_per_week'] *= 1.5
    shocked['demand_cv'] = shocked['demand_std_units_per_week'] / shocked['demand_mean_units_per_week']
    return shocked, warehouses, transport_costs, 'COVID demand shock (mean×1.02, CV×1.5)'

def event_nh19_closure(nodes, warehouses, transport_costs, corr_matrix):
    """
    NH-19 (Kolkata-Delhi corridor) closure.
    Affects: all lanes from Kolkata_WH and Siliguri_WH to nodes west of ~86°E
    (Patna, Ranchi, and western nodes). +5 days lead time, +50% cost.
    """
    shocked_costs = transport_costs.copy()
    affected_whs = ['Kolkata_WH', 'Siliguri_WH']
    affected_nodes = nodes[nodes['longitude'] < 86.0]['node_id'].tolist()

    mask = (
        shocked_costs['from_type'].eq('warehouse') &
        shocked_costs['from_id'].isin(affected_whs) &
        shocked_costs['to_id'].isin(affected_nodes)
    )
    shocked_costs.loc[mask, 'cost_per_unit'] *= 1.5
    if 'lead_time_days' in shocked_costs.columns:
        shocked_costs.loc[mask, 'lead_time_days'] += 5

    return nodes, warehouses, shocked_costs, 'NH-19 closure (+50% cost, +5d lead on westbound lanes)'

def event_warehouse_failure(nodes, warehouses, transport_costs, corr_matrix,
                            base_result):
    """
    Force-close the largest open warehouse by volume. Re-solve with remaining set.
    """
    flows = base_result['flows']
    largest = flows.groupby('warehouse')['weekly_units'].sum().idxmax()
    remaining = [w for w in warehouses['warehouse_id'] if w != largest]
    shocked_whs = warehouses[warehouses['warehouse_id'].isin(remaining)].copy()
    return nodes, shocked_whs, transport_costs, f'Warehouse failure ({largest} forced closed)'

def event_fuel_spike(nodes, warehouses, transport_costs, corr_matrix):
    """+40% on all transport costs."""
    shocked = transport_costs.copy()
    shocked['cost_per_unit'] *= 1.4
    return nodes, warehouses, shocked, 'Fuel price spike (+40% all transport)'

def run_all_stress_tests(nodes, warehouses, transport_costs, corr_matrix,
                         base_result, n_scenarios=50):
    """Run all four events. Return scorecard DataFrame."""
    base_cost = base_result['total_annual_cost']

    events = [
        event_covid_shock,
        event_nh19_closure,
        lambda n, w, c, cm: event_warehouse_failure(n, w, c, cm, base_result),
        event_fuel_spike,
    ]

    rows = []
    for event_fn in events:
        s_nodes, s_whs, s_costs, desc = event_fn(nodes, warehouses, transport_costs, corr_matrix)
        print(f"\nRunning Stress Test: {desc}...")

        result = solve_network_design(
            s_nodes, s_whs, s_costs, corr_matrix,
            service_level=0.95, n_scenarios=n_scenarios, verbose=False
        )

        if result is None:
            rows.append({
                'event': desc,
                'base_cost': base_cost,
                'stressed_cost': np.nan,
                'delta_pct': np.nan,
                'open_warehouses': 'INFEASIBLE',
                'n_warehouses': 0
            })
            continue

        delta_pct = 100 * (result['total_annual_cost'] - base_cost) / base_cost
        rows.append({
            'event': desc,
            'base_cost': base_cost,
            'stressed_cost': result['total_annual_cost'],
            'delta_pct': delta_pct,
            'open_warehouses': ','.join(result['open_warehouses']),
            'n_warehouses': len(result['open_warehouses']),
        })

    return pd.DataFrame(rows)

if __name__ == '__main__':
    nodes = pd.read_csv('data/processed/demand_nodes_anchored.csv')
    whs = pd.read_csv('data/processed/candidate_warehouses.csv')
    costs = pd.read_csv('data/processed/transport_costs.csv')
    corr = pd.read_csv('data/processed/correlation_matrix.csv', index_col=0)

    # Base case solve
    print("Computing baseline network design...")
    base = solve_network_design(nodes, whs, costs, corr,
                                service_level=0.95, n_scenarios=50, verbose=False)
    print(f"Base case: ₹{base['total_annual_cost']:,.0f} | {base['open_warehouses']}")

    scorecard = run_all_stress_tests(nodes, whs, costs, corr, base, n_scenarios=50)
    scorecard.to_csv('data/processed/stress_test_results.csv', index=False)

    print("\n" + "="*65)
    print("ROBUSTNESS SCORECARD")
    print("="*65)
    print(scorecard[['event', 'stressed_cost', 'delta_pct', 'n_warehouses']].to_string(index=False))
    print("="*65)
