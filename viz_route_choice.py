#!/usr/bin/env python3
"""
BGU Mobility Survey - Route Choice Factor Analysis
Creates interactive spider/radar charts showing importance of different route choice factors.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import os

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

def prepare_route_choice_data(df: pd.DataFrame) -> pd.DataFrame:
    """Prepare and validate route choice factor data."""
    
    # Route choice factors with English labels
    factors = {
        'Routechoice-Distance': 'Distance',
        'Routechoice-Time': 'Time', 
        'Routechoice-Shadow': 'Shade',
        'Routechoice-Stores': 'Stores',
        'Routechoice-Friends': 'Friends',
        'Routechoice-Convenience': 'Convenience',
        'Routechoice-Work': 'Work'
    }
    
    # Extract route choice data
    route_data = df[list(factors.keys())].copy()
    
    # Convert to numeric and handle missing values
    for col in factors.keys():
        route_data[col] = pd.to_numeric(route_data[col], errors='coerce')
    
    # Calculate statistics for each factor
    factor_stats = {}
    
    print(f"🛣️  Route Choice Factor Analysis:")
    print(f"Note: Scale is 1-5 where 1=Most Important, 5=Least Important")
    
    for original_col, english_name in factors.items():
        valid_data = route_data[original_col].dropna()
        
        if len(valid_data) > 0:
            # Invert scale for better visualization (higher = more important)
            # Original: 1=most important, 5=least important
            # Inverted: 5=most important, 1=least important
            inverted_mean = 6 - valid_data.mean()
            
            factor_stats[english_name] = {
                'mean_importance': inverted_mean,
                'original_mean': valid_data.mean(),
                'count': len(valid_data),
                'std': valid_data.std()
            }
            
            print(f"  {english_name}: {len(valid_data)} responses, avg={valid_data.mean():.2f} (importance={inverted_mean:.2f})")
        else:
            factor_stats[english_name] = {
                'mean_importance': 0,
                'original_mean': 0,
                'count': 0,
                'std': 0
            }
    
    return factor_stats, route_data

def create_spider_chart(factor_stats: dict) -> go.Figure:
    """Create a spider/radar chart for route choice factors."""
    
    # Prepare data for spider chart
    factors = list(factor_stats.keys())
    values = [factor_stats[factor]['mean_importance'] for factor in factors]
    counts = [factor_stats[factor]['count'] for factor in factors]
    
    # Close the polygon by adding first value at the end
    factors_closed = factors + [factors[0]]
    values_closed = values + [values[0]]
    counts_closed = counts + [counts[0]]
    
    fig = go.Figure()
    
    # Add the main radar chart
    fig.add_trace(go.Scatterpolar(
        r=values_closed,
        theta=factors_closed,
        fill='toself',
        fillcolor='rgba(0, 212, 255, 0.3)',
        line=dict(color='#00d4ff', width=4),
        marker=dict(color='#00d4ff', size=12),
        name='Average Ranked Importance',
        hovertemplate='<b>%{theta}</b><br>Importance: %{r:.2f}/5<br>Responses: %{customdata}<extra></extra>',
        customdata=counts_closed
    ))
    
    # Update layout for responsive full-screen design
    fig.update_layout(
        title={
            'text': 'Route Choice Factors - Importance Rankings<br>',
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 38, 'color': 'white', 'family': 'Inter, system-ui, sans-serif'}
        },
        polar=dict(
            bgcolor='rgba(0,0,0,0.1)',
            radialaxis=dict(
                visible=True,
                range=[0, 5],
                tickfont=dict(size=18, color='white'),
                gridcolor='rgba(128,128,128,0.3)',
                gridwidth=2,
                linecolor='rgba(128,128,128,0.5)',
                tickmode='linear',
                tick0=0,
                dtick=1
            ),
            angularaxis=dict(
                tickfont=dict(size=20, color='white'),
                linecolor='rgba(128,128,128,0.5)',
                gridcolor='rgba(128,128,128,0.3)'
            )
        ),
        paper_bgcolor='#0a0a0a',
        plot_bgcolor='rgba(0,0,0,0)',
        font={'color': 'white', 'size': 20, 'family': 'Inter, system-ui, sans-serif'},
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom", 
            y=-0.15,
            xanchor="center",
            x=0.5,
            bgcolor='rgba(0,0,0,0)',
            bordercolor='rgba(0,0,0,0)',
            borderwidth=0,
            font={'size': 20, 'family': 'Inter, system-ui, sans-serif'}
        ),
        margin=dict(l=120, r=120, t=150, b=120),
        autosize=True,
        hoverlabel=dict(
            bgcolor='rgba(15,15,15,0.95)',
            bordercolor='rgba(255,255,255,0.3)',
            font_size=18,
            font_family='Inter, system-ui, sans-serif'
        )
    )
    
    return fig

def create_factor_comparison_chart(factor_stats: dict) -> go.Figure:
    """Create a vertical bar chart comparing factor importance."""
    
    # Sort factors by importance
    sorted_factors = sorted(factor_stats.items(), key=lambda x: x[1]['mean_importance'], reverse=True)
    
    factors = [item[0] for item in sorted_factors]
    importance = [item[1]['mean_importance'] for item in sorted_factors]
    counts = [item[1]['count'] for item in sorted_factors]
    
    # Green gradient - lighter greens for higher importance
    colors = [
        '#6ee7b7',  # Very light green (most important)
        '#34d399',  # Light green
        '#10b981',  # Medium-light green
        '#059669',  # Medium green
        '#047857',  # Medium-dark green
        '#065f46',  # Dark green
        '#064e3b'   # Very dark green (least important)
    ]
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=factors,
        y=importance,
        marker=dict(
            color=colors[:len(factors)],
            line=dict(color='rgba(255,255,255,0.15)', width=1),
            opacity=0.9
        ),
        hovertemplate='<b>%{x}</b><br>Importance: %{y:.2f}/5<br>Responses: %{customdata}<extra></extra>',
        customdata=counts
    ))
    
    fig.update_layout(
        title={
            'text': 'Route Choice Factors - Ranked by Importance',
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 38, 'color': 'white', 'family': 'Inter, system-ui, sans-serif'}
        },
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='#0a0a0a',
        font={'color': 'white', 'size': 20, 'family': 'Inter, system-ui, sans-serif'},
        xaxis=dict(
            tickfont={'size': 17, 'color': 'rgba(255,255,255,0.9)'},
            color='white',
            showgrid=False,
            zeroline=False,
            showline=False
        ),
        yaxis=dict(
            tickfont={'size': 17, 'color': 'rgba(255,255,255,0.8)'},
            gridcolor='rgba(255,255,255,0.08)',
            color='white',
            range=[0, 5],
            dtick=1,
            showgrid=True,
            gridwidth=0.5,
            zeroline=False,
            showline=False
        ),
        margin=dict(l=90, r=90, t=130, b=90),
        autosize=True,
        showlegend=False,
        hoverlabel=dict(
            bgcolor='rgba(15,15,15,0.95)',
            bordercolor='rgba(255,255,255,0.3)',
            font_size=18,
            font_family='Inter, system-ui, sans-serif'
        )
    )
    
    return fig

def create_response_count_chart(factor_stats: dict) -> go.Figure:
    """Create a chart showing response counts for each factor."""
    
    factors = list(factor_stats.keys())
    counts = [factor_stats[factor]['count'] for factor in factors]
    
    # Sort by count
    sorted_data = sorted(zip(factors, counts), key=lambda x: x[1], reverse=True)
    factors_sorted = [item[0] for item in sorted_data]
    counts_sorted = [item[1] for item in sorted_data]
    
    # Modern vibrant color palette
    colors = [
        '#00d4ff',  # Cyan
        '#ff6b6b',  # Coral
        '#4ecdc4',  # Teal
        '#45b7d1',  # Sky blue
        '#96ceb4',  # Mint
        '#ffeaa7',  # Warm yellow
        '#dda0dd'   # Plum
    ]
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=factors_sorted,
        y=counts_sorted,
        marker=dict(
            color=colors[:len(factors_sorted)],
            line=dict(color='rgba(255,255,255,0.15)', width=1),
            opacity=0.9
        ),
        hovertemplate='<b>%{x}</b><br>Responses: %{y}<extra></extra>'
    ))
    
    fig.update_layout(
        title={
            'text': 'Response Rates by Route Choice Factor',
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 38, 'color': 'white', 'family': 'Inter, system-ui, sans-serif'}
        },
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='#0a0a0a',
        font={'color': 'white', 'size': 20, 'family': 'Inter, system-ui, sans-serif'},
        xaxis=dict(
            tickfont={'size': 17, 'color': 'rgba(255,255,255,0.9)'},
            color='white',
            showgrid=False,
            zeroline=False,
            showline=False
        ),
        yaxis=dict(
            tickfont={'size': 17, 'color': 'rgba(255,255,255,0.8)'},
            gridcolor='rgba(255,255,255,0.08)',
            color='white',
            showgrid=True,
            gridwidth=0.5,
            zeroline=False,
            showline=False
        ),
        margin=dict(l=90, r=90, t=130, b=90),
        autosize=True,
        showlegend=False,
        hoverlabel=dict(
            bgcolor='rgba(15,15,15,0.95)',
            bordercolor='rgba(255,255,255,0.3)',
            font_size=18,
            font_family='Inter, system-ui, sans-serif'
        )
    )
    
    return fig

def export_figure(fig: go.Figure, filename_base: str) -> None:
    """Export figure as both HTML and PNG with proper sizing."""
    html_path = f'outputs/{filename_base}.html'
    png_path = f'outputs/{filename_base}.png'
    
    # Export HTML with responsive sizing
    fig.write_html(
        html_path, 
        config={
            'displayModeBar': True,
            'responsive': True,
            'toImageButtonOptions': {
                'format': 'png',
                'filename': filename_base,
                'height': 1080,
                'width': 1920,
                'scale': 2
            }
        },
        include_plotlyjs='cdn'
    )
    print(f"✓ Saved HTML: {html_path}")
    
    # Export PNG with high resolution
    try:
        fig.write_image(
            png_path,
            width=1920,
            height=1080,
            scale=2,
            engine='kaleido'
        )
        print(f"✓ Saved PNG: {png_path}")
    except Exception as e:
        print(f"⚠️  PNG export failed for {filename_base}: {e}")
        print("   Install kaleido: pip install kaleido")

def main():
    """Main function to create route choice visualizations."""
    print("🛣️  Creating Route Choice Factor Visualizations")
    print("=" * 50)
    
    # Load data
    df = load_processed_data()
    
    # Prepare route choice data
    factor_stats, route_data = prepare_route_choice_data(df)
    
    # Create spider chart with responsive sizing
    spider_fig = create_spider_chart(factor_stats)
    export_figure(spider_fig, 'route_choice_spider')
    
    # Create comparison bar chart
    comparison_fig = create_factor_comparison_chart(factor_stats)
    export_figure(comparison_fig, 'route_choice_comparison')
    
    # Create response count chart
    count_fig = create_response_count_chart(factor_stats)
    export_figure(count_fig, 'route_choice_responses')
    
    print("\n🎯 Route choice analysis completed!")
    print("📱 HTML files are now responsive and will fill the browser window")
    print("🖼️  PNG files exported at 1920x1080 resolution")
    
    return spider_fig, comparison_fig, count_fig

if __name__ == "__main__":
    # Create outputs directory
    os.makedirs('outputs', exist_ok=True)
    
    main()