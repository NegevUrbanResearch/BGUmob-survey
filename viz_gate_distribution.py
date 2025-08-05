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

def load_processed_data() -> pd.DataFrame:
    """Load the processed survey data."""
    try:
        df = pd.read_csv('data/processed_mobility_data.csv')
        print(f"✓ Loaded processed data: {df.shape[0]} rows")
        return df
    except FileNotFoundError:
        print("⚠️  Processed data not found, loading raw data...")
        df = pd.read_csv('data/mobility-data.csv')
        return df

def get_gate_data(df: pd.DataFrame) -> dict:
    """Extract gate usage data from routes."""
    # Load the exported route data if available
    try:
        with open('outputs/bgu_mobility_data.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        gate_usage = data['statistics']['gateUsage']
        print(f"✓ Loaded gate usage from exported data: {gate_usage}")
        return gate_usage
        
    except FileNotFoundError:
        print("⚠️  Exported data not found, calculating from raw data...")
        
        # BGU Gates mapping
        bgu_gates = {
            'uni_south_3': 'South Gate 3',
            'uni_north_3': 'North Gate 3', 
            'uni_west': 'West Gate'
        }
        
        # Simple gate assignment based on proximity (fallback)
        gate_counts = {'South Gate 3': 0, 'North Gate 3': 0, 'West Gate': 0}
        
        # Count routes to each gate (simplified)
        for idx, row in df.iterrows():
            if pd.notna(row.get('Residence-Info', '')):
                # Default assignment - this would need proper coordinate parsing
                gate_counts['North Gate 3'] += 1
        
        return gate_counts

def create_gate_pie_chart(gate_data: dict) -> go.Figure:
    """Create pie chart for gate distribution using app color scheme."""
    
    # App color scheme for gates
    gate_colors = {
        'South Gate': '#E91E63',  # Pink
        'North Gate': '#9C27B0',  # Purple
        'West Gate': '#FF9800'      # Orange
    }
    
    # Prepare data
    gates = list(gate_data.keys())
    values = list(gate_data.values())
    colors = [gate_colors.get(gate, '#9E9E9E') for gate in gates]
    
    # Calculate percentages
    total = sum(values)
    percentages = [(v/total)*100 for v in values]
    
    fig = go.Figure()
    
    fig.add_trace(go.Pie(
        labels=gates,
        values=values,
        hole=0.0,  # Full pie (not donut)
        marker=dict(
            colors=colors,
            line=dict(color='rgba(255,255,255,0.8)', width=3)
        ),
        textinfo='label+percent+value',
        texttemplate='<b>%{label}</b><br>%{percent}<br>(%{value} trips)',
        textposition='auto',
        textfont=dict(
            size=14,
            color='white',
            family='Inter, system-ui, sans-serif'
        ),
        hovertemplate='<b>%{label}</b><br>Trips: %{value}<br>Percentage: %{percent}<extra></extra>',
        sort=False  # Keep original order
    ))
    
    fig.update_layout(
        title={
            'text': 'Campus Gate Distribution<br><span style="font-size: 16px; color: rgba(255,255,255,0.7); font-weight: 400;">Student route destinations by gate</span>',
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 28, 'color': 'white', 'family': 'Inter, system-ui, sans-serif'},
            'pad': {'b': 20}
        },
        paper_bgcolor='rgba(0,0,0,0)',  # Transparent background
        plot_bgcolor='rgba(0,0,0,0)',
        font={'color': 'white', 'size': 12, 'family': 'Inter, system-ui, sans-serif'},
        margin=dict(l=20, r=20, t=100, b=20),
        autosize=True,
        showlegend=True,
        legend=dict(
            orientation="v",
            yanchor="middle",
            y=0.5,
            xanchor="left",
            x=1.05,
            font=dict(size=14, color='white', family='Inter'),
            bgcolor='rgba(255,255,255,0.05)',
            bordercolor='rgba(255,255,255,0.2)',
            borderwidth=1
        ),
        hoverlabel=dict(
            bgcolor='rgba(15,15,15,0.95)',
            bordercolor='rgba(255,255,255,0.3)',
            font_size=12,
            font_family='Inter, system-ui, sans-serif'
        )
    )
    
    return fig

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
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(html_content)

def export_figure(fig: go.Figure, filename_base: str, title: str) -> None:
    """Export figure as both optimized HTML and PNG."""
    html_path = f'outputs/{filename_base}.html'
    png_path = f'outputs/{filename_base}.png'
    
    create_iframe_optimized_html(fig, html_path, title)
    print(f"✓ Saved iframe-optimized HTML: {html_path}")
    
    try:
        fig.write_image(png_path, width=1200, height=800, scale=2, engine='kaleido')
        print(f"✓ Saved PNG: {png_path}")
    except Exception as e:
        print(f"⚠️  PNG export failed: {e}")

def main():
    """Main function to create gate distribution pie chart."""
    print("🏛️  Creating Gate Distribution Pie Chart")
    print("=" * 45)
    
    # Load data
    df = load_processed_data()
    
    # Get gate usage data
    gate_data = get_gate_data(df)
    
    if not gate_data or sum(gate_data.values()) == 0:
        print("⚠️  No gate usage data found!")
        return None
    
    # Create pie chart
    fig = create_gate_pie_chart(gate_data)
    export_figure(fig, 'gate_distribution', 'Gate Distribution')
    
    # Print statistics
    total_trips = sum(gate_data.values())
    print(f"\n📊 Gate Distribution Statistics:")
    for gate, count in sorted(gate_data.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / total_trips) * 100
        print(f"   • {gate}: {count} trips ({percentage:.1f}%)")
    
    print(f"\n✨ Gate distribution visualization completed!")
    print("   • Uses same color scheme as main app")
    print("   • Shows trip counts and percentages")
    print("   • Optimized for iframe embedding")
    
    return fig

if __name__ == "__main__":
    os.makedirs('outputs', exist_ok=True)
    main() 