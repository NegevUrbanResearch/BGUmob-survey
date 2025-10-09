"""
Generate a minimal, self-contained HTML map for embedding
Contains only the map, gates, routes, and POIs - no UI elements
"""

import json
import folium
from folium import plugins
import pandas as pd


def load_data():
    """Load all required data files"""
    with open("outputs/pois.json", "r", encoding="utf-8") as f:
        pois = json.load(f)

    with open("outputs/routes.json", "r", encoding="utf-8") as f:
        routes = json.load(f)

    with open("outputs/university_polygon.json", "r", encoding="utf-8") as f:
        university_polygon = json.load(f)

    return pois, routes, university_polygon


def create_embed_map():
    """Create a minimal, self-contained map for embedding"""

    print("Loading data...")
    pois, routes, university_polygon = load_data()

    # Gate definitions
    gates = [
        {
            "lng": 34.801138,
            "lat": 31.261222,
            "name": "South Gate",
            "color": "#22a7f0",
            "id": "south",
        },
        {
            "lng": 34.79929,
            "lat": 31.263911,
            "name": "North Gate",
            "color": "#9c5dc7",
            "id": "north",
        },
        {
            "lng": 34.805528,
            "lat": 31.2625,
            "name": "West Gate",
            "color": "#e14b31",
            "id": "west",
        },
    ]

    # Gate color mapping
    gate_colors = {
        "South Gate": "#22a7f0",
        "North Gate": "#9c5dc7",
        "West Gate": "#e14b31",
        "south": "#22a7f0",
        "north": "#9c5dc7",
        "west": "#e14b31",
    }

    print("Creating map...")
    # Create base map centered on BGU
    m = folium.Map(
        location=[31.2627, 34.7983],
        zoom_start=14,
        tiles="CartoDB dark_matter",
        control_scale=True,
        zoom_control=True,
        prefer_canvas=True,
    )

    # Add university polygon
    print("Adding university polygon...")
    if university_polygon and "coordinates" in university_polygon:
        coords = university_polygon["coordinates"][0]
        # Convert [lng, lat] to [lat, lng] for folium
        polygon_coords = [[lat, lng] for lng, lat in coords]

        folium.Polygon(
            locations=polygon_coords,
            color="#64ffda",
            fill=True,
            fillColor="#64ffda",
            fillOpacity=0.15,
            weight=2,
            opacity=0.6,
            tooltip="Ben-Gurion University Campus",
        ).add_to(m)

    # Add routes
    print(f"Adding {len(routes)} routes...")

    for route in routes:
        if "routePath" not in route or not route["routePath"]:
            continue

        # Get route color based on destination gate
        destination_name = route.get("destination", {}).get("name", "Unknown")
        route_color = gate_colors.get(destination_name, "#888888")

        # Convert [lng, lat] to [lat, lng] for folium
        path_coords = [[lat, lng] for lng, lat in route["routePath"]]

        # Get transport mode for popup
        transport_mode = route.get("transportMode", "unknown")

        folium.PolyLine(
            locations=path_coords,
            color=route_color,
            weight=3,
            opacity=0.6,
            tooltip=f"{destination_name}<br>Mode: {transport_mode}",
        ).add_to(m)

    # Add POIs
    print(f"Adding {len(pois)} POIs...")

    for poi in pois:
        if "lat" not in poi or "lng" not in poi:
            continue

        comment = poi.get("comment", "No comment")
        has_comment = poi.get("hasComment", False)

        # Use different colors for POIs with/without comments
        poi_color = "#4CAF50" if has_comment else "#81C784"

        # Create tooltip with comment
        tooltip_text = f"<b>POI</b><br>{comment}" if has_comment else "<b>POI</b>"

        folium.CircleMarker(
            location=[poi["lat"], poi["lng"]],
            radius=6,
            color="#1B5E20",
            fillColor=poi_color,
            fillOpacity=0.8,
            weight=2,
            tooltip=tooltip_text,
        ).add_to(m)

    # Add gates
    print("Adding gates...")

    for gate in gates:
        # Count routes to this gate
        gate_route_count = sum(
            1
            for route in routes
            if route.get("destination", {}).get("name") == gate["name"]
        )

        folium.CircleMarker(
            location=[gate["lat"], gate["lng"]],
            radius=12,
            color=gate["color"],
            fillColor="white",
            fillOpacity=0.9,
            weight=4,
            tooltip=f"<b>{gate['name']}</b><br>{gate_route_count} routes",
        ).add_to(m)

    # Add elegant legend with dark theme
    legend_html = """
    <div style="
        position: fixed;
        bottom: 40px;
        right: 15px;
        background: linear-gradient(135deg, rgba(15, 18, 20, 0.95), rgba(20, 22, 24, 0.92));
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.2);
        border-radius: 10px;
        padding: 14px 16px;
        font-size: 13px;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
        z-index: 9999;
        color: rgba(255, 255, 255, 0.95);
    ">
        <div style="font-weight: 600; margin-bottom: 10px; font-size: 14px; color: #ffffff;">Legend</div>
        
        <!-- Routes Section -->
        <div style="margin-bottom: 8px; padding-bottom: 8px; border-bottom: 1px solid rgba(255, 255, 255, 0.1);">
            <div style="margin-bottom: 6px; display: flex; align-items: center;">
                <span style="display: inline-block; width: 28px; height: 3px; background-color: #22a7f0; margin-right: 8px; border-radius: 2px;"></span>
                <span style="font-size: 12px;">South Gate Routes</span>
            </div>
            <div style="margin-bottom: 6px; display: flex; align-items: center;">
                <span style="display: inline-block; width: 28px; height: 3px; background-color: #9c5dc7; margin-right: 8px; border-radius: 2px;"></span>
                <span style="font-size: 12px;">North Gate Routes</span>
            </div>
            <div style="margin-bottom: 0; display: flex; align-items: center;">
                <span style="display: inline-block; width: 28px; height: 3px; background-color: #e14b31; margin-right: 8px; border-radius: 2px;"></span>
                <span style="font-size: 12px;">West Gate Routes</span>
            </div>
        </div>
        
        <!-- Gates Section -->
        <div style="margin-bottom: 8px; padding-bottom: 8px; border-bottom: 1px solid rgba(255, 255, 255, 0.1);">
            <div style="margin-bottom: 6px; display: flex; align-items: center;">
                <svg width="16" height="16" style="margin-right: 8px;">
                    <circle cx="8" cy="8" r="7" fill="white" stroke="#22a7f0" stroke-width="2.5"/>
                </svg>
                <span style="font-size: 12px;">South Gate</span>
            </div>
            <div style="margin-bottom: 6px; display: flex; align-items: center;">
                <svg width="16" height="16" style="margin-right: 8px;">
                    <circle cx="8" cy="8" r="7" fill="white" stroke="#9c5dc7" stroke-width="2.5"/>
                </svg>
                <span style="font-size: 12px;">North Gate</span>
            </div>
            <div style="margin-bottom: 0; display: flex; align-items: center;">
                <svg width="16" height="16" style="margin-right: 8px;">
                    <circle cx="8" cy="8" r="7" fill="white" stroke="#e14b31" stroke-width="2.5"/>
                </svg>
                <span style="font-size: 12px;">West Gate</span>
            </div>
        </div>
        
        <!-- POI Section -->
        <div style="display: flex; align-items: center;">
            <svg width="16" height="16" style="margin-right: 8px;">
                <circle cx="8" cy="8" r="5" fill="#4CAF50" stroke="#1B5E20" stroke-width="1.5"/>
            </svg>
            <span style="font-size: 12px;">Points of Interest</span>
        </div>
    </div>
    """

    m.get_root().html.add_child(folium.Element(legend_html))

    return m


def main():
    """Generate the embeddable map HTML"""
    print("=" * 60)
    print("BGU Mobility - Embeddable Map Generator")
    print("=" * 60)

    # Create the map
    m = create_embed_map()

    # Save to file
    output_file = "outputs/embed_map.html"
    print(f"\nSaving to {output_file}...")
    m.save(output_file)

    print(f"✓ Embeddable map saved to {output_file}")
    print("\nThis HTML file is self-contained and can be embedded in any website.")
    print("You can use it with an <iframe> tag:")
    print(f'  <iframe src="{output_file}" width="100%" height="600px"></iframe>')
    print("=" * 60)


if __name__ == "__main__":
    main()
