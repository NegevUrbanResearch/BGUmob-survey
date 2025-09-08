#!/usr/bin/env python
"""
BGU Mobility Survey - Walking Distance Analysis
Generates an iframe-optimized histogram of walking trip distances and saves stats.
"""

from __future__ import annotations

import os
import json
from typing import Tuple
import math

import pandas as pd
import plotly.graph_objects as go


WALKING_HEBREW = "ברגל"
ROUTE_SUMMARY_PATH = "outputs/route_summary_filtered.csv"
OUTPUT_HTML = "outputs/walking_distance.html"
OUTPUT_PNG = "outputs/walking_distance.png"
OUTPUT_STATS = "outputs/walking_distance_stats.json"


def load_walking_routes(csv_path: str) -> pd.DataFrame:
    """Load route summary and return only walking trips.

    Assertions:
    - File exists and is non-empty
    - Required columns existet
    - At least one walking trip is present
    """
    assert os.path.exists(csv_path), f"Missing input file: {csv_path}"

    df = pd.read_csv(csv_path)
    assert len(df) > 0, "Route summary CSV is empty"

    required_cols = {"transportation_mode", "total_distance_km"}
    missing = required_cols - set(df.columns)
    assert not missing, f"Missing required columns: {sorted(missing)}"

    walking_df = df[df["transportation_mode"] == WALKING_HEBREW].copy()
    # Coerce to numeric and drop invalid
    walking_df["total_distance_km"] = pd.to_numeric(
        walking_df["total_distance_km"], errors="coerce"
    )
    walking_df = walking_df.dropna(subset=["total_distance_km"])

    assert len(walking_df) > 0, "No valid walking trips found in the dataset"

    return walking_df


def compute_average_distance(walking_df: pd.DataFrame) -> float:
    """Compute average walking distance in km."""
    distances = walking_df["total_distance_km"]
    assert (distances >= 0).all(), "Distances must be non-negative"
    avg_km = float(distances.mean())
    # Guard against nonsensical averages
    assert 0 <= avg_km < 50, f"Average distance out of expected range: {avg_km:.2f} km"
    return avg_km


def compute_median_and_max_distance(walking_df: pd.DataFrame) -> Tuple[float, float]:
    """Compute median and maximum walking distance in km with basic validation."""
    distances = walking_df["total_distance_km"]
    assert (distances >= 0).all(), "Distances must be non-negative"
    median_km = float(distances.median())
    max_km = float(distances.max())
    assert (
        0 <= median_km < 50
    ), f"Median distance out of expected range: {median_km:.2f} km"
    assert 0 <= max_km < 200, f"Max distance out of expected range: {max_km:.2f} km"
    return median_km, max_km


def create_histogram(
    walking_df: pd.DataFrame, avg_km: float, median_km: float | None = None
) -> go.Figure:
    """Create histogram of walking distances with mean (and optional median) lines."""
    distances = walking_df["total_distance_km"]

    fig = go.Figure()

    fig.add_trace(
        go.Histogram(
            x=distances,
            nbinsx=20,
            marker=dict(
                color="rgba(0, 212, 255, 0.7)",
                line=dict(color="rgba(255,255,255,0.2)", width=1),
            ),
            name="Walking trip distances",
            hovertemplate="<b>Distance</b>: %{x:.2f} km<br><b>Count</b>: %{y}<extra></extra>",
        )
    )

    # Custom ticks excluding 0
    min_km: float = float(distances.min())
    max_km: float = float(distances.max())
    data_range = max(0.01, max_km - min_km)
    if data_range <= 2:
        step = 0.1
        fmt = "{:.1f}"
    elif data_range <= 5:
        step = 0.25
        fmt = "{:.2f}"
    else:
        step = 0.5
        fmt = "{:.1f}"
    start = math.floor(min_km / step) * step
    end = math.ceil(max_km / step) * step
    tickvals = []
    v = start
    # Guard against infinite loops
    max_iters = 1000
    iters = 0
    while v <= end + 1e-9 and iters < max_iters:
        if abs(v) > 1e-9:
            tickvals.append(round(v, 2))
        v += step
        iters += 1
    ticktext = [fmt.format(tv) for tv in tickvals]

    fig.update_layout(
        title=dict(
            text="Walking Distance to Campus",
            x=0.5,
            xanchor="center",
            font=dict(size=32, color="white", family="Inter, system-ui, sans-serif"),
        ),
        xaxis=dict(
            title="Distance (km)",
            titlefont=dict(size=18, color="white"),
            tickfont=dict(size=14, color="rgba(255,255,255,0.95)"),
            gridcolor="rgba(255,255,255,0.12)",
            tickmode="array",
            tickvals=tickvals,
            ticktext=ticktext,
        ),
        yaxis=dict(
            title="Number of trips",
            titlefont=dict(size=18, color="white"),
            tickfont=dict(size=14, color="rgba(255,255,255,0.95)"),
            gridcolor="rgba(255,255,255,0.12)",
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(15,15,30,0.3)",
        font=dict(color="white", size=14, family="Inter, system-ui, sans-serif"),
        margin=dict(l=100, r=80, t=120, b=80),
        bargap=0.08,
        hoverlabel=dict(
            bgcolor="rgba(15,15,15,0.98)", bordercolor="rgba(255,255,255,0.4)"
        ),
    )

    return fig


def create_iframe_optimized_html(fig: go.Figure, filename: str, title: str) -> None:
    """Write a minimal iframe-optimized HTML wrapper for the figure."""
    html = f"""<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"UTF-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
  <title>{title}</title>
  <script src=\"https://cdn.plot.ly/plotly-2.26.0.min.js\"></script>
  <style>
    html, body {{ margin: 0; height: 100%; background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%); }}
    #plotly-div {{ width: 100%; height: 100vh; }}
    .modebar {{ opacity: .3; }}
    .modebar:hover {{ opacity: 1; }}
  </style>
  </head>
<body>
  <div id=\"plotly-div\"></div>
  <script>
    var figureJSON = {fig.to_json()};
    Plotly.newPlot('plotly-div', figureJSON.data, figureJSON.layout, {{
      displayModeBar: true, displaylogo: false, responsive: true,
      modeBarButtonsToRemove: ['pan2d', 'lasso2d', 'select2d']
    }});
    window.addEventListener('resize', () => Plotly.Plots.resize('plotly-div'));
  </script>
</body>
</html>"""
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html)


def export_figure(fig: go.Figure, filename_base: str, title: str) -> None:
    os.makedirs("outputs", exist_ok=True)
    create_iframe_optimized_html(fig, f"outputs/{filename_base}.html", title)
    try:
        fig.write_image(
            f"outputs/{filename_base}.png",
            width=1200,
            height=800,
            scale=2,
            engine="kaleido",
        )
    except Exception:
        # HTML is the primary output; PNG is optional
        pass


def save_stats(avg_km: float, median_km: float, max_km: float) -> None:
    stats = {
        "average_walking_distance_km": round(avg_km, 2),
        "median_walking_distance_km": round(median_km, 2),
        "max_walking_distance_km": round(max_km, 2),
    }
    with open(OUTPUT_STATS, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)


def main() -> Tuple[pd.DataFrame, float]:
    walking_df = load_walking_routes(ROUTE_SUMMARY_PATH)
    avg_km = compute_average_distance(walking_df)
    median_km, max_km = compute_median_and_max_distance(walking_df)

    fig = create_histogram(walking_df, avg_km, median_km)
    export_figure(fig, "walking_distance", "Walking Distance to Campus")
    save_stats(avg_km, median_km, max_km)

    print(f"average_walking_distance_km={avg_km:.4f}")
    print(f"median_walking_distance_km={median_km:.4f}")
    print(f"max_walking_distance_km={max_km:.4f}")
    print(f"✓ Saved: {OUTPUT_HTML}")
    return walking_df, avg_km


if __name__ == "__main__":
    main()
