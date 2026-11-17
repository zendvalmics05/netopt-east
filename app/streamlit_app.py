"""
NETOPT-EAST: Interactive Supply Chain Network Explorer
Deploy: streamlit run app/streamlit_app.py
Public URL: Streamlit Cloud or Hugging Face Spaces
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import folium
from streamlit_folium import st_folium
import json
import os

st.set_page_config(page_title="NETOPT-EAST Network Explorer", layout="wide")

# ── Load pre-computed results (no solving in the app — instant load) ──
@st.cache_data
def load_all():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    
    with open(os.path.join(base_dir, 'data/processed/baseline_cost.json'), 'r') as f:
        base = json.load(f)
    frontier = pd.read_csv(os.path.join(base_dir, 'data/processed/frontier_results.csv'))
    corr_sens = pd.read_csv(os.path.join(base_dir, 'data/processed/correlation_sensitivity.csv'))
    mc = pd.read_csv(os.path.join(base_dir, 'data/processed/mc_results.csv'))
    stress = pd.read_csv(os.path.join(base_dir, 'data/processed/stress_test_results.csv'))
    nodes = pd.read_csv(os.path.join(base_dir, 'data/processed/demand_nodes_anchored.csv'))
    whs = pd.read_csv(os.path.join(base_dir, 'data/processed/candidate_warehouses.csv'))
    flows = pd.read_csv(os.path.join(base_dir, 'data/processed/optimal_flows.csv'))
    return base, frontier, corr_sens, mc, stress, nodes, whs, flows

base, frontier, corr_sens, mc, stress, nodes, whs, flows = load_all()

# ── Sidebar controls ─────────────────────────────────────────────────
st.sidebar.title("NETOPT-EAST")
st.sidebar.caption("FMCG Network Design — Eastern India")
sl = st.sidebar.selectbox("Service Level Target", [0.90, 0.95, 0.98, 0.99], index=1)
rho = st.sidebar.slider("Spatial Correlation ρ₀", 0.0, 1.0, 0.3, 0.1)
show_stress = st.sidebar.checkbox("Show Stress Test Scorecard", True)

# ── Header ───────────────────────────────────────────────────────────
st.title("Supply Chain Network Design for FMCG — Eastern India")
st.markdown(
    "**Chance-constrained MILP · Real Census-anchored demand · "
    "Cost-service frontier · Monte Carlo robustness**"
)

# ── Row 1: KPIs ──────────────────────────────────────────────────────
row = frontier[frontier['service_level'] == sl]
if len(row):
    r = row.iloc[0]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Annual Cost", f"₹{r['total_cost']/1e7:.2f} Cr")
    c2.metric("Open Warehouses", f"{r['n_warehouses']} / 6 Active")
    c3.metric("Savings vs Direct Baseline",
              f"{100*(1 - r['total_cost']/base['total_annual_cost']):.1f}%")
    delta_99 = (frontier.loc[frontier['service_level']==0.99, 'total_cost'].values[0] -
                frontier.loc[frontier['service_level']==0.95, 'total_cost'].values[0])
    c4.metric("Cost of 99% vs 95% SL", f"₹{delta_99/1e5:.1f} Lakh/yr")

st.divider()

# ── Row 2: Frontier chart + Corrosion chart ─────────────────────────
col1, col2 = st.columns(2)

with col1:
    st.subheader("Cost-Service Frontier")
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=frontier['service_level'], y=frontier['total_cost']/1e6,
        mode='lines+markers', line=dict(color='#1f77b4', width=3), marker=dict(size=10),
        name='Total Annual Cost'
    ))
    fig.update_layout(xaxis_title='Customer Fill Rate', yaxis_title='Annual Cost (₹ Millions)',
                      height=350, margin=dict(l=0,r=0,t=30,b=0),
                      xaxis=dict(tickvals=[0.90, 0.95, 0.98, 0.99], ticktext=['90%', '95%', '98%', '99%']))
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("Correlation Erodes Pooling Benefit")
    fig2 = go.Figure(go.Scatter(
        x=corr_sens['rho_0'], y=corr_sens['pooling_benefit_pct'],
        mode='lines+markers', line=dict(color='#2ca02c', width=3),
        marker=dict(size=10), fill='tozeroy', fillcolor='rgba(44, 160, 44, 0.2)',
        name='Safety Stock Reduction'
    ))
    fig2.update_layout(xaxis_title='Spatial Correlation (ρ₀)', yaxis_title='SS Reduction vs No-Pooling (%)',
                       height=350, margin=dict(l=0,r=0,t=30,b=0))
    st.plotly_chart(fig2, use_container_width=True)

st.divider()

# ── Row 3: Network map ───────────────────────────────────────────────
st.subheader("Optimal Network Map: Distribution Hubs & Catchments")
m = folium.Map(location=[23.5, 87.5], zoom_start=6, tiles="OpenStreetMap")
open_wh = row['open_warehouses'].values[0].split(',') if len(row) else []

# Warehouse markers
for _, w in whs.iterrows():
    is_open = w['warehouse_id'] in open_wh
    folium.CircleMarker(
        [w['latitude'], w['longitude']],
        radius=12 if is_open else 6,
        color='blue' if is_open else 'gray',
        fill=True,
        fill_color='blue' if is_open else 'gray',
        fill_opacity=0.8 if is_open else 0.3,
        popup=f"<b>{w['warehouse_id']}</b><br>{'STATUS: OPEN' if is_open else 'STATUS: CLOSED'}<br>Capacity: {w['capacity_units_per_week']:,} u/wk",
    ).add_to(m)

# Demand node markers
for _, n in nodes.iterrows():
    folium.CircleMarker(
        [n['latitude'], n['longitude']],
        radius=max(3, min(10, n['demand_mean_units_per_week'] / 5000)),
        color='green',
        fill=True,
        fill_color='green',
        fill_opacity=0.4,
        popup=f"<b>{n['city']} ({n['state']})</b><br>Demand: {n['demand_mean_units_per_week']:,.0f} units/wk",
    ).add_to(m)

st_folium(m, width=1200, height=480)

# ── Row 4: Stress tests ──────────────────────────────────────────────
if show_stress:
    st.divider()
    st.subheader("Disruption Stress Tests & Continuity Scorecard")
    
    scorecard_display = stress[['event', 'stressed_cost', 'delta_pct', 'open_warehouses']].copy()
    scorecard_display['stressed_cost'] = scorecard_display['stressed_cost'].map(lambda x: f"₹{x/1e7:.2f} Cr")
    scorecard_display['delta_pct'] = scorecard_display['delta_pct'].map(lambda x: f"+{x:.1f}%")
    
    st.dataframe(scorecard_display, use_container_width=True)

# ── Footer ───────────────────────────────────────────────────────────
st.divider()
st.caption(
    "Data: Census 2011 × IBEF per-capita FMCG spend × published freight rates. "
    "Model: chance-constrained MILP (OR-Tools CP-SAT) with SAA scenario linearization."
)
