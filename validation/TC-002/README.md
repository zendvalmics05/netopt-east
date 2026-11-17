# TC-002: Spatial Correlation & Inventory Pooling Verification

## 1. Problem Description
Verify that the model's correlated inventory pooling module (`src/optimization/inventory.py`) mathematically follows the analytical correlated portfolio variance formula:
$$\sigma_{\text{pool}} = \sqrt{\boldsymbol{\sigma}^T \boldsymbol{\Sigma} \boldsymbol{\sigma}} = \sqrt{\sum_i \sigma_i^2 + 2 \sum_{i < j} \sigma_i \sigma_j \rho_{ij}}$$

## 2. Problem Setup
- 1 warehouse serving 2 demand nodes (`N1` and `N2`).
- Weekly demand standard deviation: $\sigma_1 = 100\text{ units}$, $\sigma_2 = 100\text{ units}$.

## 3. Analytical Hand Calculation

### Case A: Independent Demands ($\rho = 0.0$)
According to the classical Square-Root Law of inventory pooling:
$$\sigma_{\text{pool}} = \sqrt{100^2 + 100^2} = \sqrt{20,000} \approx 141.4214\text{ units}$$

### Case B: Perfect Spatial Correlation ($\rho = 1.0$)
When regional demands are perfectly correlated (e.g. shared regional economic shocks, regional festivals):
$$\sigma_{\text{pool}} = \sqrt{100^2 + 100^2 + 2(100)(100)(1.0)} = \sqrt{40,000} = 200.0000\text{ units}$$
Notice that when $\rho = 1$, the pooling benefit completely vanishes ($\sigma_{\text{pool}} = \sigma_1 + \sigma_2 = 200$).

## 4. Verification Result
- Model Output for $\rho = 0.0$: `141.4214 units` (Error: 0.00%)
- Model Output for $\rho = 1.0$: `200.0000 units` (Error: 0.00%)
- **Status:** **PASSED**.
