# NETOPT-EAST: Supply Chain Network Design for FMCG — Eastern India

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://netopt-east.streamlit.app)

A chance-constrained Mixed-Integer Linear Program (MILP) that optimizes the regional distribution network for FMCG goods across 40 Eastern Indian cities (West Bengal, Bihar, Odisha, Jharkhand, Assam). 

Features **endogenous safety stock optimization** via Sample Average Approximation (SAA), **spatial demand correlation** with distance decay, a complete **cost-service Pareto frontier (90%–99.99%)**, and **Monte Carlo + event-driven disruption stress testing**.

---

## Executive Summary of Results
- **Annual Landed Savings:** **₹8.56 Crore/year (-14.35%)** reduction in total network expenditure (from ₹59.66 Cr direct plant LTL down to ₹51.09 Cr multi-hub design).
- **Optimal Topology:** Opens all 6 regional distribution centers (Kolkata, Bhubaneswar, Patna, Ranchi, Guwahati, Siliguri) to eliminate expensive 800+ km secondary freight.
- **Cost-Service Frontier:** Pushing customer fill rate from 95% to 99% increases safety stock by **41.4%**, but adds only **+₹9.35 Lakh/year (+0.18%)** to total logistics spend.
- **Spatial Correlation:** Proves the textbook square-root pooling benefit erodes from **65.8% (at $\rho_0=0$)** to **60.6% (at realistic $\rho_0=0.3$)**, but stabilizes at **50.7%** due to geographic distance decay.
- **Robustness:** 500-scenario Monte Carlo achieves **100% feasibility** (CV = 7.6%). The 95th-percentile adverse cost (**₹57.94 Cr**) remains cheaper than the legacy direct-to-market baseline under normal conditions (**₹59.66 Cr**).
- **Single Point of Failure:** Kolkata_WH outage causes a **+67.8% cost blowout**, identifying it as the primary continuity vulnerability.

---

## Why It's Not a Tutorial Project

| Feature | Standard Tutorial / Course Project | NETOPT-EAST (This Implementation) |
| :--- | :--- | :--- |
| **Demand Generation** | `np.random.uniform()` or arbitrary numbers | **Anchored to Census 2011**, IBEF state spend, 10% market penetration factor, and urban-tier multipliers. |
| **Inventory Modeling** | Post-hoc calculation added after location solve | **Chance-constrained SAA buffer** inside the CP-SAT solver with fixed-point iteration on pooled variance. |
| **Service Level** | Fixed at 95% single point | **Pareto Frontier** mapped across 90%, 95%, 98%, 99%, 99.5%, 99.9%, and 99.99%. |
| **Demand Correlation** | Assumed independent ($\rho=0$) | **Spatial exponential decay** ($\rho_0 e^{-d/200}$) with Cholesky scenario synthesis; sensitivity tested. |
| **Facility Economics** | Base rent only | **Fully loaded lease accounting** (base rent + CAM + security/WMS + management) at ₹32–₹58/sqft/mo. |
| **Resilience Analysis** | None | **500-scenario Monte Carlo** and 4 named macro disruption stress tests (COVID, NH-19, hub failure, fuel spike). |
| **Interactive UI** | Static Jupyter notebook only | **Interactive Streamlit Web Dashboard** with Folium geospatial routing and dynamic scenario filters. |

---

## Project Structure

```
netopt-east/
├── app/
│   └── streamlit_app.py           # Interactive web dashboard
├── data/
│   ├── raw/                       # Ground-truth raw benchmarks (Census, rents, freight)
│   └── processed/                 # Processed matrices, costs, and simulation results
├── notebooks/
│   ├── 01_data_anchoring.ipynb    # Data derivation & spatial correlation
│   ├── 02_baseline.ipynb          # Legacy direct-to-market baseline
│   ├── 03_model_formulation.ipynb # MILP CP-SAT formulation & validation benchmarks
│   ├── 04_frontier.ipynb          # Cost-Service Frontier & Correlation Sensitivity
│   └── 05_stress_tests.ipynb      # Monte Carlo & Disruption Scorecard
├── reports/
│   ├── figures/                   # Interactive HTML charts and 300 DPI publication PNGs
│   └── final_report.md            # Comprehensive technical & business defense report
├── src/
│   ├── data/                      # Demand anchoring & spatial covariance builder
│   ├── optimization/              # CP-SAT MILP solver, SAA, inventory, and frontier
│   ├── simulation/                # Monte Carlo and event stress testing engines
│   └── visualization/             # Plotly publication visualization routines
├── tests/
│   └── regression/                # Pytest benchmark test cases (TC-001, TC-002, TC-003)
└── requirements.txt               # Pinned reproducible dependencies
```

---

## How to Run Locally

### 1. Setup Virtual Environment
```bash
python -m venv .venv
.venv\Scripts\activate       # Windows (or source .venv/bin/activate on Linux/Mac)
pip install -r requirements.txt
```

### 2. Run Pipeline End-to-End
```bash
# Data Foundation (Phase 1)
python src/data/demand_builder.py
python src/data/correlation.py
python src/data/cost_anchor.py

# Baseline & MILP Optimization (Phase 2)
python src/optimization/baseline.py
python src/optimization/model.py

# Cost-Service Frontier & Correlation Sensitivity (Phase 3)
python src/optimization/frontier.py
python src/optimization/correlation_sensitivity.py

# Monte Carlo & Stress Tests (Phase 4)
python src/simulation/monte_carlo.py
python src/simulation/stress_tests.py

# Generate Visualizations & Interactive Charts
python src/visualization/cost_charts.py
```

### 3. Launch Interactive Dashboard
```bash
streamlit run app/streamlit_app.py
```

---

## Mathematical Validation
All models were cross-validated against 3 hand-solved deterministic and statistical test cases in `validation/`:
- **TC-001 (Location Trade-off):** 2-warehouse, 3-node facility trade-off matches exact hand-calculated threshold of ₹11,64,000.
- **TC-002 (Correlated Pooling):** Verification of $\sigma_{\text{pool}}$ under $\rho=0$ (141.42 units) vs $\rho=1$ (200.00 units) via Cholesky decomposition.
- **TC-003 (Inventory-Lead Time Trade-off):** Hand-solved single node safety stock and cycle stock exactly matches solver output at ₹343,225.

Run regression test suite:
```bash
pytest tests/
```

---

## License
MIT License. Open-source for academic, portfolio, and commercial supply chain research.
