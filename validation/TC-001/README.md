# TC-001: Warehouse Location & Transport Tradeoff (2 Warehouses, 3 Nodes)

## 1. Problem Description
Validate that the MILP model correctly solves the classical facility location tradeoff:
opening fewer facilities saves fixed costs but incurs higher outbound transport costs; opening more facilities saves transport costs but incurs higher fixed costs.

## 2. Problem Setup
- **Candidate Warehouses:**
  - `WH1`: Annual Fixed Cost = ₹10,00,000 (₹10 Lakh).
  - `WH2`: Annual Fixed Cost = ₹8,00,000 (₹8 Lakh).
- **Demand Nodes:**
  - `Node A`: Weekly Demand = 500 units. Near `WH1` (transport ₹1/unit), far from `WH2` (transport ₹10/unit).
  - `Node B`: Weekly Demand = 500 units. Near `WH2` (transport ₹1/unit), far from `WH1` (transport ₹10/unit).
  - `Node C`: Weekly Demand = 300 units. Equidistant from both (transport ₹5/unit from either).
- Inbound Plant Transport: ₹0.
- Variable Handling: ₹0.
- Annual multiplier: 52 weeks.

## 3. Analytical Hand Calculation
We enumerate all candidate configurations:

### Configuration 1: Open `WH1` Only
- Fixed Cost = ₹10,00,000
- Weekly Outbound Transport:
  - Node A: $500 \times ₹1 = ₹500$
  - Node B: $500 \times ₹10 = ₹5,000$
  - Node C: $300 \times ₹5 = ₹1,500$
  - Total Weekly Transport = ₹7,000
  - Annual Transport = $₹7,000 \times 52 = ₹3,64,000$
- **Total Annual Cost = ₹10,00,000 + ₹3,64,000 = ₹13,64,000**

### Configuration 2: Open `WH2` Only
- Fixed Cost = ₹8,00,000
- Weekly Outbound Transport:
  - Node A: $500 \times ₹10 = ₹5,000$
  - Node B: $500 \times ₹1 = ₹500$
  - Node C: $300 \times ₹5 = ₹1,500$
  - Total Weekly Transport = ₹7,000
  - Annual Transport = $₹7,000 \times 52 = ₹3,64,000$
- **Total Annual Cost = ₹8,00,000 + ₹3,64,000 = ₹11,64,000**

### Configuration 3: Open BOTH `WH1` and `WH2`
- Fixed Cost = ₹10,00,000 + ₹8,00,000 = ₹18,00,000
- Weekly Outbound Transport:
  - Node A served from WH1: $500 \times ₹1 = ₹500$
  - Node B served from WH2: $500 \times ₹1 = ₹500$
  - Node C served from either: $300 \times ₹5 = ₹1,500$
  - Total Weekly Transport = ₹2,500
  - Annual Transport = $₹2,500 \times 52 = ₹1,30,000$
- **Total Annual Cost = ₹18,00,000 + ₹1,30,000 = ₹19,30,000**

### Conclusion
Opening only `WH2` is mathematically optimal with a total cost of **₹11,64,000**.

## 4. Model Verification Result
The OR-Tools CP-SAT model selected:
- `open_warehouses`: `['WH2']`
- `fixed_cost`: `₹800,000`
- `transport_cost`: `₹364,000`
- `total_annual_cost`: `₹1,164,000`
- **Error vs Hand Calculation:** **0.00% (Exact Match)**.
