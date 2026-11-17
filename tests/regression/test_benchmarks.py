"""
Regression and benchmark validation tests for NETOPT-EAST Phase 2.5.
Codifies test cases TC-001, TC-002, and TC-003 with pytest.approx tolerances of 5%.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import pytest
import numpy as np
import pandas as pd
from src.optimization.model import solve_network_design
from src.optimization.inventory import pooled_std_for_assignment

def test_tc_003_single_warehouse_single_node():
    """
    TC-003: 1 WH, 1 Node.
    Analytically hand-solved baseline for transport + inventory integration.
    """
    nodes = pd.DataFrame([{
        'node_id': 'N001',
        'city': 'Node1',
        'state': 'State1',
        'latitude': 20.0,
        'longitude': 80.0,
        'tier': 1,
        'demand_mean_units_per_week': 1000,
        'demand_std_units_per_week': 200,
        'demand_cv': 0.2
    }])

    warehouses = pd.DataFrame([{
        'warehouse_id': 'WH1',
        'city': 'City1',
        'latitude': 20.0,
        'longitude': 80.0,
        'fixed_cost_monthly_rupees': 0.0,
        'variable_cost_per_unit': 0.0,
        'capacity_units_per_week': 5000,
        'lead_time_from_plant_days': 7,  # 1 week lead time
    }])

    transport_costs = pd.DataFrame([
        {'from_type': 'warehouse', 'from_id': 'WH1', 'to_type': 'node', 'to_id': 'N001', 'cost_per_unit': 5.0},
        {'from_type': 'plant', 'from_id': 'PLANT', 'to_type': 'warehouse', 'to_id': 'WH1', 'cost_per_unit': 0.0}
    ])

    corr = pd.DataFrame([[1.0]], index=['N001'], columns=['N001'])

    res = solve_network_design(
        nodes=nodes,
        warehouses=warehouses,
        transport_costs=transport_costs,
        corr_matrix=corr,
        service_level=0.95,
        holding_cost_rate=0.25,
        product_value=100.0,  # holding_per_unit = 25.0
        n_scenarios=50,
        verbose=False
    )

    assert res['open_warehouses'] == ['WH1']
    assert res['transport_cost'] == pytest.approx(260000.0, rel=0.05)
    # Hand calculation: Cycle (3 wks * 1000 * 25) = 75,000; SS = 1.645 * 200 * sqrt(1) * 25 = 8,225
    assert res['inventory_cost'] == pytest.approx(83225.0, rel=0.05)
    assert res['total_annual_cost'] == pytest.approx(343225.0, rel=0.05)

def test_tc_001_location_transport_tradeoff():
    """
    TC-001: 2 WH, 3 Nodes.
    Tests fixed facility cost vs outbound transportation cost tradeoff.
    Analytical minimum is WH2 only (Total = ₹1,164,000).
    """
    nodes = pd.DataFrame([
        {'node_id': 'A', 'city': 'A', 'state': 'S', 'latitude': 0, 'longitude': 0, 'tier': 1, 'demand_mean_units_per_week': 500, 'demand_std_units_per_week': 50, 'demand_cv': 0.1},
        {'node_id': 'B', 'city': 'B', 'state': 'S', 'latitude': 0, 'longitude': 0, 'tier': 1, 'demand_mean_units_per_week': 500, 'demand_std_units_per_week': 50, 'demand_cv': 0.1},
        {'node_id': 'C', 'city': 'C', 'state': 'S', 'latitude': 0, 'longitude': 0, 'tier': 1, 'demand_mean_units_per_week': 300, 'demand_std_units_per_week': 30, 'demand_cv': 0.1},
    ])

    warehouses = pd.DataFrame([
        {'warehouse_id': 'WH1', 'city': 'W1', 'latitude': 0, 'longitude': 0, 'fixed_cost_monthly_rupees': 1000000/12, 'variable_cost_per_unit': 0, 'capacity_units_per_week': 2000, 'lead_time_from_plant_days': 7},
        {'warehouse_id': 'WH2', 'city': 'W2', 'latitude': 0, 'longitude': 0, 'fixed_cost_monthly_rupees': 800000/12, 'variable_cost_per_unit': 0, 'capacity_units_per_week': 2000, 'lead_time_from_plant_days': 7},
    ])

    transport_costs = pd.DataFrame([
        {'from_type': 'warehouse', 'from_id': 'WH1', 'to_type': 'node', 'to_id': 'A', 'cost_per_unit': 1.0},
        {'from_type': 'warehouse', 'from_id': 'WH1', 'to_type': 'node', 'to_id': 'B', 'cost_per_unit': 10.0},
        {'from_type': 'warehouse', 'from_id': 'WH1', 'to_type': 'node', 'to_id': 'C', 'cost_per_unit': 5.0},
        {'from_type': 'warehouse', 'from_id': 'WH2', 'to_type': 'node', 'to_id': 'A', 'cost_per_unit': 10.0},
        {'from_type': 'warehouse', 'from_id': 'WH2', 'to_type': 'node', 'to_id': 'B', 'cost_per_unit': 1.0},
        {'from_type': 'warehouse', 'from_id': 'WH2', 'to_type': 'node', 'to_id': 'C', 'cost_per_unit': 5.0},
        {'from_type': 'plant', 'from_id': 'PLANT', 'to_type': 'warehouse', 'to_id': 'WH1', 'cost_per_unit': 0.0},
        {'from_type': 'plant', 'from_id': 'PLANT', 'to_type': 'warehouse', 'to_id': 'WH2', 'cost_per_unit': 0.0},
    ])

    corr = pd.DataFrame(np.eye(3), index=['A', 'B', 'C'], columns=['A', 'B', 'C'])

    res = solve_network_design(
        nodes=nodes,
        warehouses=warehouses,
        transport_costs=transport_costs,
        corr_matrix=corr,
        service_level=0.95,
        holding_cost_rate=0.0,
        product_value=0.0,
        verbose=False
    )

    assert res['open_warehouses'] == ['WH2']
    assert res['fixed_cost'] == pytest.approx(800000.0, rel=0.05)
    assert res['transport_cost'] == pytest.approx(364000.0, rel=0.05)
    assert res['total_annual_cost'] == pytest.approx(1164000.0, rel=0.05)

def test_tc_002_pooling_verification():
    """
    TC-002: Spatial correlation and inventory pooling analytical check.
    Tests rho=0 vs rho=1 pooled standard deviations.
    """
    stds = pd.Series({'N1': 100.0, 'N2': 100.0})

    # Independent case (rho = 0.0)
    corr_0 = pd.DataFrame([[1.0, 0.0], [0.0, 1.0]], index=['N1', 'N2'], columns=['N1', 'N2'])
    pooled_0 = pooled_std_for_assignment({'WH': ['N1', 'N2']}, stds, corr_0)['WH']
    expected_0 = np.sqrt(100**2 + 100**2)  # ~141.42
    assert pooled_0 == pytest.approx(expected_0, rel=0.01)

    # Perfect correlation case (rho = 1.0)
    corr_1 = pd.DataFrame([[1.0, 1.0], [1.0, 1.0]], index=['N1', 'N2'], columns=['N1', 'N2'])
    pooled_1 = pooled_std_for_assignment({'WH': ['N1', 'N2']}, stds, corr_1)['WH']
    expected_1 = 200.0  # linear sum
    assert pooled_1 == pytest.approx(expected_1, rel=0.01)
