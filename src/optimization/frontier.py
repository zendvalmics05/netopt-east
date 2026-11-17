"""
Cost-service frontier solver.

Solves the chance-constrained MILP at multiple service levels and
records the full cost breakdown at each point. Output feeds the
frontier chart in the dashboard and final report.

Runtime note: 4 service levels × ~30s per solve ≈ 2 minutes total.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import pandas as pd
from src.optimization.model import solve_network_design

SERVICE_LEVELS = [0.90, 0.95, 0.98, 0.99]

def compute_frontier(nodes, warehouses, transport_costs, corr_matrix,
                     n_scenarios=50, verbose=True) -> pd.DataFrame:
    """
    Solve at each service level. Return one row per level with full
    cost breakdown + open warehouse set.
    """
    rows = []
    for alpha in SERVICE_LEVELS:
        if verbose:
            print(f"\n{'='*55}")
            print(f"Solving at {alpha:.0%} service level...")
            print(f"{'='*55}")

        result = solve_network_design(
            nodes, warehouses, transport_costs, corr_matrix,
            service_level=alpha,
            n_scenarios=n_scenarios,
            verbose=verbose,
        )

        if result is None:
            print(f"  FAILED at {alpha:.0%}")
            continue

        rows.append({
            'service_level': alpha,
            'z_alpha': {0.90: 1.282, 0.95: 1.645, 0.98: 2.054, 0.99: 2.326}[alpha],
            'total_cost': result['total_annual_cost'],
            'fixed_cost': result['fixed_cost'],
            'transport_cost': result['transport_cost'],
            'inbound_cost': result['inbound_cost'],
            'variable_cost': result['variable_cost'],
            'inventory_cost': result['inventory_cost'],
            'safety_stock_cost': result['inventory']['safety_stock'].sum()
                               * 0.25 * 90 if len(result['inventory']) else 0,
            'open_warehouses': ','.join(result['open_warehouses']),
            'n_warehouses': len(result['open_warehouses']),
        })

    frontier_df = pd.DataFrame(rows)
    return frontier_df

def frontier_insights(frontier_df: pd.DataFrame) -> dict:
    """
    Extract the headline numbers for the report and resume.

    Returns the cost of moving between service levels — the 'so what'
    that makes the frontier chart meaningful.
    """
    df = frontier_df.sort_values('service_level').reset_index(drop=True)
    insights = {}

    for i in range(1, len(df)):
        lower = df.loc[i - 1, 'service_level']
        higher = df.loc[i, 'service_level']
        cost_lower = df.loc[i - 1, 'total_cost']
        cost_higher = df.loc[i, 'total_cost']
        delta = cost_higher - cost_lower
        insights[f'{lower:.0%}_to_{higher:.0%}'] = {
            'delta_cost_inr': delta,
            'delta_cost_lakh': delta / 1e5,
            'pct_increase': 100 * delta / cost_lower,
        }

    # Cross-level delta: 95% → 99% (may not be adjacent)
    row_95 = df[df['service_level'] == 0.95]
    row_99 = df[df['service_level'] == 0.99]
    if len(row_95) and len(row_99):
        c95 = row_95['total_cost'].values[0]
        c99 = row_99['total_cost'].values[0]
        delta_95_99 = c99 - c95
        insights['95%_to_99%'] = {
            'delta_cost_inr': delta_95_99,
            'delta_cost_lakh': delta_95_99 / 1e5,
            'pct_increase': 100 * delta_95_99 / c95,
        }
        insights['headline'] = (
            f"Moving from 95% to 99% fill rate costs "
            f"₹{delta_95_99 / 1e5:.0f} lakh/year "
            f"(+{100 * delta_95_99 / c95:.1f}%)"
        )

    return insights

if __name__ == '__main__':
    nodes = pd.read_csv('data/processed/demand_nodes_anchored.csv')
    whs = pd.read_csv('data/processed/candidate_warehouses.csv')
    costs = pd.read_csv('data/processed/transport_costs.csv')
    corr = pd.read_csv('data/processed/correlation_matrix.csv', index_col=0)

    frontier = compute_frontier(nodes, whs, costs, corr)
    frontier.to_csv('data/processed/frontier_results.csv', index=False)

    insights = frontier_insights(frontier)
    print("\n" + "="*55)
    print("FRONTIER INSIGHTS")
    print("="*55)
    for k, v in insights.items():
        if k != 'headline':
            print(f"  {k}: +₹{v['delta_cost_lakh']:.0f}L ({v['pct_increase']:+.1f}%)")
    print(f"\n  HEADLINE: {insights['headline']}")
    print("="*55)
