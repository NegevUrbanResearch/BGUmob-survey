#!/usr/bin/env python3
"""
BGU Mobility Survey - Data Exporter for Modern Web Visualization
Exports clean JSON data for use with modern JavaScript mapping libraries.
"""

import pandas as pd
import json
import numpy as np
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
import os
import requests
import time
import logging
import polyline
from math import radians, cos, sin, asin, sqrt
from dataclasses import dataclass

@dataclass
class Coordinate:
    """Coordinate data class with validation"""
    lat: float
    lon: float
    comment: str = ""
    
    def __post_init__(self):
        """Validate coordinates are within Israel bounds"""
        assert 29.5 <= self.lat <= 33.3, f"Latitude {self.lat} out of Israel bounds"
        assert 34.2 <= self.lon <= 35.9, f"Longitude {self.lon} out of Israel bounds"
        
    def distance_to(self, other: 'Coordinate') -> float:
        """Calculate distance in kilometers using Haversine formula"""
        assert isinstance(other, Coordinate), "Distance calculation requires Coordinate object"
        
        lat1, lon1, lat2, lon2 = map(radians, [self.lat, self.lon, other.lat, other.lon])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        return 2 * asin(sqrt(a)) * 6371  # Earth radius in km

class BGUGateData:
    """BGU University gate/entrance data"""
    
    GATES = {
        'uni_south_3': Coordinate(31.261222, 34.801138, "South Gate 3"),
        'uni_north_3': Coordinate(31.263911, 34.799290, "North Gate 3"),
        'uni_west': Coordinate(31.262500, 34.805528, "West Gate")
    }
    
    @classmethod
    def find_closest_gate(cls, residence: Coordinate) -> Tuple[str, Coordinate]:
        """Find closest university gate to residence"""
        assert isinstance(residence, Coordinate), "Residence must be Coordinate object"
        
        closest_gate = None
        closest_distance = float('inf')
        closest_name = None
        
        for gate_name, gate_coord in cls.GATES.items():
            distance = residence.distance_to(gate_coord)
            if distance < closest_distance:
                closest_distance = distance
                closest_gate = gate_coord
                closest_name = gate_name
        
        assert closest_gate is not None, "No closest gate found"
        return closest_name, closest_gate

class OTPRouteSimulator:
    """Simulate routes using OpenTripPlanner server"""
    
    def __init__(self, base_url: str = "http://localhost:8080/otp/routers/default", 
                 max_retries: int = 5, retry_delay: float = 0.1):
        self.base_url = base_url
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
    def get_walking_route(self, origin: Coordinate, destination: Coordinate, 
                         intermediate_stop: Optional[Coordinate] = None, 
                         transportation_mode: str = "WALK") -> Optional[Dict]:
        """Get route from OTP server with retry logic and small location variations"""
        assert isinstance(origin, Coordinate), "Origin must be Coordinate"
        assert isinstance(destination, Coordinate), "Destination must be Coordinate"
        
        # Try multiple small variations of the origin location if initial attempts fail
        variations = self._generate_location_variations(origin, num_variations=3)
        
        for attempt, origin_variant in enumerate(variations):
            if intermediate_stop:
                # Route via intermediate stop: origin -> stop -> destination
                route1 = self._query_otp_route_with_mode(origin_variant, intermediate_stop, transportation_mode)
                if not route1:
                    continue
                    
                route2 = self._query_otp_route_with_mode(intermediate_stop, destination, transportation_mode)
                if not route2:
                    continue
                    
                result = self._combine_routes(route1, route2, intermediate_stop)
                if result:
                    return result
            else:
                # Direct route
                result = self._query_otp_route_with_mode(origin_variant, destination, transportation_mode)
                if result:
                    return result
                    
        return None
    
    def _generate_location_variations(self, coord: Coordinate, num_variations: int = 3) -> List[Coordinate]:
        """Generate small variations around a coordinate for retry attempts"""
        variations = [coord]  # Start with original
        
        # Add small random offsets (±20 meters approximately)
        for _ in range(num_variations - 1):
            offset_lat = np.random.uniform(-0.0002, 0.0002)  # ~±20m
            offset_lon = np.random.uniform(-0.0002, 0.0002)  # ~±20m
            
            new_lat = coord.lat + offset_lat
            new_lon = coord.lon + offset_lon
            
            # Validate bounds
            if 29.5 <= new_lat <= 33.3 and 34.2 <= new_lon <= 35.9:
                variations.append(Coordinate(new_lat, new_lon, coord.comment))
        
        return variations
    
    def _map_transportation_mode(self, hebrew_mode: str) -> str:
        """Map Hebrew transportation modes to OTP modes"""
        mode_mapping = {
            'ברגל': 'WALK',
            'אופניים': 'BICYCLE',
            'אופניים/קורקינט חשמלי': 'BICYCLE',
            'רכב': 'CAR',
            'אוטובוס': 'TRANSIT,WALK',
            'רכבת': 'TRANSIT,WALK',
            '': 'WALK'  # Default to walking
        }
        return mode_mapping.get(hebrew_mode, 'WALK')
    
    def _query_otp_route_with_mode(self, origin: Coordinate, destination: Coordinate, 
                                  transportation_mode: str) -> Optional[Dict]:
        """Query OTP server for route with specific transportation mode"""
        otp_mode = self._map_transportation_mode(transportation_mode)
        
        params = {
            'fromPlace': f"{origin.lat},{origin.lon}",
            'toPlace': f"{destination.lat},{destination.lon}",
            'mode': otp_mode,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'time': '09:00:00',
            'arriveBy': 'false',
            'walkSpeed': 1.4,  # m/s
            'maxWalkDistance': 10000,
            'locale': 'en'
        }
        
        # Add mode-specific parameters
        if 'BICYCLE' in otp_mode:
            params.update({
                'bikeSpeed': 4.0,  # m/s
                'bikeSwitchTime': 0,
                'bikeSwitchCost': 0
            })
        elif 'CAR' in otp_mode:
            params.update({
                'carSpeed': 40.0,  # km/h
                'maxCarDistance': 50000
            })
        
        return self._query_otp_route_base(params)
    
    def _query_otp_route_base(self, params: Dict) -> Optional[Dict]:
        """Base OTP query method"""
        
        for attempt in range(self.max_retries):
            try:
                response = requests.get(
                    f"{self.base_url}/plan",
                    params=params,
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if 'plan' in data and 'itineraries' in data['plan'] and data['plan']['itineraries']:
                        return data
                    else:
                        print(f"⚠️  OTP returned no itineraries for {params['fromPlace']} to {params['toPlace']}")
                        return None
                        
                elif response.status_code == 429:  # Rate limited
                    wait_time = (attempt + 1) * self.retry_delay
                    print(f"⚠️  Rate limited, waiting {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"⚠️  OTP request failed: {response.status_code}")
                    
            except requests.exceptions.RequestException as e:
                print(f"⚠️  OTP request error: {e}")
                
            if attempt < self.max_retries - 1:
                time.sleep((attempt + 1) * self.retry_delay)
        
        return None
    
    def _combine_routes(self, route1: Dict, route2: Dict, intermediate: Coordinate) -> Dict:
        """Combine two route segments via intermediate stop"""
        try:
            leg1 = route1['plan']['itineraries'][0]['legs'][0]
            leg2 = route2['plan']['itineraries'][0]['legs'][0]
            
            points1 = polyline.decode(leg1['legGeometry']['points'])
            points2 = polyline.decode(leg2['legGeometry']['points'])
            
            # Combine points, skip first point of second segment to avoid duplication
            combined_points = points1 + points2[1:]
            
            return {
                'plan': {
                    'itineraries': [{
                        'legs': [{
                            'legGeometry': {'points': combined_points},
                            'duration': leg1['duration'] + leg2['duration'],
                            'distance': leg1['distance'] + leg2['distance']
                        }]
                    }]
                },
                'intermediate_stop': {
                    'lat': intermediate.lat,
                    'lon': intermediate.lon,
                    'comment': intermediate.comment
                }
            }
        except (KeyError, IndexError) as e:
            print(f"⚠️  Error combining routes: {e}")
            return None

class BGUDataExporter:
    """Export BGU mobility survey data for modern web visualization"""
    
    def __init__(self, data_path: str = 'data/processed_mobility_data.csv'):
        self.data_path = data_path
        self.df = None
        
    def load_data(self) -> pd.DataFrame:
        """Load the processed survey data"""
        try:
            self.df = pd.read_csv(self.data_path)
            print(f"✓ Loaded data: {self.df.shape[0]} rows")
            return self.df
        except FileNotFoundError:
            print(f"⚠️  Data file not found: {self.data_path}")
            return pd.DataFrame()
    
    def parse_coordinates(self, coord_string: str) -> List[Dict]:
        """Parse coordinate strings from JSON format"""
        if pd.isna(coord_string) or coord_string == '':
            return []
        
        try:
            coord_data = json.loads(coord_string)
            coordinates = []
            
            for item in coord_data:
                if 'coordinate' in item:
                    coord_str = item['coordinate']
                    comment = item.get('comment', '').strip()
                    lat, lng = map(float, coord_str.split(','))
                    
                    # Validate coordinates are in Israel bounds
                    if 29.5 <= lat <= 33.3 and 34.2 <= lng <= 35.9:
                        coordinates.append({
                            'lat': lat,
                            'lng': lng,
                            'comment': comment if comment else 'No comment provided'
                        })
                        
            return coordinates
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            print(f"⚠️  Error parsing coordinates: {e}")
            return []
    
    def extract_pois(self) -> List[Dict]:
        """Extract all POI points with metadata"""
        if self.df is None:
            return []
        
        poi_data = self.df[self.df['POI'].notna()]['POI'].copy()
        submission_ids = self.df[self.df['POI'].notna()]['Submission ID'].copy()
        
        all_pois = []
        
        for submission_id, poi_string in zip(submission_ids, poi_data):
            coordinates = self.parse_coordinates(poi_string)
            
            for i, coord in enumerate(coordinates):
                all_pois.append({
                    'id': f"{submission_id}_{i}",
                    'submissionId': submission_id,
                    'lat': coord['lat'],
                    'lng': coord['lng'],
                    'comment': coord['comment'],
                    'hasComment': len(coord['comment']) > 0 and coord['comment'] != 'No comment provided'
                })
        
        print(f"✓ Extracted {len(all_pois)} POI points")
        return all_pois
    
    def extract_routes(self) -> List[Dict]:
        """Extract route data with simplified structure"""
        if self.df is None:
            return []
        
        routes = []
        
        # BGU Gates (from your original code)
        bgu_gates = {
            'uni_south_3': {'lat': 31.261222, 'lng': 34.801138, 'name': "South Gate"},
            'uni_north_3': {'lat': 31.263911, 'lng': 34.799290, 'name': "North Gate"},
            'uni_west': {'lat': 31.262500, 'lng': 34.805528, 'name': "West Gate"}
        }
        
        for idx, row in self.df.iterrows():
            # Parse residence
            if pd.isna(row['Residence-Info']):
                continue
                
            residences = self.parse_coordinates(row['Residence-Info'])
            if not residences:
                continue
            
            residence = residences[0]  # Use first residence
            
            # Parse POIs
            pois = []
            if pd.notna(row['POI']):
                pois = self.parse_coordinates(row['POI'])
            
            # Find closest gate (simplified distance calculation)
            closest_gate = None
            min_distance = float('inf')
            
            for gate_id, gate_data in bgu_gates.items():
                # Simple distance calculation
                dist = ((residence['lat'] - gate_data['lat'])**2 + 
                       (residence['lng'] - gate_data['lng'])**2)**0.5
                if dist < min_distance:
                    min_distance = dist
                    closest_gate = {
                        'id': gate_id,
                        'lat': gate_data['lat'],
                        'lng': gate_data['lng'],
                        'name': gate_data['name']
                    }
            
            # Transportation mode translation
            mode_translation = {
                'ברגל': 'walking',
                'אופניים': 'bicycle',
                'אופניים/קורקינט חשמלי': 'ebike',
                'רכב': 'car',
                'אוטובוס': 'bus',
                'רכבת': 'train'
            }
            
            transport_mode = row.get('Transportation-Mode', '')
            # Handle NaN values
            if pd.isna(transport_mode) or transport_mode == '':
                english_mode = 'unknown'
            else:
                english_mode = mode_translation.get(transport_mode, 'unknown')
            
            # Use OTP for proper road-following routes
            route_path = self.generate_otp_route_path(residence, closest_gate, pois, transport_mode)
            
            # Skip routes where OTP couldn't generate a path
            if route_path is None:
                continue
            
            route_data = {
                'id': row['Submission ID'],
                'residence': residence,
                'destination': closest_gate,
                'pois': pois,
                'routePath': route_path,
                'transportMode': english_mode,
                'originalMode': str(transport_mode) if not pd.isna(transport_mode) else 'unknown',
                'poiCount': len(pois),
                'distance': min_distance * 111.32  # Rough conversion to km
            }
            
            routes.append(route_data)
        
        print(f"✓ Extracted {len(routes)} routes")
        return routes
    
    def generate_otp_route_path(self, residence: Dict, destination: Dict, pois: List[Dict], transport_mode: str) -> List[List[float]]:
        """Generate route path using OTP server with multiple retry attempts"""
        # Initialize OTP simulator
        otp_simulator = OTPRouteSimulator()
        
        # Convert to Coordinate objects
        residence_coord = Coordinate(residence['lat'], residence['lng'], residence.get('comment', ''))
        destination_coord = Coordinate(destination['lat'], destination['lng'], destination.get('comment', ''))
        
        # Convert POIs to Coordinate objects
        poi_coords = [Coordinate(poi['lat'], poi['lng'], poi.get('comment', '')) for poi in pois]
        
        # Select intermediate stop (use first POI if available)
        intermediate_stop = poi_coords[0] if poi_coords else None
        
        # Try multiple location variations for both origin and destination
        origin_variations = self._generate_location_variations(residence_coord, num_variations=5)
        dest_variations = self._generate_location_variations(destination_coord, num_variations=3)
        
        # Try different combinations of origin and destination variations
        for origin_var in origin_variations:
            for dest_var in dest_variations:
                # Generate route with OTP
                route_data = otp_simulator.get_walking_route(
                    origin_var,
                    dest_var,
                    intermediate_stop,
                    transport_mode
                )
                
                if route_data:
                    try:
                        itinerary = route_data['plan']['itineraries'][0]
                        leg = itinerary['legs'][0]
                        
                        # Decode route points from polyline
                        if isinstance(leg['legGeometry']['points'], str):
                            route_points = polyline.decode(leg['legGeometry']['points'])
                        else:
                            route_points = leg['legGeometry']['points']
                        
                        # Convert to [lng, lat] format for GeoJSON
                        return [[point[1], point[0]] for point in route_points]
                        
                    except (KeyError, IndexError) as e:
                        continue  # Try next variation
        
        # If all attempts fail, return None to skip this route
        print(f"⚠️  Could not generate OTP route for {residence['lat']:.6f},{residence['lng']:.6f} to {destination['lat']:.6f},{destination['lng']:.6f}")
        return None
    
    def _generate_location_variations(self, coord: Coordinate, num_variations: int = 5) -> List[Coordinate]:
        """Generate small variations around a coordinate for retry attempts"""
        variations = [coord]  # Start with original
        
        # Add small random offsets (±50 meters approximately)
        for _ in range(num_variations - 1):
            offset_lat = np.random.uniform(-0.0005, 0.0005)  # ~±50m
            offset_lon = np.random.uniform(-0.0005, 0.0005)  # ~±50m
            
            new_lat = coord.lat + offset_lat
            new_lon = coord.lon + offset_lon
            
            # Validate bounds
            if 29.5 <= new_lat <= 33.3 and 34.2 <= new_lon <= 35.9:
                variations.append(Coordinate(new_lat, new_lon, coord.comment))
        
        return variations
    
    def calculate_statistics(self, pois: List[Dict], routes: List[Dict]) -> Dict:
        """Calculate summary statistics"""
        stats = {
            'totalPois': len(pois),
            'totalRoutes': len(routes),
            'poisWithComments': sum(1 for poi in pois if poi['hasComment']),
            'commentPercentage': round((sum(1 for poi in pois if poi['hasComment']) / len(pois) * 100) if pois else 0, 1),
            'averageDistance': round(np.mean([route['distance'] for route in routes]) if routes else 0, 1),
            'transportModes': {},
            'gateUsage': {}
        }
        
        # Transport mode distribution
        for route in routes:
            mode = route['transportMode']
            stats['transportModes'][mode] = stats['transportModes'].get(mode, 0) + 1
        
        # Gate usage
        for route in routes:
            gate_name = route['destination']['name']
            stats['gateUsage'][gate_name] = stats['gateUsage'].get(gate_name, 0) + 1
        
        # Calculate bounds for map centering
        if pois:
            lats = [poi['lat'] for poi in pois]
            lngs = [poi['lng'] for poi in pois]
            stats['bounds'] = {
                'north': max(lats),
                'south': min(lats),
                'east': max(lngs),
                'west': min(lngs),
                'center': {
                    'lat': sum(lats) / len(lats),
                    'lng': sum(lngs) / len(lngs)
                }
            }
        else:
            # Default to BGU area
            stats['bounds'] = {
                'center': {'lat': 31.2627, 'lng': 34.7983}
            }
        
        return stats
    
    def export_data(self, output_dir: str = 'outputs') -> Dict[str, Any]:
        """Export all data as JSON files"""
        os.makedirs(output_dir, exist_ok=True)
        
        # Load and process data
        self.load_data()
        pois = self.extract_pois()
        routes = self.extract_routes()
        stats = self.calculate_statistics(pois, routes)
        
        # Create complete dataset
        export_data = {
            'metadata': {
                'exportedAt': datetime.now().isoformat(),
                'source': 'BGU Mobility Survey',
                'version': '2.0'
            },
            'statistics': stats,
            'pois': pois,
            'routes': routes
        }
        
        # Save individual files
        files_saved = []
        
        # Complete dataset
        complete_path = os.path.join(output_dir, 'bgu_mobility_data.json')
        with open(complete_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)
        files_saved.append(complete_path)
        
        # Individual components for smaller file sizes
        poi_path = os.path.join(output_dir, 'pois.json')
        with open(poi_path, 'w', encoding='utf-8') as f:
            json.dump(pois, f, indent=2, ensure_ascii=False, default=str)
        files_saved.append(poi_path)
        
        route_path = os.path.join(output_dir, 'routes.json')
        with open(route_path, 'w', encoding='utf-8') as f:
            json.dump(routes, f, indent=2, ensure_ascii=False, default=str)
        files_saved.append(route_path)
        
        stats_path = os.path.join(output_dir, 'statistics.json')
        with open(stats_path, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=2, ensure_ascii=False, default=str)
        files_saved.append(stats_path)
        
        print(f"\n✓ Exported data files:")
        for file_path in files_saved:
            file_size = os.path.getsize(file_path) / 1024  # KB
            print(f"   📄 {file_path} ({file_size:.1f} KB)")
        
        return export_data

def main():
    """Main export function"""
    print("🗺️  BGU Mobility Data Exporter")
    print("=" * 40)
    
    exporter = BGUDataExporter()
    data = exporter.export_data()
    
    # Print summary
    stats = data['statistics']
    print(f"\n📊 Export Summary:")
    print(f"   📍 POIs: {stats['totalPois']} ({stats['poisWithComments']} with comments)")
    print(f"   🛣️  Routes: {stats['totalRoutes']}")
    print(f"   📏 Avg Distance: {stats['averageDistance']:.2f} km")
    
    print(f"\n🚇 Transportation Modes:")
    for mode, count in sorted(stats['transportModes'].items(), key=lambda x: x[1], reverse=True):
        percentage = (count / stats['totalRoutes']) * 100 if stats['totalRoutes'] > 0 else 0
        print(f"   • {mode.title()}: {count} ({percentage:.1f}%)")
    
    print(f"\n🏛️  Gate Usage:")
    for gate, count in sorted(stats['gateUsage'].items(), key=lambda x: x[1], reverse=True):
        percentage = (count / stats['totalRoutes']) * 100 if stats['totalRoutes'] > 0 else 0
        print(f"   • {gate}: {count} ({percentage:.1f}%)")
    
    print(f"\n🎯 Data ready for modern web visualization!")
    print("   Next: Use the exported JSON with the JavaScript interface")

if __name__ == "__main__":
    main() 