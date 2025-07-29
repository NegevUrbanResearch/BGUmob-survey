#!/usr/bin/env python3
"""
BGU Mobility Survey - Transportation Mode Analysis
Creates sleek, modern interactive bar charts with minimal clutter.
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
    """Create a sleek, modern interactive bar chart for transportation modes."""
    
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
            # Add subtle gradient effect
            opacity=0.9
        ),
        hovertemplate='<b>%{x}</b><br>Responses: %{y}<br>Percentage: %{customdata}%<extra></extra>',
        customdata=transport_counts['Percentage'],
        name='Transportation Mode'
    ))
    
    # Clean, modern layout with fixed y-axis range
    fig.update_layout(
        title={
            'text': 'Transportation to BGU University',
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 48, 'color': 'white', 'family': 'Inter, system-ui, sans-serif'},
            'pad': {'b': 20}
        },
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='#0a0a0a',  # Slightly deeper black
        font={'color': 'white', 'size': 24, 'family': 'Inter, system-ui, sans-serif'},
        xaxis=dict(
            tickfont={'size': 24, 'color': 'rgba(255,255,255,0.9)'},
            showgrid=False,
            zeroline=False,
            showline=False,
            tickangle=0
        ),
        yaxis=dict(
            tickfont={'size': 24, 'color': 'rgba(255,255,255,0.8)'},
            showgrid=True,
            gridwidth=0.5,
            gridcolor='rgba(255,255,255,0.08)',
            zeroline=False,
            showline=False,
            range=[0, 100],  # Fixed range to 100
            dtick=20  # Show ticks every 20 units
        ),
        margin=dict(l=90, r=90, t=130, b=90),
        autosize=True,
        showlegend=False,
        hoverlabel=dict(
            bgcolor='rgba(15,15,15,0.95)',
            bordercolor='rgba(255,255,255,0.3)',
            font_size=24,
            font_family='Inter, system-ui, sans-serif'
        )
    )
    
    # Add subtle animation on load
    fig.update_traces(
        marker_line_width=1,
        selector=dict(type="bar")
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
    """Main function to create transportation visualizations."""
    print("🚗 Creating Transportation Mode Visualization")
    print("=" * 50)
    
    # Load data
    df = load_processed_data()
    
    # Prepare transportation data
    transport_counts = prepare_transportation_data(df)
    
    # Create main bar chart with responsive sizing
    fig = create_transportation_bar_chart(transport_counts)
    export_figure(fig, 'transportation_modes')
    
    print("\n🎯 Transportation analysis completed!")
    print("📱 HTML file is now responsive and will fill the browser window")
    print("🖼️  PNG file exported at 1920x1080 resolution")
    
    return fig

if __name__ == "__main__":
    # Create outputs directory
    os.makedirs('outputs', exist_ok=True)
    
    main()