#!/usr/bin/env python3
"""
BGU Mobility Survey - Data Exporter for Modern Web Visualization
Exports clean JSON data for use with modern JavaScript mapping libraries.
"""

import json
import numpy as np
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any
import os
import logging

from .data_manager import data_manager, Coordinate, BGUGateData
from .route_simulator import route_generator

logger = logging.getLogger(__name__)


class BGUDataExporter:
    """Export BGU mobility survey data for modern web visualization"""

    def __init__(self, output_dir: str = "outputs"):
        self.output_dir = output_dir
        self.data_manager = data_manager

    def extract_routes(self) -> List[Dict]:
        """Extract route data with simplified structure"""
        df = self.data_manager.load_processed_data()

        if df.empty:
            return []

        routes = []

        # BGU Gates (from your original code)
        bgu_gates = {
            "uni_south_3": {"lat": 31.261222, "lng": 34.801138, "name": "South Gate"},
            "uni_north_3": {"lat": 31.263911, "lng": 34.799290, "name": "North Gate"},
            "uni_west": {"lat": 31.262500, "lng": 34.805528, "name": "West Gate"},
        }

        for idx, row in df.iterrows():
            # Parse residence
            if pd.isna(row["Residence-Info"]):
                continue

            residences = self.data_manager.parse_coordinates(row["Residence-Info"])
            if not residences:
                continue

            residence = residences[0]  # Use first residence

            # Parse POIs
            pois = []
            if pd.notna(row["POI"]):
                pois = self.data_manager.parse_coordinates(row["POI"])

            # Find closest gate (simplified distance calculation)
            closest_gate = None
            min_distance = float("inf")

            for gate_id, gate_data in bgu_gates.items():
                # Simple distance calculation
                dist = (
                    (residence["lat"] - gate_data["lat"]) ** 2
                    + (residence["lng"] - gate_data["lng"]) ** 2
                ) ** 0.5
                if dist < min_distance:
                    min_distance = dist
                    closest_gate = {
                        "id": gate_id,
                        "lat": gate_data["lat"],
                        "lng": gate_data["lng"],
                        "name": gate_data["name"],
                    }

            # Transportation mode translation
            transport_mode = row.get("Transportation-Mode", "")
            # Handle NaN values
            if pd.isna(transport_mode) or transport_mode == "":
                english_mode = "unknown"
            else:
                english_mode = self.data_manager.TRANSPORT_MODE_MAPPING.get(
                    transport_mode, "unknown"
                )

            # Use route generator for proper road-following routes
            route_path = route_generator.generate_route_path(
                residence, closest_gate, pois, transport_mode
            )

            # Skip routes where route generation couldn't create a path
            if route_path is None:
                continue

            route_data = {
                "id": row["Submission ID"],
                "residence": residence,
                "destination": closest_gate,
                "pois": pois,
                "routePath": route_path,
                "transportMode": english_mode,
                "originalMode": (
                    str(transport_mode) if not pd.isna(transport_mode) else "unknown"
                ),
                "poiCount": len(pois),
                "distance": min_distance * 111.32,  # Rough conversion to km
            }

            routes.append(route_data)

        logger.info(f"✓ Extracted {len(routes)} routes")
        return routes

    def calculate_statistics(self, pois: List[Dict], routes: List[Dict]) -> Dict:
        """Calculate summary statistics"""
        stats = {
            "totalPois": len(pois),
            "totalRoutes": len(routes),
            "poisWithComments": sum(1 for poi in pois if poi["hasComment"]),
            "commentPercentage": round(
                (
                    (sum(1 for poi in pois if poi["hasComment"]) / len(pois) * 100)
                    if pois
                    else 0
                ),
                1,
            ),
            "averageDistance": round(
                np.mean([route["distance"] for route in routes]) if routes else 0, 1
            ),
            "transportModes": {},
            "gateUsage": {},
        }

        # Transport mode distribution
        for route in routes:
            mode = route["transportMode"]
            stats["transportModes"][mode] = stats["transportModes"].get(mode, 0) + 1

        # Gate usage
        for route in routes:
            gate_name = route["destination"]["name"]
            stats["gateUsage"][gate_name] = stats["gateUsage"].get(gate_name, 0) + 1

        # Calculate bounds for map centering
        if pois:
            lats = [poi["lat"] for poi in pois]
            lngs = [poi["lng"] for poi in pois]
            stats["bounds"] = {
                "north": max(lats),
                "south": min(lats),
                "east": max(lngs),
                "west": min(lngs),
                "center": {"lat": sum(lats) / len(lats), "lng": sum(lngs) / len(lngs)},
            }
        else:
            # Default to BGU area
            stats["bounds"] = {"center": {"lat": 31.2627, "lng": 34.7983}}

        return stats

    def export_data(self) -> Dict[str, Any]:
        """Export all data as JSON files"""
        os.makedirs(self.output_dir, exist_ok=True)

        # Load and process data using data manager
        pois = self.data_manager.get_poi_data()
        routes = self.extract_routes()
        stats = self.calculate_statistics(pois, routes)

        # Create complete dataset
        export_data = {
            "metadata": {
                "exportedAt": datetime.now().isoformat(),
                "source": "BGU Mobility Survey",
                "version": "2.0",
            },
            "statistics": stats,
            "pois": pois,
            "routes": routes,
        }

        # Save individual files
        files_saved = []

        # Complete dataset
        complete_path = os.path.join(self.output_dir, "bgu_mobility_data.json")
        with open(complete_path, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)
        files_saved.append(complete_path)

        # Individual components for smaller file sizes
        poi_path = os.path.join(self.output_dir, "pois.json")
        with open(poi_path, "w", encoding="utf-8") as f:
            json.dump(pois, f, indent=2, ensure_ascii=False, default=str)
        files_saved.append(poi_path)

        route_path = os.path.join(self.output_dir, "routes.json")
        with open(route_path, "w", encoding="utf-8") as f:
            json.dump(routes, f, indent=2, ensure_ascii=False, default=str)
        files_saved.append(route_path)

        stats_path = os.path.join(self.output_dir, "statistics.json")
        with open(stats_path, "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=2, ensure_ascii=False, default=str)
        files_saved.append(stats_path)

        logger.info(f"✓ Exported data files:")
        for file_path in files_saved:
            file_size = os.path.getsize(file_path) / 1024  # KB
            logger.info(f"   📄 {file_path} ({file_size:.1f} KB)")

        return export_data


def main():
    """Main export function"""
    print("🗺️  BGU Mobility Data Exporter")
    print("=" * 40)

    exporter = BGUDataExporter()
    data = exporter.export_data()

    # Print summary
    stats = data["statistics"]
    print(f"\n📊 Export Summary:")
    print(
        f"   📍 POIs: {stats['totalPois']} ({stats['poisWithComments']} with comments)"
    )
    print(f"   🛣️  Routes: {stats['totalRoutes']}")
    print(f"   📏 Avg Distance: {stats['averageDistance']:.2f} km")

    print(f"\n🚇 Transportation Modes:")
    for mode, count in sorted(
        stats["transportModes"].items(), key=lambda x: x[1], reverse=True
    ):
        percentage = (
            (count / stats["totalRoutes"]) * 100 if stats["totalRoutes"] > 0 else 0
        )
        print(f"   • {mode.title()}: {count} ({percentage:.1f}%)")

    print(f"\n🏛️  Gate Usage:")
    for gate, count in sorted(
        stats["gateUsage"].items(), key=lambda x: x[1], reverse=True
    ):
        percentage = (
            (count / stats["totalRoutes"]) * 100 if stats["totalRoutes"] > 0 else 0
        )
        print(f"   • {gate}: {count} ({percentage:.1f}%)")

    print(f"\n🎯 Data ready for modern web visualization!")
    print("   Next: Use the exported JSON with the JavaScript interface")


if __name__ == "__main__":
    main()
