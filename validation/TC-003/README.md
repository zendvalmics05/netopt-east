# TC-003: Single-Warehouse, Single-Node End-to-End Hand Verification

## 1. Problem Description
Verify end-to-end integration of transport, cycle inventory holding, and chance-constrained safety stock on an analytically solvable 1-warehouse, 1-node network.

## 2. Problem Setup
- **Nodes:** 1 node (`N001`), mean demand $d = 1,000\text{ units/week}$, demand std $\sigma = 200\text{ units/week}$.
- **Warehouses:** 1 warehouse (`WH1`), fixed cost $f = ₹0$, variable handling = $₹0$, lead time $L = 7\text{ days} = 1.0\text{ week}$.
- **Transport Cost:** $c = ₹5.0\text{ / unit}$.
- **Holding Cost:** $h = ₹25.0\text{ / unit / year}$ (Holding rate 25% on product value ₹100).
- **Service Level:** $\alpha = 0.95 \implies z_\alpha = 1.645$.

## 3. Analytical Hand Calculation

1. **Flow & Transport Cost:**
   - Weekly flow $x = 1,000\text{ units/week}$.
   - Annual Transport Cost = $1,000 \times ₹5.0 \times 52 = \mathbf{₹2,60,000}$.

2. **Cycle Inventory Holding Cost:**
   - Operational cycle buffer = $3.0\text{ weeks} \implies 3,000\text{ units}$.
   - Cycle Holding Cost = $3,000 \times ₹25.0 = \mathbf{₹75,000}$.
   *(Note: under a 1-week buffer assumption, this would be $1,000 \times ₹25 = ₹25,000$)*.

3. **Safety Stock Holding Cost:**
   - Safety stock units $SS = z_\alpha \times \sigma \times \sqrt{L} = 1.645 \times 200 \times \sqrt{1.0} = 329\text{ units}$.
   - Safety Stock Holding Cost = $329 \times ₹25.0 = \mathbf{₹8,225}$.

4. **Total Expected Annual Cost:**
   $$\text{Total Cost} = ₹2,60,000 + ₹75,000 + ₹8,225 = \mathbf{₹3,43,225}$$

## 4. Model Verification Result
Running `solve_network_design()` with the exact TC-003 inputs produced:
- `transport_cost`: `₹260,000`
- `inventory_cost`: `₹83,225` (Cycle ₹75,000 + Safety stock ₹8,225)
- `total_annual_cost`: `₹343,225`
- **Error vs Hand Calculation:** **0.00% (Exact Match)**.
