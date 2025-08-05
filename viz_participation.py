#!/usr/bin/env python3
"""
BGU Mobility Survey - Future Participation Analysis
Creates bar chart showing willingness to participate in future studies from completed surveys only.
"""

import pandas as pd
import plotly.graph_objects as go
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
        # Need to recreate merged columns
        df['Further_Study_Interest'] = 'No Response'
        df.loc[df['Further-yes'].notna(), 'Further_Study_Interest'] = 'Yes'
        df.loc[df['Further-no'].notna(), 'Further_Study_Interest'] = 'No'
        
        df['Week_Tracking_Interest'] = 'No Response'
        df.loc[df['FurtherWeek-yes'].notna(), 'Week_Tracking_Interest'] = 'Yes'
        df.loc[df['FurtherWeek-no'].notna(), 'Week_Tracking_Interest'] = 'No'
        df.loc[df['FurtherWeek-other'].notna(), 'Week_Tracking_Interest'] = 'Other'
        
        return df

def prepare_participation_data(df: pd.DataFrame) -> pd.DataFrame:
    """Prepare participation data for completed surveys only."""
    
    # Filter only completed surveys
    completed_df = df[df['Submission Completed'] == True].copy()
    
    if len(completed_df) == 0:
        print("⚠️  No completed surveys found!")
        return None
    
    print(f"📊 Analyzing {len(completed_df)} completed surveys")
    
    # Get counts for further study interest
    study_counts = completed_df['Further_Study_Interest'].value_counts()
    print(f"\n📊 Further Study Participation (Completed Surveys):")
    for response, count in study_counts.items():
        percentage = (count / len(completed_df) * 100)
        print(f"  {response}: {count} ({percentage:.1f}%)")
    
    # Get counts for week tracking interest
    tracking_counts = completed_df['Week_Tracking_Interest'].value_counts()
    print(f"\n📊 Week Tracking Participation (Completed Surveys):")
    for response, count in tracking_counts.items():
        percentage = (count / len(completed_df) * 100)
        print(f"  {response}: {count} ({percentage:.1f}%)")
    
    return completed_df

def create_participation_comparison(completed_df: pd.DataFrame) -> go.Figure:
    """Create a comparison chart showing participation by study type."""
    
    # Create crosstabs
    study_crosstab = completed_df['Further_Study_Interest'].value_counts()
    tracking_crosstab = completed_df['Week_Tracking_Interest'].value_counts()
    
    # Create grouped bar chart with modern styling
    fig = go.Figure()
    
    categories = ['Future Study', 'Week Tracking']
    
    # Get yes/no counts for each
    study_yes = study_crosstab.get('Yes', 0)
    study_no = study_crosstab.get('No', 0)
    tracking_yes = tracking_crosstab.get('Yes', 0) 
    tracking_no = tracking_crosstab.get('No', 0)
    
    fig.add_trace(go.Bar(
        name='Yes',
        x=categories,
        y=[study_yes, tracking_yes],
        marker=dict(
            color='#00d4ff',
            line=dict(color='rgba(255,255,255,0.15)', width=1),
            opacity=0.9
        ),
        hovertemplate='<b>%{x}</b><br>Yes: %{y}<extra></extra>'
    ))
    
    fig.add_trace(go.Bar(
        name='No',
        x=categories,
        y=[study_no, tracking_no],
        marker=dict(
            color='#ff6b6b',
            line=dict(color='rgba(255,255,255,0.15)', width=1),
            opacity=0.9
        ),
        hovertemplate='<b>%{x}</b><br>No: %{y}<extra></extra>'
    ))
    
    fig.update_layout(
        title={
            'text': 'Future Research Participation Interest',
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 32, 'color': 'white', 'family': 'Inter, system-ui, sans-serif'}
        },
        barmode='group',
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font={'color': 'white', 'size': 14, 'family': 'Inter, system-ui, sans-serif'},
        xaxis=dict(
            tickfont={'size': 16, 'color': 'rgba(255,255,255,0.9)'},
            color='white',
            showgrid=False,
            zeroline=False,
            showline=False
        ),
        yaxis=dict(
            tickfont={'size': 14, 'color': 'rgba(255,255,255,0.8)'},
            gridcolor='rgba(255,255,255,0.08)',
            color='white',
            showgrid=True,
            gridwidth=0.5,
            zeroline=False,
            showline=False
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
            bgcolor='rgba(255,255,255,0.1)',
            bordercolor='rgba(255,255,255,0.3)',
            borderwidth=2,
            font={'size': 22, 'family': 'Inter, system-ui, sans-serif'}
        ),
        margin=dict(l=80, r=80, t=110, b=80),
        autosize=True,
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
    """Main function to create participation visualization."""
    print("📊 Creating Future Participation Analysis")
    print("=" * 50)
    
    # Load data
    df = load_processed_data()
    
    # Prepare participation data (completed surveys only)
    completed_df = prepare_participation_data(df)
    
    if completed_df is None:
        return None
    
    # Create participation comparison chart
    comparison_fig = create_participation_comparison(completed_df)
    export_figure(comparison_fig, 'participation_analysis')
    
    print("\n🎯 Participation analysis completed!")
    print("📊 Analysis focused on completed surveys only")
    print("📱 HTML file is now responsive and will fill the browser window")
    print("🖼️  PNG file exported at 1920x1080 resolution")
    
    return comparison_fig

if __name__ == "__main__":
    # Create outputs directory
    os.makedirs('outputs', exist_ok=True)
    
    main()