#!/usr/bin/env python3
"""
BGU Mobility Survey - Points of Interest Mapping
Creates interactive maps showing POI locations with comments using folium with enhanced widgets.
"""

import pandas as pd
import json
import folium
from folium import plugins
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

def parse_coordinates(coord_string: str) -> list:
    """Parse coordinate strings from JSON format."""
    if pd.isna(coord_string) or coord_string == '':
        return []
    
    try:
        # Parse JSON array of coordinate objects
        coord_data = json.loads(coord_string)
        coordinates = []
        
        for item in coord_data:
            if 'coordinate' in item:
                coord_str = item['coordinate']
                comment = item.get('comment', '')
                # Split lat,lng
                lat, lng = map(float, coord_str.split(','))
                coordinates.append({
                    'lat': lat,
                    'lng': lng,
                    'comment': comment.strip() if comment else ''
                })
                
        return coordinates
    except (json.JSONDecodeError, ValueError, KeyError) as e:
        print(f"⚠️  Error parsing coordinates: {coord_string[:50]}... - {e}")
        return []

def extract_all_pois(df: pd.DataFrame) -> pd.DataFrame:
    """Extract all POI points from the dataset."""
    
    poi_data = df[df['POI'].notna()]['POI'].copy()
    print(f"📍 Processing POI data from {len(poi_data)} responses...")
    
    all_pois = []
    response_counter = 0
    
    for submission_id, poi_string in zip(df[df['POI'].notna()]['Submission ID'], poi_data):
        coordinates = parse_coordinates(poi_string)
        response_counter += 1
        
        for coord in coordinates:
            all_pois.append({
                'submission_id': submission_id,
                'response_number': response_counter,
                'lat': coord['lat'],
                'lng': coord['lng'],
                'comment': coord['comment'] if coord['comment'] else 'No comment',
                'has_comment': len(coord['comment']) > 0
            })
    
    poi_df = pd.DataFrame(all_pois)
    
    print(f"✓ Extracted {len(poi_df)} POI points from {response_counter} responses")
    print(f"  Points with comments: {poi_df['has_comment'].sum()}")
    print(f"  Points without comments: {(~poi_df['has_comment']).sum()}")
    
    # Basic coordinate validation
    valid_coords = (poi_df['lat'] != 0) & (poi_df['lng'] != 0)
    print(f"  Valid coordinates: {valid_coords.sum()}")
    
    return poi_df[valid_coords].copy()

def create_folium_map(poi_df: pd.DataFrame) -> folium.Map:
    """Create an interactive Folium map with POI points and enhanced widgets."""
    
    # Calculate map center (around BGU area)
    center_lat = poi_df['lat'].median() if len(poi_df) > 0 else 31.2627
    center_lng = poi_df['lng'].median() if len(poi_df) > 0 else 34.7983
    
    # Create base map
    m = folium.Map(
        location=[center_lat, center_lng],
        zoom_start=13,
        tiles='OpenStreetMap',
        width='100%',
        height='100%'
    )
    
    # Add marker clusters for better performance
    marker_cluster = plugins.MarkerCluster(
        name='POI Clusters',
        overlay=True,
        control=True,
        options={
            'disableClusteringAtZoom': 16,  # Show individual markers at zoom 16+
            'maxClusterRadius': 50,
            'chunkedLoading': True
        }
    )
    
    # Add all POI markers to cluster (no visual differentiation)
    for _, poi in poi_df.iterrows():
        
        # Simple popup content
        popup_text = f"""
        <div style="font-family: Arial, sans-serif; max-width: 250px; font-size: 14px;">
            <h4 style="color: #333; margin: 0 0 10px 0;">BGU Student POI</h4>
            <p style="margin: 5px 0;"><strong>Comment:</strong></p>
            <p style="margin: 5px 0; font-style: italic; color: #666;">
                {poi['comment']}
            </p>
        </div>
        """
        
        # Simple tooltip
        tooltip_text = poi['comment']
        
        folium.Marker(
            location=[poi['lat'], poi['lng']],
            popup=folium.Popup(popup_text, max_width=280),
            tooltip=tooltip_text,
            icon=folium.Icon(
                color='blue',
                icon='map-pin',
                prefix='fa'
            )
        ).add_to(marker_cluster)
    
    # Add the cluster to the map
    marker_cluster.add_to(m)
    
    # Add scale bar
    plugins.MeasureControl(
        position='bottomleft',
        primary_length_unit='meters',
        secondary_length_unit='kilometers',
        primary_area_unit='sqmeters',
        secondary_area_unit='hectares'
    ).add_to(m)
    
    # Add north arrow using a simple HTML overlay
    north_arrow_html = '''
    <div style="position: fixed; 
                bottom: 80px; right: 20px; width: 50px; height: 50px; 
                background-color: rgba(255, 255, 255, 0.9); 
                border: 2px solid #ccc; 
                border-radius: 50%;
                z-index: 9999; 
                display: flex;
                align-items: center;
                justify-content: center;
                box-shadow: 0 2px 10px rgba(0,0,0,0.2);">
        <div style="font-size: 24px; color: #d63031; transform: rotate(0deg);">
            ↑
        </div>
        <div style="position: absolute; bottom: -20px; left: 50%; transform: translateX(-50%); 
                    font-size: 10px; color: #333; font-weight: bold;">N</div>
    </div>
    '''
    m.get_root().html.add_child(folium.Element(north_arrow_html))
    
    return m

def export_folium_map(folium_map: folium.Map, filename_base: str, poi_count: int) -> None:
    """Export Folium map as HTML with title and full-screen responsive design."""
    html_path = f'outputs/{filename_base}.html'
    
    # Save the map
    folium_map.save(html_path)
    
    # Read the saved HTML and add title
    with open(html_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # Add title and custom CSS
    title_and_css = '''
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
        
        body { 
            margin: 0; 
            padding: 0; 
            overflow: hidden; 
            font-family: 'Inter', Arial, sans-serif;
        }
        #map { 
            height: 100vh !important; 
            width: 100vw !important; 
        }
        .folium-map { 
            height: 100vh !important; 
            width: 100vw !important; 
        }
        
        .map-title {
            position: fixed;
            top: 20px;
            left: 20px;
            z-index: 9999;
            background: rgba(255, 255, 255, 0.95);
            padding: 15px 20px;
            border-radius: 8px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
            border: 2px solid #e9ecef;
        }
        
        .map-title h1 {
            margin: 0;
            font-size: 24px;
            font-weight: 700;
            color: #2c3e50;
        }
        
        .map-title p {
            margin: 5px 0 0 0;
            font-size: 14px;
            color: #7f8c8d;
        }
    </style>
    
    <div class="map-title">
        <h1>BGU Student Submitted POIs</h1>
        <p>''' + str(poi_count) + ''' Points of Interest</p>
    </div>
    '''
    
    # Insert the title and CSS after the opening body tag
    html_content = html_content.replace('<body>', '<body>' + title_and_css)
    
    # Write the modified HTML back
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"✓ Saved enhanced map with title and widgets: {html_path}")

def main():
    """Main function to create enhanced POI visualization."""
    print("🗺️  Creating BGU Student POI Map")
    print("=" * 50)
    
    # Load data
    df = load_processed_data()
    
    # Extract POI data
    poi_df = extract_all_pois(df)
    
    if len(poi_df) == 0:
        print("⚠️  No valid POI data found!")
        return None
    
    # Create enhanced Folium map
    poi_map = create_folium_map(poi_df)
    export_folium_map(poi_map, 'bgu_poi_map', len(poi_df))
    
    print("\n🎯 Enhanced POI mapping completed!")
    print("✨ Features:")
    print("   • BGU Student Submitted POIs title")
    print("   • Scale bar for distance reference")
    print("   • North arrow compass")
    print("   • Smart clustering that shows details at high zoom")
    print("   • Uniform POI styling")
    print("   • Simple hover tooltips")
    
    # Save processed POI data
    poi_df.to_csv('outputs/processed_poi_data.csv', index=False)
    print("💾 Saved processed POI data: outputs/processed_poi_data.csv")
    
    return poi_map

if __name__ == "__main__":
    # Create outputs directory
    os.makedirs('outputs', exist_ok=True)
    
    main()