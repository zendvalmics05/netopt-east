"""
Cost parameters anchored to published sources.

All rates loaded from data/raw/ CSVs you created in File 00 §5.3–5.4.
Every function docstring cites its source. If you change a number,
change the CSV, not this file.
"""

import pandas as pd
import numpy as np
from geopy.distance import geodesic

PLANT = {'name': 'Plant', 'latitude': 22.60, 'longitude': 88.40}

WAREHOUSES = {
    'Kolkata_WH':     {'city': 'Kolkata',     'lat': 22.5726, 'lon': 88.3639,
                       'capacity': 350000, 'lead_time_days': 1},
    'Bhubaneswar_WH': {'city': 'Bhubaneswar', 'lat': 20.2961, 'lon': 85.8245,
                       'capacity': 220000, 'lead_time_days': 2},
    'Patna_WH':       {'city': 'Patna',       'lat': 25.5941, 'lon': 85.1376,
                       'capacity': 225000, 'lead_time_days': 2},
    'Ranchi_WH':      {'city': 'Ranchi',      'lat': 23.3441, 'lon': 85.3096,
                       'capacity': 185000, 'lead_time_days': 2},
    'Guwahati_WH':    {'city': 'Guwahati',    'lat': 26.1445, 'lon': 91.7362,
                       'capacity': 188000, 'lead_time_days': 4},
    'Siliguri_WH':    {'city': 'Siliguri',    'lat': 26.7271, 'lon': 88.3953,
                       'capacity': 180000, 'lead_time_days': 3},
}

def load_rates():
    """Load freight and rent CSVs. Sources documented in the CSVs themselves."""
    freight = pd.read_csv('data/raw/freight_rates.csv')
    rents = pd.read_csv('data/raw/warehouse_rents.csv')
    return freight, rents

def haversine_road_km(lat1, lon1, lat2, lon2) -> float:
    """
    Road distance ≈ geodesic × 1.3 (road factor).
    Source: NHAI studies show road distances ~25–35% longer than straight-line
    for Indian highways; 1.3 is the midpoint. Document as assumption.
    """
    return geodesic((lat1, lon1), (lat2, lon2)).km * 1.3

def build_transport_costs(nodes: pd.DataFrame) -> pd.DataFrame:
    """
    Plant→WH: FTL. WH→node: LTL.
    FTL ₹/km from IBA truck hire rates (freight_rates.csv).
    LTL ₹/unit/100km from industry FMCG benchmarks (freight_rates.csv).
    """
    freight, _ = load_rates()
    ftl_rate = freight[freight['mode'] == 'FTL']['rate_per_km_inr'].values[0]
    ftl_cap = freight[freight['mode'] == 'FTL']['truck_capacity_units'].values[0]
    ltl_rate = freight[freight['mode'] == 'LTL']['rate_per_km_inr'].values[0]

    rows = []

    # Plant → warehouse (FTL)
    for wh_id, wh in WAREHOUSES.items():
        d = haversine_road_km(PLANT['latitude'], PLANT['longitude'],
                              wh['lat'], wh['lon'])
        cost_per_unit = d * ftl_rate / ftl_cap
        rows.append({
            'from_type': 'plant', 'from_id': 'PLANT',
            'to_type': 'warehouse', 'to_id': wh_id,
            'distance_km': round(d, 1), 'mode': 'FTL',
            'cost_per_unit': round(cost_per_unit, 2),
            'lead_time_days': wh['lead_time_days'],
            'rate_source': f'FTL ₹{ftl_rate}/km ÷ {ftl_cap} units/truck',
        })

    # Warehouse → node (LTL)
    for wh_id, wh in WAREHOUSES.items():
        for _, node in nodes.iterrows():
            d = haversine_road_km(wh['lat'], wh['lon'],
                                  node['latitude'], node['longitude'])
            cost_per_unit = (d / 100) * ltl_rate
            if d < 50:
                cost_per_unit = max(cost_per_unit, 3.0)
            rows.append({
                'from_type': 'warehouse', 'from_id': wh_id,
                'to_type': 'node', 'to_id': node['node_id'],
                'distance_km': round(d, 1), 'mode': 'LTL',
                'cost_per_unit': round(cost_per_unit, 2),
                'lead_time_days': max(1, int(d / 300)),
                'rate_source': f'LTL ₹{ltl_rate}/unit/100km',
            })

    return pd.DataFrame(rows)

def build_warehouse_table() -> pd.DataFrame:
    """
    Fixed costs from warehouse_rents.csv (fully loaded: lease rent + CAM + staff/admin + security/IT).
    Variable handling cost ₹1.0/unit (pure loading/unloading piece-rate labor, as supervisory/admin overhead is in fixed costs).
    """
    _, rents = load_rates()
    rows = []
    for wh_id, wh in WAREHOUSES.items():
        rent_row = rents[rents['city'] == wh['city']].iloc[0]
        monthly_rent = rent_row['rent_per_sqft_per_month_inr'] * rent_row['typical_warehouse_sqft']
        rows.append({
            'warehouse_id': wh_id,
            'city': wh['city'],
            'latitude': wh['lat'],
            'longitude': wh['lon'],
            'fixed_cost_monthly_rupees': monthly_rent,
            'variable_cost_per_unit': 1.0,  # ₹1.0/unit piece-rate labor; supervisory overhead in fixed
            'capacity_units_per_week': wh['capacity'],
            'lead_time_from_plant_days': wh['lead_time_days'],
            'cost_source': f"Knight Frank/JLL {rent_row['source_note']}",
        })
    return pd.DataFrame(rows)

if __name__ == '__main__':
    nodes = pd.read_csv('data/processed/demand_nodes_anchored.csv')
    costs = build_transport_costs(nodes)
    costs.to_csv('data/processed/transport_costs.csv', index=False)
    whs = build_warehouse_table()
    whs.to_csv('data/processed/candidate_warehouses.csv', index=False)

    print(f"Transport lanes: {len(costs)}")
    print(f"Warehouses: {len(whs)}")
    print(f"Total weekly capacity: {whs['capacity_units_per_week'].sum():,} units")
    print(f"Total weekly demand: {nodes['demand_mean_units_per_week'].sum():,.0f} units")
    print(f"Capacity/demand ratio: "
          f"{whs['capacity_units_per_week'].sum() / nodes['demand_mean_units_per_week'].sum():.2f}")
