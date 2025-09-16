#!/usr/bin/env python3
"""
BGU Mobility Survey - Future Participation Analysis
Creates bar chart showing willingness to participate in future studies from completed surveys only.
"""

import pandas as pd
import plotly.graph_objects as go
import os

from viz_utils import data_loader, styling, exporter, processor, chart_builder


def prepare_participation_data(df: pd.DataFrame) -> pd.DataFrame:
    """Prepare participation data for completed surveys only."""

    # Filter only completed surveys
    completed_df = df[df["Submission Completed"] == True].copy()

    if len(completed_df) == 0:
        print("⚠️  No completed surveys found!")
        return None

    print(f"📊 Analyzing {len(completed_df)} completed surveys")

    # Get counts for further study interest
    study_counts = completed_df["Further_Study_Interest"].value_counts()
    print(f"\n📊 Further Study Participation (Completed Surveys):")
    for response, count in study_counts.items():
        percentage = count / len(completed_df) * 100
        print(f"  {response}: {count} ({percentage:.1f}%)")

    # Get counts for week tracking interest
    tracking_counts = completed_df["Week_Tracking_Interest"].value_counts()
    print(f"\n📊 Week Tracking Participation (Completed Surveys):")
    for response, count in tracking_counts.items():
        percentage = count / len(completed_df) * 100
        print(f"  {response}: {count} ({percentage:.1f}%)")

    return completed_df


def create_participation_comparison(completed_df: pd.DataFrame) -> go.Figure:
    """Create a comparison chart showing participation by study type."""

    # Create crosstabs
    study_crosstab = completed_df["Further_Study_Interest"].value_counts()
    tracking_crosstab = completed_df["Week_Tracking_Interest"].value_counts()

    categories = ["Future Study", "Week Tracking"]

    # Get yes/no counts for each
    study_yes = study_crosstab.get("Yes", 0)
    study_no = study_crosstab.get("No", 0)
    tracking_yes = tracking_crosstab.get("Yes", 0)
    tracking_no = tracking_crosstab.get("No", 0)

    data_series = {"Yes": [study_yes, tracking_yes], "No": [study_no, tracking_no]}

    return chart_builder.create_grouped_bar_chart(
        categories=categories,
        data_series=data_series,
        title="Future Research Participation Interest",
        colors=["#00d4ff", "#ff6b6b"],
    )


def main():
    """Main function to create participation visualization."""
    print("📊 Creating Future Participation Analysis")
    print("=" * 50)

    # Load data
    df = data_loader.load_processed_data()

    # Prepare participation data (completed surveys only)
    completed_df = prepare_participation_data(df)

    if completed_df is None:
        return None

    # Create participation comparison chart
    comparison_fig = create_participation_comparison(completed_df)
    exporter.export_figure(
        comparison_fig,
        "participation_analysis",
        "Future Research Participation Interest",
        use_iframe_html=False,
    )

    print("\n🎯 Participation analysis completed!")
    print("📊 Analysis focused on completed surveys only")
    print("📱 HTML file is now responsive and will fill the browser window")
    print("🖼️  PNG file exported at 1920x1080 resolution")

    return comparison_fig


if __name__ == "__main__":
    main()
