#!/usr/bin/env python3
"""
BGU Mobility Survey - Route Choice Factor Analysis
Creates interactive spider/radar charts optimized for iframe embedding.
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
    """Create a spider/radar chart optimized for iframe embedding."""
    
    # Prepare data for spider chart
    factors = list(factor_stats.keys())
    values = [factor_stats[factor]['mean_importance'] for factor in factors]
    counts = [factor_stats[factor]['count'] for factor in factors]
    
    # Close the polygon by adding first value at the end
    factors_closed = factors + [factors[0]]
    values_closed = values + [values[0]]
    counts_closed = counts + [counts[0]]
    
    fig = go.Figure()
    
    # Add background grid lines for better readability
    for i in range(1, 6):
        fig.add_trace(go.Scatterpolar(
            r=[i] * len(factors_closed),
            theta=factors_closed,
            mode='lines',
            line=dict(color='rgba(255,255,255,0.05)', width=1),
            showlegend=False,
            hoverinfo='skip'
        ))
    
    # Add shadow/background trace for depth
    fig.add_trace(go.Scatterpolar(
        r=values_closed,
        theta=factors_closed,
        fill='toself',
        fillcolor='rgba(0, 255, 136, 0.1)',
        line=dict(color='rgba(0, 255, 136, 0.4)', width=6),
        showlegend=False,
        hoverinfo='skip'
    ))
    
    # Add the main radar chart with enhanced styling
    fig.add_trace(go.Scatterpolar(
        r=values_closed,
        theta=factors_closed,
        fill='toself',
        fillcolor='rgba(0, 212, 255, 0.4)',
        line=dict(color='#00d4ff', width=4),
        marker=dict(
            color='#ffffff', 
            line=dict(color='#00d4ff', width=3), 
            size=16,
            symbol='circle'
        ),
        name='Student Priorities',
        hovertemplate='<b>%{theta}</b><br>Importance: %{r:.2f}/5<br>Responses: %{customdata}<extra></extra>',
        customdata=counts_closed
    ))
    
    # Optimized layout for iframe embedding
    fig.update_layout(
        title={
            'text': 'Route Choice Factors - Student Priorities<br><span style="font-size: 16px; color: rgba(255,255,255,0.7); font-weight: 400;">Scale: 1-5 where higher values indicate more important factors</span>',
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 28, 'color': 'white', 'family': 'Inter, system-ui, sans-serif'},
            'pad': {'b': 20}
        },
        polar=dict(
            bgcolor='rgba(10,10,30,0.15)',
            radialaxis=dict(
                visible=True,
                range=[0, 5],
                tickfont=dict(size=16, color='rgba(255,255,255,0.9)', family='Inter'),
                gridcolor='rgba(255,255,255,0.12)',
                gridwidth=1.5,
                linecolor='rgba(255,255,255,0.2)',
                tickmode='linear',
                tick0=0,
                dtick=1,
                tickvals=[1, 2, 3, 4, 5],
                ticktext=['1', '2', '3', '4', '5 (Most Important)']
            ),
            angularaxis=dict(
                tickfont=dict(size=18, color='white', family='Inter', weight=600),
                linecolor='rgba(255,255,255,0.3)',
                gridcolor='rgba(255,255,255,0.15)',
                gridwidth=1.5
            )
        ),
        paper_bgcolor='rgba(0,0,0,0)',  # Transparent background for iframe
        plot_bgcolor='rgba(0,0,0,0)',
        font={'color': 'white', 'size': 12, 'family': 'Inter, system-ui, sans-serif'},
        showlegend=False,
        # Optimized margins for iframe - extra top space for title and subtitle
        margin=dict(l=80, r=80, t=140, b=80),
        autosize=True,
        hoverlabel=dict(
            bgcolor='rgba(15,15,15,0.95)',
            bordercolor='rgba(255,255,255,0.3)',
            font_size=12,
            font_family='Inter, system-ui, sans-serif'
        )
    )
    
    return fig

def create_factor_comparison_chart(factor_stats: dict) -> go.Figure:
    """Create a vertical bar chart comparing factor importance - iframe optimized."""
    
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
            'font': {'size': 24, 'color': 'white', 'family': 'Inter, system-ui, sans-serif'},
            'pad': {'b': 10}
        },
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',  # Transparent background for iframe
        font={'color': 'white', 'size': 12, 'family': 'Inter, system-ui, sans-serif'},
        xaxis=dict(
            tickfont={'size': 12, 'color': 'rgba(255,255,255,0.9)'},
            color='white',
            showgrid=False,
            zeroline=False,
            showline=False,
            tickangle=-15
        ),
        yaxis=dict(
            tickfont={'size': 12, 'color': 'rgba(255,255,255,0.8)'},
            gridcolor='rgba(255,255,255,0.08)',
            color='white',
            range=[0, 5],
            dtick=1,
            showgrid=True,
            gridwidth=0.5,
            zeroline=False,
            showline=False
        ),
        # Optimized margins for iframe
        margin=dict(l=50, r=20, t=70, b=50),
        autosize=True,
        showlegend=False,
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
            background: transparent;
            font-family: 'Inter', system-ui, sans-serif;
            overflow: hidden;  /* Prevent scrollbars in iframe */
        }}
        
        #plotly-div {{
            width: 100%;
            height: 100vh;  /* Full viewport height */
            margin: 0;
            padding: 0;
        }}
        
        /* Ensure Plotly toolbar is accessible but minimal */
        .modebar {{
            opacity: 0.3;
            transition: opacity 0.3s ease;
        }}
        
        .modebar:hover {{
            opacity: 1;
        }}
        
        /* Custom scrollbar for any overflow */
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
        // Get the figure data from Python
        var figureJSON = {fig.to_json()};
        
        // Configuration optimized for iframe
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
        
        // Create the plot
        Plotly.newPlot('plotly-div', figureJSON.data, figureJSON.layout, config);
        
        // Handle window resize for iframe
        window.addEventListener('resize', function() {{
            Plotly.Plots.resize('plotly-div');
        }});
        
        // Initial resize to fit container
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
    
    # Create iframe-optimized HTML
    create_iframe_optimized_html(fig, html_path, title)
    print(f"✓ Saved iframe-optimized HTML: {html_path}")
    
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
    print("🛣️  Creating Route Choice Factor Visualizations (Iframe Optimized)")
    print("=" * 65)
    
    # Load data
    df = load_processed_data()
    
    # Prepare route choice data
    factor_stats, route_data = prepare_route_choice_data(df)
    
    # Create spider chart with iframe optimization
    spider_fig = create_spider_chart(factor_stats)
    export_figure(spider_fig, 'route_choice_spider', 'Route Choice Spider Chart')
    
    # Create comparison bar chart
    comparison_fig = create_factor_comparison_chart(factor_stats)
    export_figure(comparison_fig, 'route_choice_comparison', 'Route Choice Comparison')
    
    print("\n🎯 Route choice analysis completed!")
    print("📱 HTML files are now optimized for iframe embedding")
    print("🖼️  PNG files exported at 1920x1080 resolution")
    print("✨ Features:")
    print("   • Transparent background for seamless integration")
    print("   • Responsive sizing that fills iframe container")
    print("   • Optimized margins and font sizes for tight spaces")
    print("   • Minimal toolbar that appears on hover")
    print("   • No scrollbars or overflow issues")
    print("   • Spider chart optimized for radar visualization")
    
    return spider_fig, comparison_fig

if __name__ == "__main__":
    # Create outputs directory
    os.makedirs('outputs', exist_ok=True)
    
    main()