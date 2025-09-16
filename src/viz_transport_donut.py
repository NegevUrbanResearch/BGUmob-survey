#!/usr/bin/env python3
"""
BGU Mobility Survey - Transportation Modes Donut Chart
Creates a donut chart showing transportation mode distribution with Vega-inspired styling.
"""

import pandas as pd
import plotly.graph_objects as go
import numpy as np
import os
import json

from viz_utils import data_loader, styling, exporter, processor


def get_transport_mode_data(df: pd.DataFrame) -> dict:
    """Extract transportation mode data from routes."""
    # Load the exported route data if available
    data = data_loader.load_exported_data("outputs/bgu_mobility_data.json")

    if data and "statistics" in data and "transportModes" in data["statistics"]:
        transport_modes = data["statistics"]["transportModes"]
        print(f"✓ Loaded transport modes from exported data: {transport_modes}")
        return transport_modes
    else:
        print("⚠️  Exported data not found, calculating from raw data...")

        # Fallback: parse from raw data
        mode_translation = processor.get_transport_mode_mapping()

        mode_counts = {
            "walking": 0,
            "bicycle": 0,
            "ebike": 0,
            "car": 0,
            "bus": 0,
            "train": 0,
            "unknown": 0,
        }

        for idx, row in df.iterrows():
            transport_mode = row.get("Transportation-Mode", "")
            if pd.isna(transport_mode) or transport_mode == "":
                english_mode = "unknown"
            else:
                english_mode = mode_translation.get(transport_mode, "unknown")

            mode_counts[english_mode] += 1

        # Remove modes with 0 counts
        mode_counts = {k: v for k, v in mode_counts.items() if v > 0}
        return mode_counts


def create_transport_donut_chart(transport_data: dict) -> go.Figure:
    """Create donut chart for transportation modes with Vega-inspired styling."""

    # Vega-inspired color palette for transportation modes
    transport_colors = styling.TRANSPORT_COLORS

    # Transportation mode display names without emojis
    mode_display_names = {
        "walking": "Walking",
        "bicycle": "Bicycle",
        "ebike": "E-bike",
        "car": "Car",
        "bus": "Bus",
        "train": "Train",
        "unknown": "Unknown",
    }

    # Prepare data - sort by frequency
    sorted_modes = sorted(transport_data.items(), key=lambda x: x[1], reverse=True)
    modes = [mode for mode, count in sorted_modes]
    values = [count for mode, count in sorted_modes]
    colors = [transport_colors.get(mode, "#808080") for mode in modes]
    display_names = [mode_display_names.get(mode, mode.title()) for mode in modes]

    # Calculate percentages
    total = sum(values)
    percentages = [(v / total) * 100 for v in values]

    fig = go.Figure()

    # Add the donut chart
    fig.add_trace(
        go.Pie(
            labels=display_names,
            values=values,
            hole=0.45,  # Donut hole size
            marker=dict(
                colors=colors, line=dict(color="rgba(255,255,255,0.6)", width=2)
            ),
            textinfo="label+percent",
            texttemplate="<b>%{label}</b><br>%{percent}",
            textposition="outside",
            textfont=dict(
                size=16, color="white", family="Inter, system-ui, sans-serif"
            ),
            hovertemplate="<b>%{label}</b><br>Trips: %{value}<br>Percentage: %{percent}<extra></extra>",
            hoverlabel=dict(
                bgcolor="rgba(15,15,15,0.95)",
                bordercolor="rgba(255,255,255,0.3)",
                font_size=14,
                font_family="Inter, system-ui, sans-serif",
            ),
            sort=False,  # Keep sorted order
        )
    )

    # Add center text showing total
    fig.add_annotation(
        text=f"<b>{total}</b><br><span style='font-size: 16px; color: rgba(255,255,255,0.8);'>Total Trips</span>",
        x=0.5,
        y=0.5,
        font=dict(size=28, color="white", family="Inter, system-ui, sans-serif"),
        showarrow=False,
        align="center",
    )

    fig.update_layout(
        title={
            "text": "Transportation Mode Distribution",
            "x": 0.5,
            "xanchor": "center",
            "font": {
                "size": 32,
                "color": "white",
                "family": "Inter, system-ui, sans-serif",
            },
            "pad": {"b": 30},
        },
        paper_bgcolor="rgba(0,0,0,0)",  # Transparent background
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "white", "size": 14, "family": "Inter, system-ui, sans-serif"},
        margin=dict(l=80, r=180, t=120, b=40),
        autosize=True,
        showlegend=True,
        legend=dict(
            orientation="v",
            yanchor="middle",
            y=0.5,
            xanchor="left",
            x=1.01,
            font=dict(size=24, color="white", family="Inter, system-ui, sans-serif"),
            bgcolor="rgba(255,255,255,0.1)",
            bordercolor="rgba(255,255,255,0.3)",
            borderwidth=2,
            traceorder="normal",
            itemsizing="constant",
            itemwidth=60,
        ),
        hoverlabel=dict(
            bgcolor="rgba(15,15,15,0.95)",
            bordercolor="rgba(255,255,255,0.3)",
            font_size=14,
            font_family="Inter, system-ui, sans-serif",
        ),
        # Add subtle animation
        transition=dict(duration=500, easing="cubic-in-out"),
    )

    return fig


def _removed_create_iframe_optimized_html(
    fig: go.Figure, filename: str, title: str
) -> None:
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
        
        /* Smooth hover transitions without overlap */
        .js-plotly-plot .plotly .slice {{
            transition: opacity 0.2s ease;
        }}
        
        .js-plotly-plot .plotly .slice:hover {{
            opacity: 0.9;
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
            modeBarButtonsToRemove: ['pan2d', 'lasso2d', 'select2d', 'autoScale2d'],
            responsive: true,
            staticPlot: false,
            toImageButtonOptions: {{
                format: 'png',
                filename: '{title.lower().replace(" ", "_")}',
                height: 800,
                width: 1200,
                scale: 2
            }}
        }};
        
        Plotly.newPlot('plotly-div', figureJSON.data, figureJSON.layout, config);
        
        // Disable legend clicking to make it static
        document.getElementById('plotly-div').on('plotly_legendclick', function() {{
            return false;
        }});
        document.getElementById('plotly-div').on('plotly_legenddoubleclick', function() {{
            return false;
        }});
        
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


def _removed_export_figure(fig: go.Figure, filename_base: str, title: str) -> None:
    """Export figure as both optimized HTML and PNG."""
    html_path = f"outputs/{filename_base}.html"
    png_path = f"outputs/{filename_base}.png"

    _removed_create_iframe_optimized_html(fig, html_path, title)
    print(f"✓ Saved iframe-optimized HTML: {html_path}")

    try:
        fig.write_image(png_path, width=1200, height=800, scale=2, engine="kaleido")
        print(f"✓ Saved PNG: {png_path}")
    except Exception as e:
        print(f"⚠️  PNG export failed: {e}")


def main():
    """Main function to create transportation modes donut chart."""

    # Load data
    df = data_loader.load_processed_data()

    # Get transportation mode data
    transport_data = get_transport_mode_data(df)

    if not transport_data or sum(transport_data.values()) == 0:
        print("⚠️  No transportation mode data found!")
        return None

    # Create donut chart
    fig = create_transport_donut_chart(transport_data)
    exporter.export_figure(
        fig,
        "transport_modes_donut",
        "Transportation Modes Donut",
        background_gradient="linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%)",
    )

    # Print statistics
    total_trips = sum(transport_data.values())
    print(f"\n📊 Transportation Mode Statistics:")
    for mode, count in sorted(transport_data.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / total_trips) * 100
        print(f"   • {mode.title()}: {count} trips ({percentage:.1f}%)")

    return fig


if __name__ == "__main__":
    main()
