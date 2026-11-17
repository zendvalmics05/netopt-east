"""
Demand scenario generator.

Generates S correlated demand-shock scenarios for all nodes.
Used by:
  - model.py  (SAA chance constraints, S=50)
  - monte_carlo.py (evaluation, S=500)

Correlation: scenarios drawn from multivariate normal with the spatial
correlation matrix built in Phase 1. This is what makes the chance
constraint "correlation-aware" without any nonlinear algebra in the MILP.
"""

import numpy as np
import pandas as pd

def generate_scenarios(nodes: pd.DataFrame,
                       corr_matrix: pd.DataFrame,
                       n_scenarios: int,
                       seed: int = 42) -> np.ndarray:
    """
    Return array of shape (n_scenarios, n_nodes).
    Each row is a demand multiplier ~ MVN(mean=1, cov=CV-weighted correlation).

    The multiplier has mean 1 and per-node std = node's CV, cross-node
    correlation from the spatial matrix. Truncated below at 0.1 to avoid
    negative demand.
    """
    rng = np.random.default_rng(seed)
    node_ids = nodes['node_id'].tolist()
    cv = nodes['demand_cv'].values          # per-node std of the multiplier
    n = len(node_ids)

    # Covariance of multipliers: diag(cv) @ corr @ diag(cv)
    C = corr_matrix.loc[node_ids, node_ids].values
    Sigma = np.outer(cv, cv) * C

    # Cholesky (PSD guaranteed by Phase 1 projection)
    L = np.linalg.cholesky(Sigma + 1e-10 * np.eye(n))

    z = rng.standard_normal((n_scenarios, n))
    multipliers = 1.0 + z @ L.T
    multipliers = np.clip(multipliers, 0.1, None)
    return multipliers

def lead_time_demands(flows_x: np.ndarray,      # (n_wh, n_nodes) weekly flow
                      multipliers: np.ndarray,   # (n_scen, n_nodes)
                      lead_times_weeks: np.ndarray  # (n_wh,)
                      ) -> np.ndarray:
    """
    Return array (n_scen, n_wh): total lead-time demand at each warehouse
    in each scenario.

    D[j, s] = Σ_i x[j,i] × mult[s,i] × L[j]
    """
    # weekly demand seen by wh j in scenario s
    weekly = multipliers @ flows_x.T          # (n_scen, n_wh)
    return weekly * lead_times_weeks[np.newaxis, :]   # scale by lead time

if __name__ == '__main__':
    # Unit tests for scenarios.py as specified in Implementation Plan 02 §2.2
    nodes = pd.read_csv('data/processed/demand_nodes_anchored.csv')
    corr = pd.read_csv('data/processed/correlation_matrix.csv', index_col=0)

    print("Running scenarios.py verification tests...")

    # 1. Shape and non-negativity test
    n_scen = 1000
    scenarios = generate_scenarios(nodes, corr, n_scen, seed=42)
    assert scenarios.shape == (n_scen, len(nodes)), f"Shape mismatch: {scenarios.shape}"
    assert np.all(scenarios > 0), "Found non-positive scenario multipliers"
    print(f"✓ Shape test passed: {scenarios.shape}, all values > 0")

    # 2. Mean and std test
    means = np.mean(scenarios, axis=0)
    stds = np.std(scenarios, axis=0)
    cvs = nodes['demand_cv'].values

    assert np.all(np.abs(means - 1.0) < 0.05), "Column means not within 1.0 ± 0.05"
    # Relative error on std dev within ~20%
    assert np.all(np.abs(stds - cvs) / cvs < 0.25), "Column stds not within target CV tolerances"
    print(f"✓ Mean and std tests passed: Mean across nodes = {means.mean():.4f}, Std deviation aligns with CVs")

    # 3. Empirical correlation test (Kolkata-Howrah vs Kolkata-Guwahati)
    k_idx = nodes[nodes['city'] == 'Kolkata'].index[0]
    h_idx = nodes[nodes['city'] == 'Howrah'].index[0]
    g_idx = nodes[nodes['city'] == 'Guwahati'].index[0]

    emp_corr = np.corrcoef(scenarios.T)
    rho_kh = emp_corr[k_idx, h_idx]
    rho_kg = emp_corr[k_idx, g_idx]
    assert rho_kh > rho_kg, f"Expected rho_kh ({rho_kh:.3f}) > rho_kg ({rho_kg:.3f})"
    print(f"✓ Empirical correlation test passed: Kolkata-Howrah ({rho_kh:.3f}) > Kolkata-Guwahati ({rho_kg:.3f})")

    # 4. Reproducibility test
    scenarios_again = generate_scenarios(nodes, corr, 100, seed=42)
    scenarios_first_100 = generate_scenarios(nodes, corr, 100, seed=42)
    assert np.array_equal(scenarios_again, scenarios_first_100), "Reproducibility test failed"
    print("✓ Reproducibility test passed (identical seeds yield identical scenarios)")

    # 5. Lead time demand test
    n_wh = 6
    flows_dummy = np.ones((n_wh, len(nodes))) * 100
    lead_times = np.array([1/7, 2/7, 2/7, 2/7, 4/7, 3/7])
    ltd = lead_time_demands(flows_dummy, scenarios[:50], lead_times)
    assert ltd.shape == (50, n_wh), f"LTD shape mismatch: {ltd.shape}"
    print(f"✓ lead_time_demands test passed: output shape {ltd.shape}")

    print("\nALL SCENARIOS.PY VERIFICATION TESTS PASSED SUCCESSFULLY!")
