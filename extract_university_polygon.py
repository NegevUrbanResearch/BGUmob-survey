#!/usr/bin/env python3
"""
Extract University Polygon from Shapefile
Converts the university polygon from shapefile to GeoJSON format for map visualization
"""

import geopandas as gpd
import json
import os


def extract_university_polygon():
    """Extract university polygon and save as GeoJSON"""

    # Path to the shapefile
    shapefile_path = "data/polygon-shp/Polygon Notes.shp"

    if not os.path.exists(shapefile_path):
        print(f"❌ Shapefile not found: {shapefile_path}")
        return False

    try:
        # Read the shapefile
        print("📖 Reading shapefile...")
        gdf = gpd.read_file(shapefile_path)

        # Display basic info about the shapefile
        print(f"✓ Loaded {len(gdf)} features")
        print(f"✓ Columns: {list(gdf.columns)}")
        print(f"✓ CRS: {gdf.crs}")

        # Display the data to understand structure
        print("\n📊 Shapefile data:")
        print(gdf.head())

        # Look for university polygon (name contains "UNI")
        if "Name" in gdf.columns:
            uni_rows = gdf[gdf["Name"].str.contains("UNI", case=False, na=False)]
        elif "name" in gdf.columns:
            uni_rows = gdf[gdf["name"].str.contains("UNI", case=False, na=False)]
        else:
            # If no Name column, check all string columns for UNI
            string_cols = gdf.select_dtypes(include=["object"]).columns
            uni_rows = gdf
            for col in string_cols:
                mask = gdf[col].astype(str).str.contains("UNI", case=False, na=False)
                if mask.any():
                    uni_rows = gdf[mask]
                    print(f"✓ Found UNI in column: {col}")
                    break

        if len(uni_rows) == 0:
            print("⚠️ No polygon with 'UNI' found. Showing all available data:")
            print(gdf)
            # Use the first polygon as fallback
            if len(gdf) > 0:
                uni_rows = gdf.iloc[[0]]
                print("📍 Using first polygon as university boundary")
            else:
                print("❌ No polygons found in shapefile")
                return False

        print(f"✓ Found {len(uni_rows)} university polygon(s)")

        # Convert to WGS84 if not already
        if gdf.crs != "EPSG:4326":
            print("🔄 Converting to WGS84...")
            uni_rows = uni_rows.to_crs("EPSG:4326")

        # Convert to GeoJSON format
        print("📝 Converting to GeoJSON...")

        # Drop problematic date columns and keep only essential fields
        essential_cols = ["Name", "Notes", "geometry"]
        available_cols = [col for col in essential_cols if col in uni_rows.columns]
        uni_clean = uni_rows[available_cols].copy()

        geojson_data = json.loads(uni_clean.to_json())

        # Create outputs directory if it doesn't exist
        os.makedirs("outputs", exist_ok=True)

        # Save the GeoJSON
        output_path = "outputs/university_polygon.json"
        with open(output_path, "w") as f:
            json.dump(geojson_data, f, indent=2)

        print(f"✅ University polygon saved to: {output_path}")

        # Display basic statistics
        if len(uni_rows) > 0:
            bounds = uni_rows.bounds
            print(f"📍 Polygon bounds:")
            print(f"   Min longitude: {bounds.minx.iloc[0]:.6f}")
            print(f"   Max longitude: {bounds.maxx.iloc[0]:.6f}")
            print(f"   Min latitude: {bounds.miny.iloc[0]:.6f}")
            print(f"   Max latitude: {bounds.maxy.iloc[0]:.6f}")

            # Calculate center
            centroid = uni_rows.geometry.centroid.iloc[0]
            print(f"   Center: {centroid.x:.6f}, {centroid.y:.6f}")

        return True

    except Exception as e:
        print(f"❌ Error processing shapefile: {e}")
        return False


if __name__ == "__main__":
    print("🗺️ BGU University Polygon Extractor")
    print("=" * 40)

    success = extract_university_polygon()

    if success:
        print("\n✅ University polygon extraction completed!")
        print("💡 You can now use 'outputs/university_polygon.json' in your map")
    else:
        print("\n❌ Extraction failed. Please check the shapefile.")
