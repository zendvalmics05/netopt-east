# Supply Chain Network Design for FMCG Distribution in Eastern India
**NETOPT-EAST v2.0 · Comprehensive Technical & Executive Defense Report**

---

## Executive Summary
- **The Challenge:** An FMCG manufacturer distributes personal care/packaged goods across 40 major consumption nodes in 5 Eastern Indian states (West Bengal, Bihar, Odisha, Jharkhand, Assam) from a single manufacturing plant in Dankuni, WB. The legacy operating model relies on direct plant-to-node LTL transport, resulting in an annual landed logistics cost of **₹59.66 Crore**, zero inventory risk-pooling, and replenishment lead times spanning 2 to 7 days.
- **The Method:** We formulated a **chance-constrained Mixed-Integer Linear Program (MILP)** solved via OR-Tools CP-SAT. The formulation features:
  - **Sample Average Approximation (SAA)** with correlated scenarios integrated directly into the objective and lead-time constraints (not computed post-hoc).
  - **Fixed-point iteration** on spatial correlation ($\rho_{ij} = \rho_0 \cdot \exp(-d_{ij}/200\text{ km})$) to rigorously capture the square-root pooling law with spatial decay.
  - **Real-anchored demand:** Derived from Census 2011 urban populations, state-level IBEF FMCG per-capita spend, a 10% target addressable market penetration factor ($0.10$), and Tier-weighted consumption multiples. Zero unanchored random demand.
  - **Realistic facility accounting:** Fully loaded monthly warehouse lease and facility operating expenses (₹32–₹58/sqft/mo covering base rent, CAM, security, WMS, and admin labor) combined with variable piece-rate handling at ₹1.0/unit and 3 weeks of cycle stock buffering.
- **The Strategic Finding:** At a 95% service level, the optimal configuration opens **all 6 regional distribution centers (RDCs)** (Kolkata, Bhubaneswar, Patna, Ranchi, Guwahati, and Siliguri), reducing annual landed supply chain spend from **₹59.66 Crore to ₹51.09 Crore**—delivering **₹8.56 Crore in annual savings (14.35% landed cost reduction)**.
- **Cost-Service Frontier:** Mapped across fill rates from 90% to 99.99%. Moving from 95% to 99% fill rate requires a **41.4% increase in safety stock**, but incurs only **+₹9.35 Lakh/year (+0.18%)** in total logistics budget because transport consolidation and fixed facilities dominate annual spend.
- **Resilience:** Under 500 Monte Carlo scenarios (joint demand, transport rate, and lead time variance), the network achieves a **100% feasibility rate** with a tight cost coefficient of variation of **7.6%**. The 95th-percentile adverse annual cost is **₹57.94 Crore**, proving the network remains cheaper in a 1-in-20-year crisis than the legacy direct-ship baseline in a normal year.

---

## 1. Real-Anchored Data Foundation (Why the Numbers are Defensible)

Standard portfolio projects frequently employ `np.random.uniform` to synthesize demand and arbitrary unit costs. In NETOPT-EAST, every model parameter is traced to verified public benchmarks:

1. **Demand Calibration:**
   - **Baseline Population:** 2011 Census of India city populations across 40 Tier-1/2/3 urban agglomerations in Eastern India.
   - **Market Penetration:** Calibrated to an addressable target market share of **10% of urban population** ($0.10 \times \text{Population}$), reflecting a single competitive enterprise brand footprint.
   - **Consumption Spend:** IBEF and Nielsen FMCG Eastern India annual per-capita consumption estimates (₹1,500–₹2,200/year adjusted by state economic indicators).
   - **Urban Tier Multiplier:** Tier 1 (1.4×), Tier 2 (1.1×), Tier 3 (0.85×) reflecting urban disposable income and organized retail penetration.
   - **SKU Valuation:** Representative unit retail price of ₹90/unit ($C = 90$).
2. **Transportation Economics:**
   - **Primary Plant-to-Warehouse:** Freight rates anchored to Indian Banks' Association (IBA) National Truck Freight Indices for multi-axle 16-tonne full-truckloads (FTL) at ₹4.20/tonne-km ($\approx$ ₹0.00105/unit-km).
   - **Secondary Warehouse-to-Node:** LTL consolidated transport at ₹9.50/tonne-km with a ₹2.5/unit local delivery minimum.
   - **Dynamic Transit Lead Time:** Computed using realistic ground routing: $\text{Lead Time} = \max\left(2, \left\lfloor\frac{d_{ij} \times 1.3}{300\text{ km/day}}\right\rfloor + 1\right)$ days, accounting for 1.3× highway circuity and commercial vehicle transit speeds.
3. **Fully Loaded Facility Costs:**
   - Knight Frank and JLL Industrial Logistics Warehouse Benchmarks (Q3 2024 / 2025):
     - Grade-A Base Rents: ₹20 to ₹28/sqft/month.
     - Common Area Maintenance (CAM): ₹4 to ₹5/sqft/month.
     - Supervision, WMS, Utilities & Security: ₹8 to ₹15/sqft/month.
     - **Fully Loaded Monthly Fixed Cost:** ₹32 to ₹58/sqft/month across Kolkata, Bhubaneswar, Patna, Ranchi, Guwahati, and Siliguri.
   - Variable piece-rate handling labor: Fixed at **₹1.0/unit** to avoid double-counting salaried facility personnel already captured in the monthly lease base.

---

## 2. Mathematical Formulation & Optimization Architecture

The model is formulated as a Chance-Constrained Mixed-Integer Linear Program (MILP) solved via OR-Tools CP-SAT using an integer-scaled penalty objective ($100\times$ integer resolution).

### 2.1 Optimization Formulation

$$\min \sum_{j \in \mathcal{W}} F_j y_j + \sum_{p \in \mathcal{P}} \sum_{j \in \mathcal{W}} c_{pj}^{\text{in}} x_{pj} + \sum_{j \in \mathcal{W}} \sum_{i \in \mathcal{N}} c_{ji}^{\text{out}} x_{ji} + \sum_{j \in \mathcal{W}} v_j q_j + \sum_{j \in \mathcal{W}} h \cdot \left(q_j \cdot W_{\text{cycle}} + z_\alpha \cdot \sigma_j^{\text{pool}} \sqrt{\frac{L_j}{7}}\right)$$

**Subject to:**
1. **Demand Satisfaction:** $\sum_{j \in \mathcal{W}} x_{ji} = d_i, \quad \forall i \in \mathcal{N}$
2. **Flow Balance at Hubs:** $q_j = \sum_{i \in \mathcal{N}} x_{ji} = \sum_{p \in \mathcal{P}} x_{pj}, \quad \forall j \in \mathcal{W}$
3. **Capacity Constraints:** $q_j \le K_j \cdot y_j, \quad \forall j \in \mathcal{W}$
4. **Single Sourcing / Primary Assignment:** $x_{ji} \le d_i \cdot a_{ji}, \quad \sum_{j} a_{ji} = 1$
5. **Sample Average Approximation (SAA) Chance-Constraint Buffer:**
   $$100 \cdot I_j \ge \sum_{i \in \mathcal{N}} a_{ji} \cdot d_{is} \cdot \left(\frac{L_j}{7}\right) - 100 \cdot M (1 - y_j), \quad \forall s \in \{1,\dots,S\}$$

### 2.2 Correlated Spatial Pooling & Fixed-Point Iteration
The pooled variance at warehouse $j$ serving assignment set $\mathcal{N}_j$ is given by:
$$\sigma_j^{\text{pool}} = \sqrt{\sum_{i \in \mathcal{N}_j} \sum_{k \in \mathcal{N}_j} \sigma_i \sigma_k \rho_{ik}}$$
where $\rho_{ik} = \rho_0 \cdot \exp(-d_{ik} / 200\text{ km})$. 

Because the assignment variables $a_{ji}$ enter non-linearly inside the square-root, standard solvers cannot optimize this directly in a single pass. We implemented a **Fixed-Point Iteration Algorithm**:
1. **Step 0:** Solve MILP with unpooled decentralized variance $\sigma_j^{(0)} = \sum_{i} \sigma_i$.
2. **Step 1:** Extract the optimal cluster assignments $\mathcal{N}_j^{(t)}$.
3. **Step 2:** Compute true correlated pooled standard deviation $\sigma_j^{(t)}$ via Cholesky covariance matrix decomposition.
4. **Step 3:** Update objective inventory coefficients and re-solve.
5. **Convergence:** The algorithm reaches stable warehouse selection within **1 to 2 iterations**.

---

## 3. Results & Strategic Analysis

### 3.1 Baseline vs. Optimal Network Configuration (95% Service Level)

| Cost Component | Legacy Baseline (Direct Plant LTL) | Optimal Multi-Hub Network (95% SL) | Absolute Savings | % Share of Optimal Cost |
| :--- | :---: | :---: | :---: | :---: |
| **Primary Inbound Freight** | ₹0 | ₹6.50 Crore | -₹6.50 Cr | 12.7% |
| **Secondary Outbound Freight**| ₹59.66 Crore | ₹20.40 Crore | +₹39.26 Cr | 39.9% |
| **Fixed Facility Leases** | ₹0 | ₹15.61 Crore | -₹15.61 Cr | 30.6% |
| **Variable Handling Labor** | ₹0 | ₹3.64 Crore | -₹3.64 Cr | 7.1% |
| **Inventory Holding (Cycle + SS)**| ₹0 (Passed to nodes) | ₹4.95 Crore | -₹4.95 Cr | 9.7% |
| **TOTAL ANNUAL EXPENDITURE** | **₹59.66 Crore** | **₹51.09 Crore** | **+₹8.56 Crore (+14.35%)**| **100.0%** |

**Why all 6 Warehouses Open:**
In a geographically dispersed region like Eastern India (spanning over 1,000 km between Dankuni and Upper Assam), linehaul LTL freight rates quickly escalate over distances exceeding 400 km. Opening local regional distribution centers in Guwahati, Patna, Siliguri, Ranchi, and Bhubaneswar allows bulk consolidated FTL linehauls from Dankuni, saving more in freight than the facilities cost in monthly rent.

---

### 3.2 The Cost-Service Frontier: Quantifying the Fill Rate Premium

Solving the MILP across service levels $\alpha \in \{90\%, 95\%, 98\%, 99\%, 99.5\%, 99.9\%, 99.99\%\}$ yields the Pareto frontier:

| Target Service Level ($\alpha$) | $z_\alpha$ | Safety Stock Units | Annual Safety Stock Cost | Total Network Cost | $\Delta$ vs. 95% Baseline |
| :---: | :---: | :---: | :---: | :---: | :---: |
| **90.00%** | 1.282 | 78,236 | ₹17.60 Lakh | ₹51.04 Crore | -₹4.98 Lakh (-0.10%) |
| **95.00%** | 1.645 | 100,389 | ₹22.59 Lakh | ₹51.09 Crore | **Baseline (₹0)** |
| **98.00%** | 2.054 | 125,349 | ₹28.20 Lakh | ₹51.15 Crore | +₹5.62 Lakh (+0.11%) |
| **99.00%** | 2.326 | 141,948 | ₹31.94 Lakh | ₹51.19 Crore | **+₹9.35 Lakh (+0.18%)** |
| **99.50%** | 2.576 | 157,205 | ₹35.37 Lakh | ₹51.22 Crore | +₹12.78 Lakh (+0.25%) |
| **99.90%** | 3.090 | 188,572 | ₹42.43 Lakh | ₹51.29 Crore | +₹19.84 Lakh (+0.39%) |
| **99.99%** | 3.719 | 226,958 | ₹51.07 Lakh | ₹51.38 Crore | +₹28.48 Lakh (+0.56%) |

**Strategic Takeaway:**
- While moving from 95% to 99% fill rate requires **+41.4% additional safety stock**, total network cost increases by only **+0.18% (+₹9.35 Lakh/year)**.
- Reaching extreme "four nines" reliability (99.99%) more than doubles safety stock (+126%), yet adds only **+₹28.48 Lakh/year (+0.56%)** to the overall logistics budget.
- **Stockout Economics:** Assuming a retail contribution margin loss of ₹50/unit, moving to 99% fill rate is commercially justified if annual stockout losses exceed 18,700 units (representing just 0.05% of regional sales).

---

### 3.3 Correlation Erodes the Square-Root Pooling Benefit

We evaluated the erosion of risk-pooling efficiency under varying spatial demand correlation levels $\rho_0 \in \{0.0, 0.3, 0.6, 1.0\}$:

| Base Correlation ($\rho_0$) | Safety Stock Cost (₹) | Pooling Benefit vs. No-Pooling (%) | Theoretical Expectation |
| :---: | :---: | :---: | :--- |
| **$\rho_0 = 0.0$ (Independent)** | **₹18.18 Lakh** | **65.8%** | Maximum textbook square-root diversification |
| **$\rho_0 = 0.3$ (Realistic Base)** | **₹20.95 Lakh** | **60.6%** | Realistic regional economic co-movement |
| **$\rho_0 = 0.6$ (High Co-movement)**| **₹23.36 Lakh** | **56.1%** | Substantial regional macroeconomic correlation |
| **$\rho_0 = 1.0$ (Extreme Local Peak)**| **₹26.20 Lakh** | **50.7%** | Spatial distance decay preserves ~50% benefit |

**The Geographic Insight:**
Why does the network preserve a **50.7% safety stock reduction** even when base local correlation is $\rho_0 = 1.0$?
Because correlation decays exponentially with distance ($d_0 = 200\text{ km}$). Two demand centers 500 km apart have a pairwise correlation of less than 0.10. Therefore, wide geographic dispersion across Eastern India provides natural portfolio diversification that macro-level demand shocks cannot fully erode.

---

### 3.4 Operational Robustness: Monte Carlo & Stress Test Scorecard

#### A. 500-Scenario Monte Carlo Simulation
- **Feasibility Rate:** **100% (500 / 500)** — Capacities comfortably absorb demand surges.
- **Expected Mean Cost:** **₹51.54 Crore** (vs. ₹51.09 Cr deterministic).
- **Cost CV:** **7.62%** — Highly predictable cost envelope.
- **95th Percentile Cost:** **₹57.94 Crore** (+13.4% budget tail).
- **Crucial Finding:** The 95th-percentile worst-case cost under extreme market volatility (₹57.94 Cr) is **lower than the legacy direct-to-market baseline under normal conditions (₹59.66 Cr)**.

#### B. Disruption Stress Scorecard

| Disruption Event | Stressed Cost | $\Delta$ vs. Base | Critical Vulnerability & Operational Response |
| :--- | :---: | :---: | :--- |
| **COVID-Style Demand Shock** | ₹51.91 Crore | **+1.60%** | Volatility absorbed through regional buffer inventory. |
| **NH-19 Highway Closure** | ₹51.09 Crore | **0.00%** | **Structurally immune**: Localized hubs in Patna & Ranchi already serve western nodes. |
| **Kolkata Hub Failure** | ₹85.71 Crore | **+67.75%** | **Critical Single Point of Failure**: Shifting 350k units/week to peripheral hubs causes severe freight escalation. Contracted 3PL backup required in Dankuni. |
| **Fuel Price Spike (+40%)** | ₹61.89 Crore | **+21.13%** | Direct freight pass-through; network structure remains stable without closing hubs. |

---

## 4. Modeling Limitations & Boundary Conditions
1. **Static Lead Times in Baseline:** Transit lead times are calculated deterministically using distance and commercial highway speeds; real-world monsoon delays and interstate border friction add stochastic lead-time variance ($\sigma_L$).
2. **Aggregated Urban Catchments:** Demand is modeled across 40 strategic commercial clusters rather than individual kirana store endpoints, reflecting strategic network design practice.
3. **Census 2011 Anchor:** Baseline populations are anchored to Census 2011 figures scaled by published urbanization growth rates due to the absence of Census 2021 data.

---

## 5. Executive Conclusion & Recommendations
1. **Network Transformation:** Transition from the single-plant direct shipping model to the 6-hub regional distribution network to capture **₹8.56 Crore in annual savings (14.35%)** while cutting average delivery lead times from 5 days to 24–48 hours.
2. **Target Service Level:** Commit to a **98% or 99% customer fill rate** target. The marginal annual cost premium is negligible (+₹9.35 Lakh/yr) compared to the commercial brand equity and lost sales protection it provides.
3. **Risk Mitigation:** Establish a contingency 3PL overflow contract in the Kolkata/Howrah logistics belt to insulate against the catastrophic operational risk (+67.8% cost impact) of a primary hub outage.
