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

def prepare_transportation_data(df: pd.DataFrame) -> pd.DataFrame:
    """Clean and prepare transportation mode data."""
    # Filter out empty transportation mode responses
    transport_data = df[df['Transportation-Mode'].notna()].copy()
    
    # Hebrew to English mapping for better presentation
    mode_mapping = {
        'ברגל': 'Walking',
        'אופניים': 'Bicycle', 
        'רכב': 'Car',
        'אופניים/קורקינט חשמלי': 'Electric Bike/Scooter',
        'אוטובוס': 'Bus',
        'רכבת': 'Train',
        'אחר': 'Other'
    }
    
    transport_data['Transport_English'] = transport_data['Transportation-Mode'].map(mode_mapping)
    transport_data['Transport_English'] = transport_data['Transport_English'].fillna(transport_data['Transportation-Mode'])
    
    # Get counts
    transport_counts = transport_data['Transport_English'].value_counts().reset_index()
    transport_counts.columns = ['Mode', 'Count']
    
    # Calculate percentages
    transport_counts['Percentage'] = (transport_counts['Count'] / transport_counts['Count'].sum() * 100).round(1)
    
    print(f"📊 Transportation Mode Distribution:")
    for _, row in transport_counts.iterrows():
        print(f"  {row['Mode']}: {row['Count']} ({row['Percentage']}%)")
    
    return transport_counts

def create_transportation_bar_chart(transport_counts: pd.DataFrame) -> go.Figure:
    """Create a sleek, modern interactive bar chart optimized for iframe embedding."""
    
    # Modern vibrant color palette with gradients
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
    
    # Add beautiful bars with subtle styling
    fig.add_trace(go.Bar(
        x=transport_counts['Mode'],
        y=transport_counts['Count'],
        marker=dict(
            color=colors[:len(transport_counts)],
            line=dict(color='rgba(255,255,255,0.15)', width=1),
            opacity=0.9
        ),
        hovertemplate='<b>%{x}</b><br>Responses: %{y}<br>Percentage: %{customdata}%<extra></extra>',
        customdata=transport_counts['Percentage'],
        name='Transportation Mode'
    ))
    
    # Optimized layout for iframe embedding
    fig.update_layout(
        title={
            'text': 'Transportation to BGU University',
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 28, 'color': 'white', 'family': 'Inter, system-ui, sans-serif'},
            'pad': {'b': 10}
        },
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',  # Transparent background for iframe
        font={'color': 'white', 'size': 14, 'family': 'Inter, system-ui, sans-serif'},
        xaxis=dict(
            tickfont={'size': 14, 'color': 'rgba(255,255,255,0.9)'},
            showgrid=False,
            zeroline=False,
            showline=False,
            tickangle=-15  # Slight angle for better fit
        ),
        yaxis=dict(
            tickfont={'size': 14, 'color': 'rgba(255,255,255,0.8)'},
            showgrid=True,
            gridwidth=0.5,
            gridcolor='rgba(255,255,255,0.08)',
            zeroline=False,
            showline=False,
            range=[0, max(transport_counts['Count']) * 1.1],  # Dynamic range with 10% padding
            dtick=max(1, max(transport_counts['Count']) // 5)  # Dynamic tick spacing
        ),
        # Optimized margins for iframe - minimal for maximum space usage
        margin=dict(l=50, r=20, t=60, b=40),
        autosize=True,
        showlegend=False,
        hoverlabel=dict(
            bgcolor='rgba(15,15,15,0.95)',
            bordercolor='rgba(255,255,255,0.3)',
            font_size=14,
            font_family='Inter, system-ui, sans-serif'
        )
    )
    
    return fig

def create_iframe_optimized_html(fig: go.Figure, filename: str) -> None:
    """Create HTML file specifically optimized for iframe embedding."""
    
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Transportation Modes Analysis</title>
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
                filename: 'transportation_modes',
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

def export_figure(fig: go.Figure, filename_base: str) -> None:
    """Export figure as both optimized HTML and PNG."""
    html_path = f'outputs/{filename_base}.html'
    png_path = f'outputs/{filename_base}.png'
    
    # Create iframe-optimized HTML
    create_iframe_optimized_html(fig, html_path)
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
    """Main function to create transportation visualizations."""
    print("🚗 Creating Transportation Mode Visualization (Iframe Optimized)")
    print("=" * 60)
    
    # Load data
    df = load_processed_data()
    
    # Prepare transportation data
    transport_counts = prepare_transportation_data(df)
    
    # Create iframe-optimized bar chart
    fig = create_transportation_bar_chart(transport_counts)
    export_figure(fig, 'transportation_modes')
    
    print("\n🎯 Transportation analysis completed!")
    print("📱 HTML file is now optimized for iframe embedding")
    print("🖼️  PNG file exported at 1920x1080 resolution")
    print("✨ Features:")
    print("   • Transparent background for seamless integration")
    print("   • Responsive sizing that fills iframe container")
    print("   • Optimized margins and font sizes")
    print("   • Minimal toolbar that appears on hover")
    print("   • No scrollbars or overflow issues")
    
    return fig

if __name__ == "__main__":
    # Create outputs directory
    os.makedirs('outputs', exist_ok=True)
    
    main()