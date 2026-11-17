"""
Interactive cost visualization charts for NETOPT-EAST.

Includes:
- Cost-Service Frontier (stacked cost breakdown + total cost line)
- Corrosion of Pooling (pooling benefit % vs. spatial correlation rho_0)
- Robustness Scorecard (horizontal bar chart of event stress tests)
- Monte Carlo Cost Distribution (histogram with 5th, median, 95th percentiles & base marker)
"""

import os
import sys
import pandas as pd
import plotly.graph_objects as go

def plot_cost_service_frontier(frontier_df: pd.DataFrame,
                               output_html='reports/figures/frontier.html',
                               output_png='reports/figures/frontier.png'):
    """
    THE chart. X: fill rate. Y: total annual cost.
    Annotated with the cost of each service-level step.
    """
    os.makedirs(os.path.dirname(output_html), exist_ok=True)
    os.makedirs(os.path.dirname(output_png), exist_ok=True)

    df = frontier_df.sort_values('service_level')

    fig = go.Figure()

    # Stacked area: show cost composition at each service level
    fig.add_trace(go.Scatter(
        x=df['service_level'], y=df['fixed_cost'] / 1e6,
        name='Fixed', stackgroup='one', fillcolor='rgba(150,150,150,0.5)',
    ))
    fig.add_trace(go.Scatter(
        x=df['service_level'], y=df['transport_cost'] / 1e6,
        name='Transport', stackgroup='one', fillcolor='rgba(100,150,255,0.5)',
    ))
    fig.add_trace(go.Scatter(
        x=df['service_level'], y=df['inventory_cost'] / 1e6,
        name='Inventory', stackgroup='one', fillcolor='rgba(255,150,100,0.6)',
    ))

    # Total cost line on top
    fig.add_trace(go.Scatter(
        x=df['service_level'], y=df['total_cost'] / 1e6,
        name='Total Cost', mode='lines+markers',
        line=dict(color='black', width=3),
        marker=dict(size=10),
    ))

    # Annotate the 95% -> 99% jump
    if len(df) >= 2:
        row_95 = df[df['service_level'] == 0.95]
        row_99 = df[df['service_level'] == 0.99]
        if len(row_95) and len(row_99):
            delta = (row_99['total_cost'].values[0] -
                     row_95['total_cost'].values[0]) / 1e5
            fig.add_annotation(
                x=0.99, y=row_99['total_cost'].values[0] / 1e6,
                text=f"+₹{delta:.0f}L/yr vs 95%",
                showarrow=True, arrowhead=2, ax=-60, ay=-40,
            )

    fig.update_layout(
        title='Cost-Service Frontier: What Does Fill Rate Actually Cost?',
        xaxis_title='Fill Rate (Service Level)',
        yaxis_title='Annual Cost (₹ Millions)',
        xaxis=dict(tickvals=[0.90, 0.95, 0.98, 0.99],
                   ticktext=['90%', '95%', '98%', '99%']),
        hovermode='x unified',
        height=500,
    )

    fig.write_html(output_html)
    try:
        fig.write_image(output_png, scale=2)
        print(f"Frontier chart saved: {output_html}, {output_png}")
    except Exception as e:
        print(f"Frontier chart saved to HTML ({output_html}). Image export notice: {e}")

    return fig


def plot_corrosion_of_pooling(sens_df: pd.DataFrame,
                              output_html='reports/figures/corrosion.html',
                              output_png='reports/figures/corrosion.png'):
    """
    Second money chart: pooling benefit % vs. correlation level.
    Shows the square-root law is an upper bound, not a guarantee.
    """
    os.makedirs(os.path.dirname(output_html), exist_ok=True)
    os.makedirs(os.path.dirname(output_png), exist_ok=True)

    df = sens_df.sort_values('rho_0')

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df['rho_0'], y=df['pooling_benefit_pct'],
        mode='lines+markers', name='Pooling benefit',
        line=dict(color='steelblue', width=3),
        marker=dict(size=12),
        fill='tozeroy', fillcolor='rgba(100,150,255,0.2)',
    ))

    # Reference line: textbook square-root (independent demand)
    rho_0_rows = df[df['rho_0'] == 0]
    if len(rho_0_rows) > 0:
        base_val = rho_0_rows['pooling_benefit_pct'].values[0]
        fig.add_hline(y=base_val,
                      line_dash='dot', line_color='gray',
                      annotation_text='Textbook square-root (ρ=0)')

    fig.update_layout(
        title='Correlation Erodes the Square-Root Pooling Benefit',
        xaxis_title='Spatial Correlation (ρ₀)',
        yaxis_title='Safety Stock Reduction vs. No Pooling (%)',
        xaxis=dict(tickvals=[0.0, 0.3, 0.6, 1.0]),
        height=450,
    )

    fig.write_html(output_html)
    try:
        fig.write_image(output_png, scale=2)
        print(f"Corrosion chart saved: {output_html}, {output_png}")
    except Exception as e:
        print(f"Corrosion chart saved to HTML ({output_html}). Image export notice: {e}")

    return fig


def plot_robustness_scorecard(scorecard: pd.DataFrame,
                              output_html='reports/figures/scorecard.html',
                              output_png='reports/figures/scorecard.png'):
    """Horizontal bar: cost increase % per event, sorted."""
    os.makedirs(os.path.dirname(output_html), exist_ok=True)
    os.makedirs(os.path.dirname(output_png), exist_ok=True)

    df = scorecard.dropna(subset=['delta_pct']).sort_values('delta_pct')

    fig = go.Figure(go.Bar(
        y=df['event'],
        x=df['delta_pct'],
        orientation='h',
        marker_color=['#d62728' if v > 15 else '#ff7f0e' if v > 8 else '#2ca02c'
                      for v in df['delta_pct']],
        text=[f"+{v:.1f}%" for v in df['delta_pct']],
        textposition='outside',
    ))

    fig.update_layout(
        title='Robustness Scorecard: Cost Impact of Disruption Events',
        xaxis_title='Cost Increase vs. Base Case (%)',
        margin=dict(l=280),
        height=450,
    )

    fig.write_html(output_html)
    try:
        fig.write_image(output_png, scale=2)
        print(f"Scorecard chart saved: {output_html}, {output_png}")
    except Exception as e:
        print(f"Scorecard chart saved to HTML ({output_html}). Image export notice: {e}")

    return fig


def plot_mc_distribution(mc_df: pd.DataFrame, base_cost: float,
                         output_html='reports/figures/mc_dist.html',
                         output_png='reports/figures/mc_dist.png'):
    """Histogram of Monte Carlo costs with percentile lines and base marker."""
    os.makedirs(os.path.dirname(output_html), exist_ok=True)
    os.makedirs(os.path.dirname(output_png), exist_ok=True)

    valid = mc_df.dropna(subset=['total_cost'])

    fig = go.Figure()
    fig.add_trace(go.Histogram(
        x=valid['total_cost'] / 1e6,
        nbinsx=50,
        marker_color='steelblue',
        opacity=0.75,
        name='Scenario cost',
    ))

    for p, label, color in [(0.05, '5th pct', 'red'),
                            (0.50, 'Median', 'green'),
                            (0.95, '95th pct', 'red')]:
        v = valid['total_cost'].quantile(p) / 1e6
        fig.add_vline(x=v, line_dash='dash', line_color=color,
                      annotation_text=f'{label}: ₹{v:.1f}M')

    fig.add_vline(x=base_cost / 1e6, line_color='black', line_width=3,
                  annotation_text='Base case', annotation_position='top right')

    fig.update_layout(
        title=f'Monte Carlo Cost Distribution ({len(valid)} Scenarios, Fixed Network)',
        xaxis_title='Total Annual Cost (₹ Millions)',
        yaxis_title='Frequency',
        height=450,
    )

    fig.write_html(output_html)
    try:
        fig.write_image(output_png, scale=2)
        print(f"MC Distribution chart saved: {output_html}, {output_png}")
    except Exception as e:
        print(f"MC Distribution chart saved to HTML ({output_html}). Image export notice: {e}")

    return fig


if __name__ == '__main__':
    frontier_path = 'data/processed/frontier_results.csv'
    sens_path = 'data/processed/correlation_sensitivity.csv'
    scorecard_path = 'data/processed/stress_test_results.csv'
    mc_path = 'data/processed/mc_results.csv'

    if os.path.exists(frontier_path):
        f_df = pd.read_csv(frontier_path)
        plot_cost_service_frontier(f_df)

    if os.path.exists(sens_path):
        s_df = pd.read_csv(sens_path)
        plot_corrosion_of_pooling(s_df)

    if os.path.exists(scorecard_path):
        sc_df = pd.read_csv(scorecard_path)
        plot_robustness_scorecard(sc_df)

    if os.path.exists(mc_path):
        mc_df = pd.read_csv(mc_path)
        base_cost = 510947120.0
        plot_mc_distribution(mc_df, base_cost)
