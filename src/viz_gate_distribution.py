#!/usr/bin/env python3
"""
BGU Mobility Survey - Gate Distribution Pie Chart
Creates a pie chart showing the distribution of routes to different campus gates
using the same color scheme as the main application.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import os
import json

from viz_utils import data_loader, styling, exporter, processor, chart_builder


def get_gate_data(df: pd.DataFrame) -> dict:
    """Extract gate usage data from routes."""
    # Load the exported route data if available
    data = data_loader.load_exported_data("outputs/bgu_mobility_data.json")

    if data and "statistics" in data and "gateUsage" in data["statistics"]:
        gate_usage = data["statistics"]["gateUsage"]
        print(f"✓ Loaded gate usage from exported data: {gate_usage}")
        return gate_usage
    else:
        print("⚠️  Exported data not found, calculating from raw data...")

        # BGU Gates mapping
        bgu_gates = processor.get_bgu_gates()

        # Simple gate assignment based on proximity (fallback)
        gate_counts = {"South Gate 3": 0, "North Gate 3": 0, "West Gate": 0}

        # Count routes to each gate (simplified)
        for idx, row in df.iterrows():
            if pd.notna(row.get("Residence-Info", "")):
                # Default assignment - this would need proper coordinate parsing
                gate_counts["North Gate 3"] += 1

        return gate_counts


def create_gate_pie_chart(gate_data: dict) -> go.Figure:
    """Create pie chart for gate distribution using app color scheme."""

    # App color scheme for gates
    gate_colors = styling.GATE_COLORS

    # Prepare data
    gates = list(gate_data.keys())
    values = list(gate_data.values())
    colors = [gate_colors.get(gate, "#9E9E9E") for gate in gates]

    return chart_builder.create_pie_chart(
        labels=gates,
        values=values,
        title="Campus Gate Distribution",
        colors=colors,
        hole=0.0,  # Full pie (not donut)
    )


def main():
    """Main function to create gate distribution pie chart."""
    print("🏛️  Creating Gate Distribution Pie Chart")
    print("=" * 45)

    # Load data
    df = data_loader.load_processed_data()

    # Get gate usage data
    gate_data = get_gate_data(df)

    if not gate_data or sum(gate_data.values()) == 0:
        print("⚠️  No gate usage data found!")
        return None

    # Create pie chart
    fig = create_gate_pie_chart(gate_data)
    exporter.export_figure(
        fig,
        "gate_distribution",
        "Gate Distribution",
        background_gradient="linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%)",
    )

    # Print statistics
    total_trips = sum(gate_data.values())
    print(f"\n📊 Gate Distribution Statistics:")
    for gate, count in sorted(gate_data.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / total_trips) * 100
        print(f"   • {gate}: {count} trips ({percentage:.1f}%)")
    return fig


if __name__ == "__main__":
    main()
