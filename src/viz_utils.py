#!/usr/bin/env python3
"""
BGU Mobility Survey - Shared Visualization Utilities
Consolidated functions for data loading, export, and styling across all visualizations.
Maintains exact output compatibility while reducing code duplication.
"""

import pandas as pd
import plotly.graph_objects as go
import os
import json
from typing import Dict, Any, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class VizDataLoader:
    """Centralized data loading with caching and validation."""

    def __init__(self):
        self._cache: Dict[str, pd.DataFrame] = {}

    def load_processed_data(self) -> pd.DataFrame:
        """Load the processed survey data with fallback to raw data processing."""
        cache_key = "processed_data"

        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            df = pd.read_csv("data/processed_mobility_data.csv")
            print(f"✓ Loaded processed data: {df.shape[0]} rows")
            self._cache[cache_key] = df
            return df
        except FileNotFoundError:
            print("⚠️  Processed data not found, loading raw data...")
            df = pd.read_csv("data/mobility-data.csv")

            # Apply the same processing logic that was in individual files
            df = self._process_raw_data_fallback(df)
            self._cache[cache_key] = df
            return df

    def _process_raw_data_fallback(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply fallback processing for raw data (matching original logic)."""
        df_processed = df.copy()

        # Merge binary questions (from participation analysis)
        if "Further-yes" in df.columns or "Further-no" in df.columns:
            df_processed["Further_Study_Interest"] = "No Response"
            if "Further-yes" in df.columns:
                df_processed.loc[
                    df_processed["Further-yes"].notna(), "Further_Study_Interest"
                ] = "Yes"
            if "Further-no" in df.columns:
                df_processed.loc[
                    df_processed["Further-no"].notna(), "Further_Study_Interest"
                ] = "No"

        if any(col.startswith("FurtherWeek-") for col in df.columns):
            df_processed["Week_Tracking_Interest"] = "No Response"
            if "FurtherWeek-yes" in df.columns:
                df_processed.loc[
                    df_processed["FurtherWeek-yes"].notna(), "Week_Tracking_Interest"
                ] = "Yes"
            if "FurtherWeek-no" in df.columns:
                df_processed.loc[
                    df_processed["FurtherWeek-no"].notna(), "Week_Tracking_Interest"
                ] = "No"
            if "FurtherWeek-other" in df.columns:
                df_processed.loc[
                    df_processed["FurtherWeek-other"].notna(), "Week_Tracking_Interest"
                ] = "Other"

        return df_processed

    def load_exported_data(self, file_path: str) -> Dict[str, Any]:
        """Load exported JSON data with validation."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            print(f"✓ Loaded exported data from: {file_path}")
            return data
        except FileNotFoundError:
            print(f"⚠️  Exported data not found: {file_path}")
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing JSON from {file_path}: {e}")
            return {}


class VizStyling:
    """Centralized styling constants and themes."""

    # Common font family used across all visualizations
    FONT_FAMILY = "Inter, system-ui, sans-serif"

    # Common color palettes
    TRANSPORT_COLORS = {
        "walking": "#2E8B57",  # Sea Green
        "bicycle": "#FF6347",  # Tomato Red
        "ebike": "#9370DB",  # Medium Purple
        "car": "#4682B4",  # Steel Blue
        "bus": "#DAA520",  # Goldenrod
        "train": "#8B4513",  # Saddle Brown
        "unknown": "#808080",  # Gray
    }

    GATE_COLORS = {
        "South Gate": "#E91E63",  # Pink
        "North Gate": "#9C27B0",  # Purple
        "West Gate": "#FF9800",  # Orange
    }

    # Modern vibrant colors for bar charts
    MODERN_COLORS = [
        "#00d4ff",  # Cyan
        "#ff6b6b",  # Coral
        "#4ecdc4",  # Teal
        "#45b7d1",  # Sky blue
        "#96ceb4",  # Mint
        "#ffeaa7",  # Warm yellow
        "#dda0dd",  # Plum
    ]

    # Common layout settings
    @staticmethod
    def get_common_layout(title: str, **kwargs) -> Dict[str, Any]:
        """Get common layout settings with optional overrides."""
        layout = {
            "title": {
                "text": title,
                "x": 0.5,
                "xanchor": "center",
                "font": {
                    "size": 32,
                    "color": "white",
                    "family": VizStyling.FONT_FAMILY,
                },
            },
            "plot_bgcolor": "rgba(0,0,0,0)",
            "paper_bgcolor": "rgba(0,0,0,0)",
            "font": {"color": "white", "size": 14, "family": VizStyling.FONT_FAMILY},
            "hoverlabel": {
                "bgcolor": "rgba(15,15,15,0.95)",
                "bordercolor": "rgba(255,255,255,0.3)",
                "font_size": 14,
                "font_family": VizStyling.FONT_FAMILY,
            },
        }

        # Apply any overrides
        layout.update(kwargs)
        return layout


class VizExporter:
    """Centralized export functionality maintaining exact output compatibility."""

    @staticmethod
    def ensure_outputs_dir():
        """Ensure outputs directory exists."""
        os.makedirs("outputs", exist_ok=True)

    @staticmethod
    def create_iframe_optimized_html(
        fig: go.Figure,
        filename: str,
        title: str,
        background_gradient: str = "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
    ) -> None:
        """Create HTML file specifically optimized for iframe embedding.

        Maintains exact compatibility with original implementations.
        """
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
            background: {background_gradient};
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
        
        ::-webkit-scrollbar {{
            width: 4px;
        }}
        
        ::-webkit-scrollbar-track {{
            background: rgba(255,255,255,0.1);
        }}
        
        ::-webkit-scrollbar-thumb {{
            background: rgba(255,255,255,0.3);
            border-radius: 2px;
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

    @staticmethod
    def export_figure(
        fig: go.Figure,
        filename_base: str,
        title: str = None,
        use_iframe_html: bool = True,
        background_gradient: str = "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
    ) -> None:
        """Export figure as both HTML and PNG maintaining exact compatibility."""
        VizExporter.ensure_outputs_dir()

        html_path = f"outputs/{filename_base}.html"
        png_path = f"outputs/{filename_base}.png"

        if use_iframe_html:
            # Use iframe-optimized HTML (matches original implementations)
            VizExporter.create_iframe_optimized_html(
                fig, html_path, title or filename_base, background_gradient
            )
            print(f"✓ Saved iframe-optimized HTML: {html_path}")
        else:
            # Use standard HTML export (for files that used this approach)
            fig.write_html(
                html_path,
                config={
                    "displayModeBar": True,
                    "responsive": True,
                    "toImageButtonOptions": {
                        "format": "png",
                        "filename": filename_base,
                        "height": 1080,
                        "width": 1920,
                        "scale": 2,
                    },
                },
                include_plotlyjs="cdn",
            )
            print(f"✓ Saved HTML: {html_path}")

        # Export PNG with high resolution (maintaining original settings)
        try:
            fig.write_image(
                png_path, width=1920, height=1080, scale=2, engine="kaleido"
            )
            print(f"✓ Saved PNG: {png_path}")
        except Exception as e:
            print(f"⚠️  PNG export failed for {filename_base}: {e}")
            print("   Install kaleido: pip install kaleido")


class VizDataProcessor:
    """Centralized data processing utilities."""

    @staticmethod
    def get_transport_mode_mapping() -> Dict[str, str]:
        """Get Hebrew to English transportation mode mapping."""
        return {
            "ברגל": "walking",
            "אופניים": "bicycle",
            "אופניים/קורקינט חשמלי": "ebike",
            "אופניים חשמליים/קורקינט": "ebike",
            "רכב": "car",
            "אוטובוס": "bus",
            "רכבת": "train",
            "רכיבה על סוסים": "horseback",
            "אחר": "other",
        }

    @staticmethod
    def get_transport_mode_display_mapping() -> Dict[str, str]:
        """Get Hebrew to English display names for transportation modes."""
        return {
            "ברגל": "Walking",
            "אופניים": "Bicycle",
            "אופניים/קורקינט חשמלי": "Electric Bike/Scooter",
            "אופניים חשמליים/קורקינט": "E-bike",
            "רכב": "Car",
            "אוטובוס": "Bus",
            "רכבת": "Train",
            "רכיבה על סוסים": "Horseback",
            "אחר": "Other",
            "": "Unknown",
            "Unknown": "Unknown",
        }

    @staticmethod
    def get_route_choice_factors() -> Dict[str, str]:
        """Get route choice factor mapping."""
        return {
            "Routechoice-Distance": "Distance",
            "Routechoice-Time": "Time",
            "Routechoice-Shadow": "Shade",
            "Routechoice-Stores": "Stores",
            "Routechoice-Friends": "Friends",
            "Routechoice-Convenience": "Convenience",
            "Routechoice-Work": "Work",
        }

    @staticmethod
    def get_bgu_gates() -> Dict[str, Dict[str, Any]]:
        """Get BGU gate data."""
        return {
            "uni_south_3": {"lat": 31.261222, "lng": 34.801138, "name": "South Gate 3"},
            "uni_north_3": {"lat": 31.263911, "lng": 34.799290, "name": "North Gate 3"},
            "uni_west": {"lat": 31.262500, "lng": 34.805528, "name": "West Gate"},
        }

    @staticmethod
    def calculate_percentages(counts: Dict[str, int]) -> Dict[str, float]:
        """Calculate percentages from counts dictionary."""
        total = sum(counts.values())
        if total == 0:
            return {k: 0.0 for k in counts.keys()}
        return {k: (v / total) * 100 for k, v in counts.items()}

    @staticmethod
    def get_statistics_summary(data: pd.Series) -> Dict[str, Any]:
        """Get comprehensive statistics for a pandas Series."""
        valid_data = data.dropna()
        if len(valid_data) == 0:
            return {"count": 0, "mean": 0, "std": 0, "value_counts": {}}

        return {
            "count": len(valid_data),
            "mean": float(valid_data.mean()),
            "std": float(valid_data.std()),
            "value_counts": valid_data.value_counts().to_dict(),
        }


class VizMapUtils:
    """Map and coordinate utilities for consolidation."""

    @staticmethod
    def interpolate_color(color1: str, color2: str, factor: float) -> str:
        """Interpolate between two hex colors based on factor (0-1)."""

        def hex_to_rgb(hex_color):
            hex_color = hex_color.lstrip("#")
            return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))

        def rgb_to_hex(rgb):
            return "#{:02x}{:02x}{:02x}".format(int(rgb[0]), int(rgb[1]), int(rgb[2]))

        rgb1 = hex_to_rgb(color1)
        rgb2 = hex_to_rgb(color2)
        interpolated = tuple(rgb1[i] + (rgb2[i] - rgb1[i]) * factor for i in range(3))
        return rgb_to_hex(interpolated)

    @staticmethod
    def get_intensity_color(intensity: float) -> str:
        """Get smooth gradient color based on intensity level using green palette."""
        color_stops = [
            (0.0, "#006400"),  # Dark Green - Low usage
            (0.25, "#228B22"),  # Forest Green - Low-medium usage
            (0.5, "#32CD32"),  # Lime Green - Medium usage
            (0.75, "#90EE90"),  # Light Green - High-medium usage
            (1.0, "#E8F5E8"),  # Very Light Green - High usage
        ]
        intensity = max(0.0, min(1.0, intensity))

        for i in range(len(color_stops) - 1):
            if intensity <= color_stops[i + 1][0]:
                segment_start, color1 = color_stops[i]
                segment_end, color2 = color_stops[i + 1]
                if segment_end == segment_start:
                    return color1
                local_factor = (intensity - segment_start) / (
                    segment_end - segment_start
                )
                return VizMapUtils.interpolate_color(color1, color2, local_factor)
        return color_stops[-1][1]

    @staticmethod
    def get_intensity_color_blend(intensity: float) -> str:
        """Get smooth gradient color for route lines."""
        color_stops = [
            (0.0, "#004D00"),  # Very Dark Green - Low usage
            (0.25, "#006400"),  # Dark Green - Low-medium usage
            (0.5, "#228B22"),  # Forest Green - Medium usage
            (0.75, "#32CD32"),  # Lime Green - High-medium usage
            (1.0, "#90EE90"),  # Light Green - High usage
        ]
        intensity = max(0.0, min(1.0, intensity))

        for i in range(len(color_stops) - 1):
            if intensity <= color_stops[i + 1][0]:
                segment_start, color1 = color_stops[i]
                segment_end, color2 = color_stops[i + 1]
                if segment_end == segment_start:
                    return color1
                local_factor = (intensity - segment_start) / (
                    segment_end - segment_start
                )
                return VizMapUtils.interpolate_color(color1, color2, local_factor)
        return color_stops[-1][1]


class VizChartBuilder:
    """Common chart creation utilities to reduce duplication."""

    @staticmethod
    def create_bar_chart(
        x_data: list,
        y_data: list,
        title: str,
        colors: list = None,
        customdata: list = None,
        hovertemplate: str = None,
    ) -> go.Figure:
        """Create a standardized bar chart with common styling."""
        fig = go.Figure()

        if colors is None:
            colors = styling.MODERN_COLORS[: len(x_data)]

        fig.add_trace(
            go.Bar(
                x=x_data,
                y=y_data,
                marker=dict(
                    color=colors,
                    line=dict(color="rgba(255,255,255,0.15)", width=1),
                    opacity=0.9,
                ),
                hovertemplate=hovertemplate
                or "<b>%{x}</b><br>Count: %{y}<extra></extra>",
                customdata=customdata,
            )
        )

        fig.update_layout(
            **styling.get_common_layout(title),
            xaxis=dict(
                tickfont={"size": 14, "color": "rgba(255,255,255,0.9)"},
                showgrid=False,
                zeroline=False,
                showline=False,
                tickangle=-15,
            ),
            yaxis=dict(
                tickfont={"size": 14, "color": "rgba(255,255,255,0.8)"},
                showgrid=True,
                gridwidth=0.5,
                gridcolor="rgba(255,255,255,0.08)",
                zeroline=False,
                showline=False,
                range=[0, max(y_data) * 1.1] if y_data else [0, 10],
                dtick=max(1, max(y_data) // 5) if y_data else 1,
            ),
            margin=dict(l=60, r=40, t=100, b=50),
            autosize=True,
            showlegend=False,
        )

        return fig

    @staticmethod
    def create_pie_chart(
        labels: list,
        values: list,
        title: str,
        colors: list = None,
        hole: float = 0.0,
        textinfo: str = "label+percent",
    ) -> go.Figure:
        """Create a standardized pie chart with common styling."""
        fig = go.Figure()

        fig.add_trace(
            go.Pie(
                labels=labels,
                values=values,
                hole=hole,
                marker=dict(
                    colors=colors or styling.MODERN_COLORS[: len(labels)],
                    line=dict(color="rgba(255,255,255,0.8)", width=3),
                ),
                textinfo=textinfo,
                texttemplate="<b>%{label}</b><br>%{percent}",
                textposition="outside",
                textfont=dict(size=16, color="white", family=styling.FONT_FAMILY),
                hovertemplate="<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percent}<extra></extra>",
                sort=False,
            )
        )

        fig.update_layout(
            **styling.get_common_layout(title),
            margin=dict(l=80, r=180, t=120, b=40),
            autosize=True,
            showlegend=True,
            legend=dict(
                orientation="v",
                yanchor="middle",
                y=0.5,
                xanchor="left",
                x=1.01,
                font=dict(size=24, color="white", family=styling.FONT_FAMILY),
                bgcolor="rgba(255,255,255,0.1)",
                bordercolor="rgba(255,255,255,0.3)",
                borderwidth=2,
                itemsizing="constant",
                itemwidth=60,
            ),
        )

        return fig

    @staticmethod
    def create_grouped_bar_chart(
        categories: list, data_series: Dict[str, list], title: str, colors: list = None
    ) -> go.Figure:
        """Create a standardized grouped bar chart."""
        fig = go.Figure()

        if colors is None:
            colors = styling.MODERN_COLORS

        for i, (series_name, values) in enumerate(data_series.items()):
            fig.add_trace(
                go.Bar(
                    name=series_name,
                    x=categories,
                    y=values,
                    marker=dict(
                        color=colors[i % len(colors)],
                        line=dict(color="rgba(255,255,255,0.15)", width=1),
                        opacity=0.9,
                    ),
                    hovertemplate=f"<b>%{{x}}</b><br>{series_name}: %{{y}}<extra></extra>",
                )
            )

        fig.update_layout(
            **styling.get_common_layout(title),
            barmode="group",
            xaxis=dict(
                tickfont={"size": 16, "color": "rgba(255,255,255,0.9)"},
                color="white",
                showgrid=False,
                zeroline=False,
                showline=False,
            ),
            yaxis=dict(
                tickfont={"size": 14, "color": "rgba(255,255,255,0.8)"},
                gridcolor="rgba(255,255,255,0.08)",
                color="white",
                showgrid=True,
                gridwidth=0.5,
                zeroline=False,
                showline=False,
            ),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="center",
                x=0.5,
                bgcolor="rgba(255,255,255,0.1)",
                bordercolor="rgba(255,255,255,0.3)",
                borderwidth=2,
                font={"size": 22, "family": styling.FONT_FAMILY},
            ),
            margin=dict(l=80, r=80, t=110, b=80),
            autosize=True,
        )

        return fig


# Global instances for easy access
data_loader = VizDataLoader()
styling = VizStyling()
exporter = VizExporter()
processor = VizDataProcessor()
chart_builder = VizChartBuilder()
map_utils = VizMapUtils()
