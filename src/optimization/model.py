"""
Chance-constrained MILP for warehouse location + flow + inventory.

Key v2.0 upgrade vs v1.0: safety stock is IN the model via SAA scenario
constraints (set 5 below), and its cost is in the objective via the
correlated pooled std term.

Solver: OR-Tools CP-SAT (integer-safe via scaling).
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from ortools.sat.python import cp_model
import pandas as pd
import numpy as np
from src.optimization.scenarios import generate_scenarios, lead_time_demands
from src.optimization.inventory import pooled_std_for_assignment, safety_stock_cost

Z_ALPHA = {
    0.90: 1.282,
    0.95: 1.645,
    0.98: 2.054,
    0.99: 2.326,
    0.995: 2.576,
    0.999: 3.090,
    0.9995: 3.291,
    0.9999: 3.719,
}

def solve_network_design(nodes: pd.DataFrame,
                         warehouses: pd.DataFrame,
                         transport_costs: pd.DataFrame,
                         corr_matrix: pd.DataFrame,
                         service_level: float = 0.95,
                         holding_cost_rate: float = 0.25,
                         product_value: float = 90.0,   # matches AVG_SKU_PRICE
                         n_scenarios: int = 50,
                         max_iterations: int = 3,
                         seed: int = 42,
                         verbose: bool = True) -> dict:
    """
    Solve the chance-constrained network design.

    Fixed-point iteration on pooled std:
        iter 0: assume independent demand (upper bound on pooling benefit)
        iter k: update pooled std from iteration k-1 assignment, re-solve
        stop when open-warehouse set is stable or max_iterations reached.

    Parameters mirror the mathematical formulation in File 02 §2.1.
    """

    # ── 0. Setup ──────────────────────────────────────────────────────
    node_ids = nodes['node_id'].tolist()
    wh_ids = warehouses['warehouse_id'].tolist()
    n_nodes, n_wh = len(node_ids), len(wh_ids)

    demand = nodes.set_index('node_id')['demand_mean_units_per_week']
    stds = nodes.set_index('node_id')['demand_std_units_per_week']

    fixed_annual = warehouses.set_index('warehouse_id')['fixed_cost_monthly_rupees'] * 12
    capacity = warehouses.set_index('warehouse_id')['capacity_units_per_week']
    var_cost = warehouses.set_index('warehouse_id')['variable_cost_per_unit']
    lead_days = warehouses.set_index('warehouse_id')['lead_time_from_plant_days']
    lead_weeks = (lead_days / 7.0).to_dict()

    # Transport cost lookups
    wh_node_cost = {}
    for _, r in transport_costs[transport_costs['from_type'] == 'warehouse'].iterrows():
        wh_node_cost[(r['from_id'], r['to_id'])] = r['cost_per_unit']
    plant_wh_cost = {}
    for _, r in transport_costs[transport_costs['from_type'] == 'plant'].iterrows():
        plant_wh_cost[r['to_id']] = r['cost_per_unit']

    holding_per_unit = holding_cost_rate * product_value   # ₹/unit/year
    z = Z_ALPHA[service_level]

    # Generate scenarios ONCE (same scenarios across fixed-point iterations
    # — this is the "common random numbers" variance-reduction technique)
    scenarios = generate_scenarios(nodes, corr_matrix, n_scenarios, seed=seed)

    # ── Fixed-point iteration ─────────────────────────────────────────
    prev_open = None
    pooled_std_est = {j: float(np.sqrt((stds ** 2).sum())) for j in wh_ids}  # independent upper bound

    for iteration in range(max_iterations):

        if verbose:
            print(f"\n── Fixed-point iteration {iteration} ──")

        # ── 1. Build MILP ─────────────────────────────────────────────
        model = cp_model.CpModel()
        SCALE = 100   # ₹ → ₹100 units for CP-SAT integer safety

        # Variables
        y = {j: model.NewBoolVar(f'y_{j}') for j in wh_ids}
        x = {(j, i): model.NewIntVar(0, int(capacity[j]), f'x_{j}_{i}')
             for j in wh_ids for i in node_ids}
        q = {j: model.NewIntVar(0, int(capacity[j]), f'q_{j}') for j in wh_ids}
        I = {j: model.NewIntVar(0, int(capacity[j]) * 4, f'I_{j}')  # inventory in units
             for j in wh_ids}

        # Objective
        obj = []

        # Fixed costs
        for j in wh_ids:
            obj.append(int(fixed_annual[j] / SCALE) * y[j])

        # Outbound transport (annual)
        for j in wh_ids:
            for i in node_ids:
                c = int(wh_node_cost.get((j, i), 999) * 52 / SCALE)
                obj.append(c * x[j, i])

        # Inbound transport (annual)
        for j in wh_ids:
            c = int(plant_wh_cost.get(j, 999) * 52 / SCALE)
            obj.append(c * q[j])

        # Variable handling cost (annual)
        for j in wh_ids:
            c = int(var_cost[j] * 52 / SCALE)
            obj.append(c * q[j])

        # Cycle inventory holding: h × (q_j × WEEKS_OF_CYCLE_STOCK)
        # Industry benchmark: 3 weeks of cycle inventory held at regional hubs
        WEEKS_OF_CYCLE_STOCK = 3.0
        for j in wh_ids:
            c = int(holding_per_unit * WEEKS_OF_CYCLE_STOCK / SCALE)
            obj.append(c * q[j])

        # SAA Lead-time inventory buffer cost (proportional to I[j])
        for j in wh_ids:
            c = int(holding_per_unit / SCALE)
            obj.append(c * I[j])

        # Safety stock holding: h × z × σ_pool × √L   (from current estimate)
        for j in wh_ids:
            ss_units = z * pooled_std_est[j] * np.sqrt(lead_weeks[j])
            c = int(ss_units * holding_per_unit / SCALE)
            obj.append(c * y[j])

        model.Minimize(sum(obj))

        # Constraints
        # (1) demand satisfaction
        for i in node_ids:
            model.Add(sum(x[j, i] for j in wh_ids) >= int(demand[i]))

        # (2) flow conservation
        for j in wh_ids:
            model.Add(q[j] == sum(x[j, i] for i in node_ids))

        # (3) capacity + linking
        for j in wh_ids:
            model.Add(q[j] <= int(capacity[j]) * y[j])

        # (4) big-M linking
        for j in wh_ids:
            for i in node_ids:
                model.Add(x[j, i] <= int(demand[i]) * y[j])

        # (5) SAA chance constraint: I_j covers lead-time demand in every scenario
        # Precompute per-scenario, per-warehouse lead-time demand as linear expr
        M = int(demand.sum() * 4)   # generous big-M
        for j in wh_ids:
            L_j = lead_weeks[j]
            for s in range(n_scenarios):
                # D_j^s = Σ_i x[j,i] × mult[s,i] × L_j
                # Scale constraint by 100 to avoid dividing CP-SAT LinearExpr by integer:
                # 100 * I[j] >= Σ_k int(mult * L_j * 100) * x[j,k] - 100 * M * (1 - y[j])
                expr = sum(
                    int(round(scenarios[s, k] * L_j * 100)) * x[j, node_ids[k]]
                    for k in range(n_nodes)
                )
                model.Add(100 * I[j] >= expr - 100 * M * (1 - y[j]))

        # (6) no inventory at closed warehouses
        for j in wh_ids:
            model.Add(I[j] <= int(capacity[j]) * 4 * y[j])

        # ── 2. Solve ──────────────────────────────────────────────────
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 120
        solver.parameters.num_search_workers = 8
        if verbose:
            solver.parameters.log_search_progress = False

        status = solver.Solve(model)

        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            print("MILP infeasible — check capacity vs demand")
            return None

        # ── 3. Extract assignment ─────────────────────────────────────
        open_wh = [j for j in wh_ids if solver.Value(y[j]) == 1]
        assignment = {j: [] for j in open_wh}
        flows = []
        for j in open_wh:
            for i in node_ids:
                v = solver.Value(x[j, i])
                if v > 0:
                    assignment[j].append(i)
                    flows.append({'warehouse': j, 'node': i, 'weekly_units': v})

        if verbose:
            print(f"  Open: {open_wh}")
            print(f"  Obj (scaled): {solver.ObjectiveValue():,.0f}")

        # ── 4. Update pooled std from new assignment ──────────────────
        new_pooled = pooled_std_for_assignment(assignment, stds, corr_matrix)
        for j in wh_ids:
            pooled_std_est[j] = new_pooled.get(j, 0.0)

        # Convergence check
        if prev_open is not None and set(open_wh) == set(prev_open):
            if verbose:
                print(f"  Converged after iteration {iteration}")
            break
        prev_open = open_wh

    # ── 5. Final cost breakdown ───────────────────────────────────────
    flows_df = pd.DataFrame(flows)

    total_fixed = sum(fixed_annual[j] for j in open_wh)
    total_transport = sum(
        r['weekly_units'] * wh_node_cost.get((r['warehouse'], r['node']), 0) * 52
        for _, r in flows_df.iterrows()
    )
    total_inbound = sum(
        solver.Value(q[j]) * plant_wh_cost.get(j, 0) * 52 for j in open_wh
    )
    total_variable = sum(
        solver.Value(q[j]) * var_cost[j] * 52 for j in open_wh
    )

    # Inventory: cycle + safety (correlated, from final assignment)
    inv_rows = []
    total_inv_cost = 0.0
    WEEKS_OF_CYCLE_STOCK = 3.0  # Industry benchmark: 3 weeks cycle buffer at RDC
    for j in open_wh:
        q_j = solver.Value(q[j])
        cycle_units = q_j * WEEKS_OF_CYCLE_STOCK   # 3 weeks cycle stock
        ss_units = z * pooled_std_est[j] * np.sqrt(lead_weeks[j])
        total_units = cycle_units + ss_units
        cost = total_units * holding_per_unit
        total_inv_cost += cost
        inv_rows.append({
            'warehouse': j,
            'cycle_stock': cycle_units,
            'safety_stock': ss_units,
            'total_inventory': total_units,
            'annual_holding_cost': cost,
            'pooled_std': pooled_std_est[j],
        })
    inv_df = pd.DataFrame(inv_rows)

    grand_total = total_fixed + total_transport + total_inbound + total_variable + total_inv_cost

    result = {
        'status': 'OPTIMAL' if status == cp_model.OPTIMAL else 'FEASIBLE',
        'service_level': service_level,
        'open_warehouses': open_wh,
        'total_annual_cost': grand_total,
        'fixed_cost': total_fixed,
        'transport_cost': total_transport,
        'inbound_cost': total_inbound,
        'variable_cost': total_variable,
        'inventory_cost': total_inv_cost,
        'flows': flows_df,
        'inventory': inv_df,
        'iterations_used': iteration + 1,
        'n_scenarios': n_scenarios,
    }

    if verbose:
        print(f"\n{'='*55}")
        print(f"OPTIMAL NETWORK at {service_level:.0%} service level")
        print(f"{'='*55}")
        print(f"Open warehouses:  {open_wh}")
        print(f"Fixed:            ₹{total_fixed:,.0f}")
        print(f"Transport:        ₹{total_transport:,.0f}")
        print(f"Inbound:          ₹{total_inbound:,.0f}")
        print(f"Variable:         ₹{total_variable:,.0f}")
        print(f"Inventory:        ₹{total_inv_cost:,.0f}")
        print(f"TOTAL:            ₹{grand_total:,.0f}")
        print(f"{'='*55}")

    return result

if __name__ == '__main__':
    nodes = pd.read_csv('data/processed/demand_nodes_anchored.csv')
    warehouses = pd.read_csv('data/processed/candidate_warehouses.csv')
    transport_costs = pd.read_csv('data/processed/transport_costs.csv')
    corr_matrix = pd.read_csv('data/processed/correlation_matrix.csv', index_col=0)

    res = solve_network_design(
        nodes=nodes,
        warehouses=warehouses,
        transport_costs=transport_costs,
        corr_matrix=corr_matrix,
        service_level=0.95,
        n_scenarios=50,
        verbose=True
    )
