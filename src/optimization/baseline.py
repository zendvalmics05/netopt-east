"""
Calculate baseline cost: current network with direct plant-to-node shipments.
"""

import pandas as pd
import numpy as np
from geopy.distance import geodesic

def calculate_baseline_cost(demand_nodes, transport_costs):
    """
    Calculate total cost of current direct-shipment network.

    Current model:
    - No warehouses
    - Plant ships directly to each demand node
    - Each node holds its own safety stock
    - Transport is LTL (small shipments)
    """

    # Plant location
    PLANT = {'latitude': 22.60, 'longitude': 88.40}

    # 1. TRANSPORT COST
    total_transport_cost = 0
    transport_details = []

    for _, node in demand_nodes.iterrows():
        dist_km = geodesic(
            (PLANT['latitude'], PLANT['longitude']),
            (node['latitude'], node['longitude'])
        ).km

        # LTL cost from plant to node
        # Assume higher cost for long-distance direct shipment
        cost_per_unit = (dist_km / 100) * 6  # ₹6 per unit per 100 km (premium for direct)

        weekly_volume = node['demand_mean_units_per_week']
        weekly_transport_cost = weekly_volume * cost_per_unit
        annual_transport_cost = weekly_transport_cost * 52

        total_transport_cost += annual_transport_cost

        transport_details.append({
            'node_id': node['node_id'],
            'city': node['city'],
            'distance_km': round(dist_km, 1),
            'weekly_volume': weekly_volume,
            'cost_per_unit': round(cost_per_unit, 2),
            'annual_cost': round(annual_transport_cost, 0),
        })

    # 2. INVENTORY COST (safety stock at each node)
    # Safety stock = z * σ * √(lead time)
    # z = 2.326 for 99% service level
    # Lead time = current lead time from plant to node

    Z_99 = 2.326  # Service level factor
    HOLDING_COST_RATE = 0.31  # 31% of product value per year
    PRODUCT_VALUE = 100  # ₹100 per unit (assumption)

    total_inventory_cost = 0
    inventory_details = []

    for _, node in demand_nodes.iterrows():
        # Safety stock calculation
        # σ_weekly = demand_std_units_per_week
        # Lead time in weeks
        # Road distance with circuity factor 1.3
        # Commercial freight speed ~300 km/day (NHAI benchmark) + 1 day order processing/dispatch
        lead_time_days = max(2, int(dist_km * 1.3 / 300) + 1)
        lead_time_weeks = lead_time_days / 7.0

        safety_stock = Z_99 * node['demand_std_units_per_week'] * np.sqrt(lead_time_weeks)

        # Average inventory = safety stock + half of cycle stock
        # For simplicity, assume cycle stock = 2 weeks demand
        cycle_stock = node['demand_mean_units_per_week'] * 2
        average_inventory = safety_stock + (cycle_stock / 2)

        # Annual holding cost
        annual_holding_cost = average_inventory * PRODUCT_VALUE * HOLDING_COST_RATE

        total_inventory_cost += annual_holding_cost

        inventory_details.append({
            'node_id': node['node_id'],
            'city': node['city'],
            'safety_stock': round(safety_stock, 0),
            'average_inventory': round(average_inventory, 0),
            'annual_holding_cost': round(annual_holding_cost, 0),
        })

    # 3. NO WAREHOUSE FIXED COSTS (current network has no warehouses)
    total_fixed_cost = 0

    # 4. STOCKOUT COST (estimate)
    # Assume 3% stockout rate in current network due to long lead times
    STOCKOUT_RATE = 0.03
    STOCKOUT_PENALTY_PER_UNIT = 40  # ₹40 per unit short (lost margin + goodwill)

    total_weekly_demand = demand_nodes['demand_mean_units_per_week'].sum()
    annual_stockout_cost = total_weekly_demand * 52 * STOCKOUT_RATE * STOCKOUT_PENALTY_PER_UNIT

    # SUMMARY
    total_cost = total_transport_cost + total_inventory_cost + total_fixed_cost + annual_stockout_cost

    result = {
        'total_annual_cost': total_cost,
        'transport_cost': total_transport_cost,
        'inventory_cost': total_inventory_cost,
        'fixed_cost': total_fixed_cost,
        'stockout_cost': annual_stockout_cost,
        'cost_per_unit': total_cost / (total_weekly_demand * 52),
        'transport_details': pd.DataFrame(transport_details),
        'inventory_details': pd.DataFrame(inventory_details),
    }

    return result

def cost_structure_summary(result: dict) -> dict:
    """Return cost breakdown percentages for benchmark triangulation."""
    total = result['total_annual_cost']
    return {
        'transport_pct': result['transport_cost'] / total,
        'inventory_pct': result['inventory_cost'] / total,
        'fixed_pct': result.get('fixed_cost', 0) / total,
        'stockout_pct': result.get('stockout_cost', 0) / total,
        'cost_per_unit': result['cost_per_unit'],
    }

if __name__ == '__main__':
    # Load data
    nodes = pd.read_csv('data/processed/demand_nodes_anchored.csv')

    # Calculate baseline
    baseline = calculate_baseline_cost(nodes, None)

    print("=" * 60)
    print("BASELINE NETWORK COST (Current: Direct from Plant)")
    print("=" * 60)
    print(f"Transport Cost:     ₹{baseline['transport_cost']:,.0f}")
    print(f"Inventory Cost:     ₹{baseline['inventory_cost']:,.0f}")
    print(f"Fixed Cost:         ₹{baseline['fixed_cost']:,.0f}")
    print(f"Stockout Cost:      ₹{baseline['stockout_cost']:,.0f}")
    print("-" * 60)
    print(f"TOTAL ANNUAL COST:  ₹{baseline['total_annual_cost']:,.0f}")
    print(f"Cost per Unit:      ₹{baseline['cost_per_unit']:.2f}")
    print("=" * 60)
    print(cost_structure_summary(baseline))

    # Save for comparison
    import json
    with open('data/processed/baseline_cost.json', 'w') as f:
        json.dump({k: v for k, v in baseline.items() if not isinstance(v, pd.DataFrame)}, f, indent=2)

    print("\nBaseline saved to data/processed/baseline_cost.json")
