#!/usr/bin/env python3
"""
BGU Mobility Survey - Distance Comparison Analysis
Creates a line chart comparing perceived distance importance vs actual route distances.
"""

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import numpy as np
import os
import json
from typing import List, Dict, Tuple

from viz_utils import data_loader, styling, exporter


def get_route_distances() -> Dict:
    """Load actual route distances from OTP analysis."""
    data = data_loader.load_exported_data("outputs/bgu_mobility_data.json")

    if data and "routes" in data:
        routes = data["routes"]
        distances = [route["distance"] for route in routes if "distance" in route]

        print(f"✓ Loaded {len(distances)} route distances from OTP data")
        return {
            "distances": distances,
            "avg_distance": np.mean(distances) if distances else 0,
            "median_distance": np.median(distances) if distances else 0,
            "std_distance": np.std(distances) if distances else 0,
        }
    else:
        print("⚠️  Route distance data not found")
        return {
            "distances": [],
            "avg_distance": 0,
            "median_distance": 0,
            "std_distance": 0,
        }


def analyze_perceived_distance_importance(df: pd.DataFrame) -> Dict:
    """Analyze how important distance is to students from route choice data."""
    # Distance importance from route choice survey (1=most important, 5=least important)
    distance_col = "Routechoice-Distance"

    if distance_col not in df.columns:
        print(f"⚠️  Column {distance_col} not found in data")
        return {"responses": [], "avg_importance": 0, "importance_distribution": {}}

    # Clean and convert distance importance data
    distance_responses = pd.to_numeric(df[distance_col], errors="coerce").dropna()

    if len(distance_responses) == 0:
        print("⚠️  No valid distance importance responses found")
        return {"responses": [], "avg_importance": 0, "importance_distribution": {}}

    # Invert scale: 1=most important becomes 5, 5=least important becomes 1
    # This makes higher values = more important for better visualization
    inverted_responses = 6 - distance_responses

    # Calculate distribution
    importance_dist = {}
    for i in range(1, 6):
        original_value = 6 - i  # Convert back to original scale for counting
        count = sum(distance_responses == original_value)
        importance_dist[i] = count

    avg_importance = inverted_responses.mean()

    print(f"✓ Analyzed {len(distance_responses)} distance importance responses")
    print(f"   Average importance (1-5 scale): {avg_importance:.2f}")

    return {
        "responses": list(inverted_responses),
        "avg_importance": avg_importance,
        "importance_distribution": importance_dist,
        "response_count": len(distance_responses),
    }


def create_distance_comparison_chart(
    perceived_data: Dict, actual_data: Dict, linked_data: List[Dict]
) -> go.Figure:
    """Create scatter plot comparing perceived vs actual distance for matched responses."""

    fig = go.Figure()

    if not linked_data:
        fig.add_annotation(
            text="No linked distance data available",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=20, color="white"),
        )
        return fig

    # Extract data for scatter plot
    actual_distances = [item["actual_distance"] for item in linked_data]
    perceived_importance = [item["perceived_importance"] for item in linked_data]
    submission_ids = [item["submission_id"] for item in linked_data]

    # Filter to trips under 2.5 km
    filtered_points = [
        (x, y, sid)
        for x, y, sid in zip(actual_distances, perceived_importance, submission_ids)
        if x is not None and y is not None and x < 2.5
    ]
    if not filtered_points:
        fig.add_annotation(
            text="No trips under 10 km",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=20, color="white"),
        )
        return fig

    xs, ys, texts = zip(*filtered_points)

    # Create scatter plot
    fig.add_trace(
        go.Scatter(
            x=xs,
            y=ys,
            mode="markers",
            name="Individual Responses",
            marker=dict(
                size=12,
                color="rgba(0, 212, 255, 0.8)",
                line=dict(width=2, color="rgba(255, 255, 255, 0.6)"),
                opacity=0.8,
            ),
            hovertemplate="<b>Student Response</b><br>Actual Distance: %{x:.2f} km<br>Perceived Importance: %{y:.1f}/5<br>ID: %{text}<extra></extra>",
            text=texts,
        )
    )

    # Trend line removed per request

    fig.update_layout(
        title={
            "text": "Distance: Perception vs Reality",
            "x": 0.5,
            "xanchor": "center",
            "font": {
                "size": 32,
                "color": "white",
                "family": "Inter, system-ui, sans-serif",
            },
            "pad": {"b": 30},
        },
        xaxis=dict(
            title="Actual Trip Distance (km)",
            titlefont=dict(
                size=18, color="white", family="Inter, system-ui, sans-serif"
            ),
            tickfont=dict(size=14, color="rgba(255,255,255,0.95)", family="Inter"),
            gridcolor="rgba(255,255,255,0.15)",
            showgrid=True,
            zeroline=False,
            showline=True,
            linecolor="rgba(255,255,255,0.4)",
            linewidth=2,
            range=[0, 2.5],
        ),
        yaxis=dict(
            title="Perceived Distance Importance (1-5 scale)",
            titlefont=dict(
                size=18, color="white", family="Inter, system-ui, sans-serif"
            ),
            tickfont=dict(size=14, color="rgba(255,255,255,0.95)", family="Inter"),
            gridcolor="rgba(255,255,255,0.15)",
            showgrid=True,
            zeroline=False,
            showline=True,
            linecolor="rgba(255,255,255,0.4)",
            linewidth=2,
            range=[0.5, 5.5],
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(15,15,30,0.3)",
        font={"color": "white", "size": 14, "family": "Inter, system-ui, sans-serif"},
        margin=dict(l=120, r=160, t=140, b=90),
        autosize=True,
        showlegend=False,
        hovermode="closest",
        hoverlabel=dict(
            bgcolor="rgba(15,15,15,0.98)",
            bordercolor="rgba(255,255,255,0.4)",
            font_size=14,
            font_family="Inter, system-ui, sans-serif",
        ),
    )

    return fig


def link_perceived_and_actual_distances(
    df: pd.DataFrame, actual_data: Dict
) -> List[Dict]:
    """Link survey responses to actual route distances using submission IDs."""
    linked_data = []

    # Create a lookup dictionary for route distances by submission ID
    route_lookup = {}
    try:
        with open("outputs/bgu_mobility_data.json", "r", encoding="utf-8") as f:
            data = json.load(f)

        for route in data["routes"]:
            submission_id = route["id"]
            distance = route.get("distance", 0)
            route_lookup[submission_id] = distance

    except FileNotFoundError:
        print("⚠️  Route data not found for linking")
        return linked_data

    # Distance importance from route choice survey
    distance_col = "Routechoice-Distance"

    if distance_col not in df.columns:
        print(f"⚠️  Column {distance_col} not found")
        return linked_data

    # Process each survey response
    for idx, row in df.iterrows():
        submission_id = row.get("Submission ID")
        distance_importance_raw = row.get(distance_col)

        # Check if we have both pieces of data
        if (
            pd.notna(submission_id)
            and pd.notna(distance_importance_raw)
            and submission_id in route_lookup
        ):

            # Convert distance importance (invert scale: 1=most important becomes 5)
            distance_importance = 6 - float(distance_importance_raw)
            actual_distance = route_lookup[submission_id]

            linked_data.append(
                {
                    "submission_id": submission_id,
                    "perceived_importance": distance_importance,
                    "actual_distance": actual_distance,
                }
            )

    print(f"✓ Successfully linked {len(linked_data)} responses with actual distances")
    return linked_data


def create_iframe_optimized_html(fig: go.Figure, filename: str, title: str) -> None:
    """Create HTML file specifically optimized for iframe embedding."""

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <script src="https://cdn.plot.ly/plotly-2.26.0.min.js"></script>
    <style>
        body {{
            margin: 0;
            padding: 0;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
            font-family: 'Inter', system-ui, sans-serif;
            overflow: hidden;
        }}
        
        #plotly-div {{
            width: 100%;
            height: 100vh;
            margin: 0;
            padding: 0;
        }}
        
        .modebar {{
            opacity: 0.3;
            transition: opacity 0.3s ease;
        }}
        
        .modebar:hover {{
            opacity: 1;
        }}
    </style>
</head>
<body>
    <div id="plotly-div"></div>
    
    <script>
        var figureJSON = {fig.to_json()};
        
        var config = {{
            displayModeBar: true,
            displaylogo: false,
            modeBarButtonsToRemove: ['pan2d', 'lasso2d', 'select2d'],
            responsive: true,
            toImageButtonOptions: {{
                format: 'png',
                filename: '{title.lower().replace(" ", "_")}',
                height: 800,
                width: 1200,
                scale: 2
            }}
        }};
        
        Plotly.newPlot('plotly-div', figureJSON.data, figureJSON.layout, config);
        
        window.addEventListener('resize', function() {{
            Plotly.Plots.resize('plotly-div');
        }});
        
        setTimeout(function() {{
            Plotly.Plots.resize('plotly-div');
        }}, 100);
    </script>
</body>
</html>"""

    with open(filename, "w", encoding="utf-8") as f:
        f.write(html_content)


def export_figure(fig: go.Figure, filename_base: str, title: str) -> None:
    """Export figure as both optimized HTML and PNG."""
    html_path = f"outputs/{filename_base}.html"
    png_path = f"outputs/{filename_base}.png"

    create_iframe_optimized_html(fig, html_path, title)
    print(f"✓ Saved iframe-optimized HTML: {html_path}")

    try:
        fig.write_image(png_path, width=1200, height=800, scale=2, engine="kaleido")
        print(f"✓ Saved PNG: {png_path}")
    except Exception as e:
        print(f"⚠️  PNG export failed: {e}")


def main():
    """Main function to create distance comparison analysis."""
    print("📏 Creating Distance Comparison Analysis")
    print("=" * 45)

    # Load data
    df = data_loader.load_processed_data()

    # Analyze perceived distance importance
    perceived_data = analyze_perceived_distance_importance(df)

    # Get actual route distances
    actual_data = get_route_distances()

    if not perceived_data["responses"] and not actual_data["distances"]:
        print("⚠️  No distance data available for comparison!")
        return None

    # Link survey responses with actual route distances
    linked_data = link_perceived_and_actual_distances(df, actual_data)

    # Create comparison chart
    fig = create_distance_comparison_chart(perceived_data, actual_data, linked_data)
    export_figure(fig, "distance_comparison", "Distance Comparison")

    # Print analysis summary
    print(f"\n📊 Distance Analysis Summary:")
    if perceived_data["responses"]:
        print(
            f"   • Perceived importance responses: {perceived_data['response_count']}"
        )
        print(
            f"   • Average importance rating: {perceived_data['avg_importance']:.2f}/5"
        )

    if actual_data["distances"]:
        print(f"   • Actual route distances analyzed: {len(actual_data['distances'])}")
        print(f"   • Average actual distance: {actual_data['avg_distance']:.2f} km")
        print(f"   • Median actual distance: {actual_data['median_distance']:.2f} km")

    return fig


if __name__ == "__main__":
    os.makedirs("outputs", exist_ok=True)
    main()
