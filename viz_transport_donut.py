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

def get_transport_mode_data(df: pd.DataFrame) -> dict:
    """Extract transportation mode data from routes."""
    # Load the exported route data if available
    try:
        with open('outputs/bgu_mobility_data.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        transport_modes = data['statistics']['transportModes']
        print(f"✓ Loaded transport modes from exported data: {transport_modes}")
        return transport_modes
        
    except FileNotFoundError:
        print("⚠️  Exported data not found, calculating from raw data...")
        
        # Fallback: parse from raw data
        mode_translation = {
            'ברגל': 'walking',
            'אופניים': 'bicycle',
            'אופניים/קורקינט חשמלי': 'ebike',
            'רכב': 'car',
            'אוטובוס': 'bus',
            'רכבת': 'train'
        }
        
        mode_counts = {'walking': 0, 'bicycle': 0, 'ebike': 0, 'car': 0, 'bus': 0, 'train': 0, 'unknown': 0}
        
        for idx, row in df.iterrows():
            transport_mode = row.get('Transportation-Mode', '')
            if pd.isna(transport_mode) or transport_mode == '':
                english_mode = 'unknown'
            else:
                english_mode = mode_translation.get(transport_mode, 'unknown')
            
            mode_counts[english_mode] += 1
        
        # Remove modes with 0 counts
        mode_counts = {k: v for k, v in mode_counts.items() if v > 0}
        return mode_counts

def create_transport_donut_chart(transport_data: dict) -> go.Figure:
    """Create donut chart for transportation modes with Vega-inspired styling."""
    
    # Vega-inspired color palette for transportation modes
    transport_colors = {
        'walking': '#2E8B57',     # Sea Green - natural, healthy
        'bicycle': '#FF6347',     # Tomato Red - energy, movement
        'ebike': '#9370DB',       # Medium Purple - modern, tech
        'car': '#4682B4',         # Steel Blue - solid, reliable
        'bus': '#DAA520',         # Goldenrod - public, shared
        'train': '#8B4513',       # Saddle Brown - traditional, heavy
        'unknown': '#808080'      # Gray - neutral
    }
    
    # Transportation mode display names without emojis
    mode_display_names = {
        'walking': 'Walking',
        'bicycle': 'Bicycle',
        'ebike': 'E-bike',
        'car': 'Car',
        'bus': 'Bus',
        'train': 'Train',
        'unknown': 'Unknown'
    }
    
    # Prepare data - sort by frequency
    sorted_modes = sorted(transport_data.items(), key=lambda x: x[1], reverse=True)
    modes = [mode for mode, count in sorted_modes]
    values = [count for mode, count in sorted_modes]
    colors = [transport_colors.get(mode, '#808080') for mode in modes]
    display_names = [mode_display_names.get(mode, mode.title()) for mode in modes]
    
    # Calculate percentages
    total = sum(values)
    percentages = [(v/total)*100 for v in values]
    
    fig = go.Figure()
    
    # Add the donut chart
    fig.add_trace(go.Pie(
        labels=display_names,
        values=values,
        hole=0.45,  # Donut hole size
        marker=dict(
            colors=colors,
            line=dict(color='rgba(255,255,255,0.6)', width=2)
        ),
        textinfo='label+percent',
        texttemplate='<b>%{label}</b><br>%{percent}',
        textposition='auto',
        textfont=dict(
            size=13,
            color='white',
            family='Inter, system-ui, sans-serif'
        ),
        hovertemplate='<b>%{label}</b><br>Trips: %{value}<br>Percentage: %{percent}<extra></extra>',
        sort=False  # Keep sorted order
    ))
    
    # Add center text showing total
    fig.add_annotation(
        text=f"<b>{total}</b><br><span style='font-size: 14px; color: rgba(255,255,255,0.8);'>Total Trips</span>",
        x=0.5, y=0.5,
        font=dict(size=24, color='white', family='Inter'),
        showarrow=False,
        align='center'
    )
    
    fig.update_layout(
        title={
            'text': 'Transportation Mode Distribution<br><span style="font-size: 16px; color: rgba(255,255,255,0.7); font-weight: 400;">How students travel to campus</span>',
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
            borderwidth=1,
            traceorder='normal'
        ),
        hoverlabel=dict(
            bgcolor='rgba(15,15,15,0.95)',
            bordercolor='rgba(255,255,255,0.3)',
            font_size=12,
            font_family='Inter, system-ui, sans-serif'
        ),
        # Add subtle animation
        transition=dict(duration=500, easing='cubic-in-out')
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
        
        /* Vega-inspired hover effects */
        .slice:hover {{
            transform: scale(1.05);
            transition: transform 0.2s ease;
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
    """Main function to create transportation modes donut chart."""
    print("🚇 Creating Transportation Modes Donut Chart")
    print("=" * 50)
    
    # Load data
    df = load_processed_data()
    
    # Get transportation mode data
    transport_data = get_transport_mode_data(df)
    
    if not transport_data or sum(transport_data.values()) == 0:
        print("⚠️  No transportation mode data found!")
        return None
    
    # Create donut chart
    fig = create_transport_donut_chart(transport_data)
    export_figure(fig, 'transport_modes_donut', 'Transportation Modes Donut')
    
    # Print statistics
    total_trips = sum(transport_data.values())
    print(f"\n📊 Transportation Mode Statistics:")
    for mode, count in sorted(transport_data.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / total_trips) * 100
        print(f"   • {mode.title()}: {count} trips ({percentage:.1f}%)")
    
    print(f"\n✨ Transportation modes donut chart completed!")
    print("   • Vega-inspired color palette")
    print("   • Donut chart with center total display")
    print("   • Sorted by frequency")
    print("   • Optimized for iframe embedding")
    
    return fig

if __name__ == "__main__":
    os.makedirs('outputs', exist_ok=True)
    main() 