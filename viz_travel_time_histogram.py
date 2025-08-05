#!/usr/bin/env python3
"""
BGU Mobility Survey - Travel Time Histogram
Creates a histogram showing distribution of travel times to university based on OTP analysis.
"""

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import numpy as np
import os
import json
from typing import List, Dict, Tuple

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

def get_travel_times_from_routes() -> Dict:
    """Extract travel times from OTP route analysis."""
    try:
        with open('outputs/bgu_mobility_data.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        routes = data['routes']
        
        # Calculate travel times from distances and transport modes
        travel_times = []
        transport_modes = []
        
        # Average speeds by transport mode (km/h)
        speed_mapping = {
            'walking': 4.5,    # 4.5 km/h
            'bicycle': 15.0,   # 15 km/h  
            'ebike': 20.0,     # 20 km/h
            'car': 30.0,       # 30 km/h in urban areas
            'bus': 20.0,       # 20 km/h with stops
            'train': 40.0,     # 40 km/h average
            'unknown': 4.5     # Default to walking speed
        }
        
        for route in routes:
            if 'distance' in route and 'transportMode' in route:
                distance_km = route['distance']
                mode = route['transportMode'] or 'unknown'
                speed_kmh = speed_mapping.get(mode, 4.5)
                
                # Calculate time in minutes
                time_minutes = (distance_km / speed_kmh) * 60
                
                travel_times.append(time_minutes)
                transport_modes.append(mode)
        
        print(f"✓ Calculated {len(travel_times)} travel times from route data")
        
        return {
            'travel_times': travel_times,
            'transport_modes': transport_modes,
            'avg_time': np.mean(travel_times) if travel_times else 0,
            'median_time': np.median(travel_times) if travel_times else 0,
            'std_time': np.std(travel_times) if travel_times else 0,
            'min_time': np.min(travel_times) if travel_times else 0,
            'max_time': np.max(travel_times) if travel_times else 0
        }
        
    except FileNotFoundError:
        print("⚠️  Route data not found")
        return {
            'travel_times': [], 'transport_modes': [], 
            'avg_time': 0, 'median_time': 0, 'std_time': 0,
            'min_time': 0, 'max_time': 0
        }

def analyze_travel_times_by_mode(travel_data: Dict) -> Dict:
    """Analyze travel times broken down by transportation mode."""
    if not travel_data['travel_times']:
        return {}
    
    times = travel_data['travel_times']
    modes = travel_data['transport_modes']
    
    mode_analysis = {}
    unique_modes = set(modes)
    
    for mode in unique_modes:
        mode_times = [times[i] for i, m in enumerate(modes) if m == mode]
        
        if mode_times:
            mode_analysis[mode] = {
                'times': mode_times,
                'count': len(mode_times),
                'avg_time': np.mean(mode_times),
                'median_time': np.median(mode_times),
                'std_time': np.std(mode_times),
                'min_time': np.min(mode_times),
                'max_time': np.max(mode_times)
            }
    
    return mode_analysis

def create_travel_time_histogram(travel_data: Dict) -> go.Figure:
    """Create histogram of travel times with mode breakdown."""
    
    if not travel_data['travel_times']:
        # Create empty chart
        fig = go.Figure()
        fig.add_annotation(
            text="No travel time data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=20, color='white')
        )
        return fig
    
    # Transportation mode colors (consistent with other visualizations)
    mode_colors = {
        'walking': '#2E8B57',     # Sea Green
        'bicycle': '#FF6347',     # Tomato Red
        'ebike': '#9370DB',       # Medium Purple
        'car': '#4682B4',         # Steel Blue
        'bus': '#DAA520',         # Goldenrod
        'train': '#8B4513',       # Saddle Brown
        'unknown': '#808080'      # Gray
    }
    
    # Mode display names without emojis
    mode_display_names = {
        'walking': 'Walking',
        'bicycle': 'Bicycle',
        'ebike': 'E-bike',
        'car': 'Car',
        'bus': 'Bus',
        'train': 'Train',
        'unknown': 'Unknown'
    }
    
    fig = go.Figure()
    
    # Analyze by mode for stacked histogram
    mode_analysis = analyze_travel_times_by_mode(travel_data)
    
    # Create bins that work for all modes
    all_times = travel_data['travel_times']
    min_time, max_time = min(all_times), max(all_times)
    bin_size = (max_time - min_time) / 15  # 15 bins
    
    # Sort modes by frequency for better visual hierarchy
    sorted_modes = sorted(mode_analysis.items(), key=lambda x: x[1]['count'], reverse=True)
    
    for mode, mode_data in sorted_modes:
        color = mode_colors.get(mode, '#808080')
        display_name = mode_display_names.get(mode, mode.title())
        
        fig.add_trace(go.Histogram(
            x=mode_data['times'],
            name=display_name,
            marker=dict(
                color=color,
                line=dict(color='rgba(255,255,255,0.4)', width=1),
                opacity=0.8
            ),
            hovertemplate=f'<b>{display_name}</b><br>Travel Time: %{{x:.1f}} minutes<br>Count: %{{y}}<extra></extra>',
            xbins=dict(
                start=min_time,
                end=max_time,
                size=bin_size
            )
        ))
    
    # Add average line
    avg_time = travel_data['avg_time']
    if avg_time > 0:
        fig.add_vline(
            x=avg_time,
            line=dict(color='#ffffff', width=3, dash='dash'),
            annotation_text=f"Average: {avg_time:.1f} min",
            annotation_position="top"
        )
    
    # Add median line
    median_time = travel_data['median_time']
    if median_time > 0:
        fig.add_vline(
            x=median_time,
            line=dict(color='#ffff00', width=2, dash='dot'),
            annotation_text=f"Median: {median_time:.1f} min",
            annotation_position="bottom"
        )
    
    fig.update_layout(
        title={
            'text': 'Travel Time Distribution to Campus<br><span style="font-size: 18px; color: rgba(255,255,255,0.8); font-weight: 400;">Based on route distances and transportation modes</span>',
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 32, 'color': 'white', 'family': 'Inter, system-ui, sans-serif', 'weight': 700},
            'pad': {'b': 30}
        },
        xaxis=dict(
            title='Travel Time (minutes)',
            titlefont=dict(size=18, color='white', family='Inter, system-ui, sans-serif'),
            tickfont=dict(size=14, color='rgba(255,255,255,0.95)', family='Inter'),
            gridcolor='rgba(255,255,255,0.15)',
            showgrid=True,
            zeroline=False,
            showline=True,
            linecolor='rgba(255,255,255,0.4)',
            linewidth=2
        ),
        yaxis=dict(
            title='Number of Trips',
            titlefont=dict(size=18, color='white', family='Inter, system-ui, sans-serif'),
            tickfont=dict(size=14, color='rgba(255,255,255,0.95)', family='Inter'),
            gridcolor='rgba(255,255,255,0.15)',
            showgrid=True,
            zeroline=False,
            showline=True,
            linecolor='rgba(255,255,255,0.4)',
            linewidth=2
        ),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(15,15,30,0.3)',  # Subtle dark background for plot area
        font={'color': 'white', 'size': 14, 'family': 'Inter, system-ui, sans-serif'},
        margin=dict(l=100, r=120, t=140, b=90),
        autosize=True,
        barmode='stack',
        legend=dict(
            orientation="v",
            yanchor="top",
            y=0.98,
            xanchor="left",
            x=1.02,
            font=dict(size=18, color='white', family='Inter, system-ui, sans-serif', weight=500),
            bgcolor='rgba(255,255,255,0.08)',
            bordercolor='rgba(255,255,255,0.3)',
            borderwidth=2,
            itemsizing='constant',
            itemwidth=40,
            tracegroupgap=10
        ),
        hoverlabel=dict(
            bgcolor='rgba(15,15,15,0.98)',
            bordercolor='rgba(255,255,255,0.4)',
            font_size=14,
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
    """Main function to create travel time histogram."""
    print("⏱️  Creating Travel Time Histogram")
    print("=" * 40)
    
    # Load data
    df = load_processed_data()
    
    # Get travel time data
    travel_data = get_travel_times_from_routes()
    
    if not travel_data['travel_times']:
        print("⚠️  No travel time data found!")
        return None
    
    # Create histogram
    fig = create_travel_time_histogram(travel_data)
    export_figure(fig, 'travel_time_histogram', 'Travel Time Histogram')
    
    # Print analysis summary
    print(f"\n📊 Travel Time Analysis Summary:")
    print(f"   • Total trips analyzed: {len(travel_data['travel_times'])}")
    print(f"   • Average travel time: {travel_data['avg_time']:.1f} minutes")
    print(f"   • Median travel time: {travel_data['median_time']:.1f} minutes")
    print(f"   • Range: {travel_data['min_time']:.1f} - {travel_data['max_time']:.1f} minutes")
    
    # Mode breakdown
    mode_analysis = analyze_travel_times_by_mode(travel_data)
    if mode_analysis:
        print(f"\n🚇 Travel Time by Transportation Mode:")
        for mode, data in sorted(mode_analysis.items(), key=lambda x: x[1]['avg_time']):
            print(f"   • {mode.title()}: {data['avg_time']:.1f} min avg ({data['count']} trips)")
    
    print(f"\n✨ Travel time histogram completed!")
    print("   • Shows distribution by transportation mode")
    print("   • Includes average and median indicators")
    print("   • Based on route distances and realistic speeds")
    print("   • Stacked histogram for mode comparison")
    
    return fig

if __name__ == "__main__":
    os.makedirs('outputs', exist_ok=True)
    main() 