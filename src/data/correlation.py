"""
Spatial demand correlation for 40 nodes.

Model: rho_ij = rho_0 * exp(-d_ij / d_0)
  rho_0 = 0.5  (max correlation at zero distance)
  d_0   = 200 km (decay length)

Justification: nearby cities share weather, festivals, regional economic
shocks → correlated demand. rho_0=0.5 and d_0=200km are modeling choices
within the range used in published spatial demand correlation work
(document as assumption; sensitivity-tested in Phase 3).
"""

import pandas as pd
import numpy as np
from geopy.distance import geodesic
from scipy.linalg import eigh

RHO_0 = 0.5
D_0 = 200.0  # km

def build_correlation_matrix(nodes: pd.DataFrame,
                             rho_0: float = RHO_0,
                             d_0: float = D_0) -> pd.DataFrame:
    """Return 40x40 correlation matrix as DataFrame indexed by node_id."""
    n = len(nodes)
    corr = np.eye(n)
    ids = nodes['node_id'].tolist()
    coords = list(zip(nodes['latitude'], nodes['longitude']))

    for i in range(n):
        for j in range(i + 1, n):
            d = geodesic(coords[i], coords[j]).km
            rho = rho_0 * np.exp(-d / d_0)
            corr[i, j] = rho
            corr[j, i] = rho

    # Ensure positive semi-definite (nearest correlation matrix)
    # If any eigenvalue < 0, project onto PSD cone
    w, V = eigh(corr)
    if w.min() < 1e-8:
        w = np.clip(w, 1e-8, None)
        corr = V @ np.diag(w) @ V.T
        # Re-normalize to unit diagonal
        d = np.sqrt(np.diag(corr))
        corr = corr / np.outer(d, d)

    return pd.DataFrame(corr, index=ids, columns=ids)

def correlated_pooled_std(stds: np.ndarray, corr_sub: np.ndarray) -> float:
    """
    Pooled std under correlation: sqrt(sigma' Sigma sigma).
    stds: vector of individual stds for nodes in the group.
    corr_sub: submatrix of the full correlation matrix for those nodes.
    """
    sigma = np.asarray(stds)
    return float(np.sqrt(sigma @ corr_sub @ sigma))

if __name__ == '__main__':
    nodes = pd.read_csv('data/processed/demand_nodes_anchored.csv')
    corr = build_correlation_matrix(nodes)
    corr.to_csv('data/processed/correlation_matrix.csv')

    # Sanity checks
    assert np.allclose(np.diag(corr.values), 1.0), "Diagonal must be 1"
    assert corr.values.min() >= -1 and corr.values.max() <= 1
    print(f"Correlation matrix: {corr.shape}")
    print(f"Mean off-diagonal correlation: "
          f"{corr.values[np.triu_indices_from(corr, k=1)].mean():.3f}")
          
    print(corr)

    # Demo: pooled std for Kolkata + Howrah (very close, high correlation)
    # vs. Kolkata + Guwahati (far, low correlation)
    k, h, g = 'N000', 'N001', None  # Kolkata, Howrah
    guwahati_id = nodes[nodes['city'] == 'Guwahati']['node_id'].values[0]
    pair1 = [k, h]
    pair2 = [k, guwahati_id]
    stds = nodes.set_index('node_id')['demand_std_units_per_week']
    for pair, label in [(pair1, 'Kolkata+Howrah (close)'),
                        (pair2, 'Kolkata+Guwahati (far)')]:
        sub = corr.loc[pair, pair].values
        s = stds.loc[pair].values
        pooled = correlated_pooled_std(s, sub)
        indep = np.sqrt((s ** 2).sum())
        print(f"{label}: correlated pooled std = {pooled:.0f}, "
              f"independent = {indep:.0f}, "
              f"correlation penalty = {100*(pooled/indep - 1):.1f}%")
