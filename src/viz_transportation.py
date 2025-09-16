#!/usr/bin/env python3
"""
BGU Mobility Survey - Transportation Mode Analysis
Creates sleek, modern interactive bar charts optimized for iframe embedding.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
import os

from viz_utils import data_loader, styling, exporter, processor, chart_builder


def prepare_transportation_data(df: pd.DataFrame) -> pd.DataFrame:
    """Clean and prepare transportation mode data."""
    # Filter out empty transportation mode responses
    transport_data = df[df["Transportation-Mode"].notna()].copy()

    # Hebrew to English mapping for better presentation
    mode_mapping = processor.get_transport_mode_display_mapping()

    transport_data["Transport_English"] = transport_data["Transportation-Mode"].map(
        mode_mapping
    )
    transport_data["Transport_English"] = transport_data["Transport_English"].fillna(
        transport_data["Transportation-Mode"]
    )

    # Get counts
    transport_counts = transport_data["Transport_English"].value_counts().reset_index()
    transport_counts.columns = ["Mode", "Count"]

    # Calculate percentages
    transport_counts["Percentage"] = (
        transport_counts["Count"] / transport_counts["Count"].sum() * 100
    ).round(1)

    print(f"📊 Transportation Mode Distribution:")
    for _, row in transport_counts.iterrows():
        print(f"  {row['Mode']}: {row['Count']} ({row['Percentage']}%)")

    return transport_counts


def create_transportation_bar_chart(transport_counts: pd.DataFrame) -> go.Figure:
    """Create a sleek, modern interactive bar chart optimized for iframe embedding."""
    return chart_builder.create_bar_chart(
        x_data=transport_counts["Mode"].tolist(),
        y_data=transport_counts["Count"].tolist(),
        title="Transportation to BGU University",
        customdata=transport_counts["Percentage"].tolist(),
        hovertemplate="<b>%{x}</b><br>Responses: %{y}<br>Percentage: %{customdata}%<extra></extra>",
    )


def main():
    """Main function to create transportation visualizations."""
    print("🚗 Creating Transportation Mode Visualization (Iframe Optimized)")
    print("=" * 60)

    # Load data
    df = data_loader.load_processed_data()

    # Prepare transportation data
    transport_counts = prepare_transportation_data(df)

    # Create iframe-optimized bar chart
    fig = create_transportation_bar_chart(transport_counts)
    exporter.export_figure(fig, "transportation_modes", "Transportation Modes Analysis")

    return fig


if __name__ == "__main__":
    main()
