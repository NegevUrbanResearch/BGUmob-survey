#!/usr/bin/env python3
"""
BGU Mobility Survey - Points of Interest Mapping with Route Visualization
Creates interactive maps showing POI locations with comments and static route lines
from residences to campus via POIs using OTP road network routing.
"""

import pandas as pd
import json
import folium
from folium import plugins
import os
import numpy as np
import requests
import time
import logging
from datetime import datetime
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass
import polyline
from math import radians, cos, sin, asin, sqrt

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

class CoordinateParser:
    """Parse coordinate data from survey JSON strings"""
    
    @staticmethod
    def parse_coordinate_string(coord_str: str) -> List[Coordinate]:
        """Parse coordinate JSON string from survey data"""
        if pd.isna(coord_str) or not coord_str.strip():
            return []
        
        try:
            data = json.loads(coord_str)
            assert isinstance(data, list), f"Expected list, got {type(data)}"
            
            coordinates = []
            for item in data:
                assert 'coordinate' in item, "Missing 'coordinate' field"
                lat_lon = item['coordinate'].split(',')
                assert len(lat_lon) == 2, f"Invalid coordinate format: {item['coordinate']}"
                
                lat, lon = float(lat_lon[0]), float(lat_lon[1])
                comment = item.get('comment', '')
                coordinates.append(Coordinate(lat, lon, comment))
            
            return coordinates
        except (json.JSONDecodeError, ValueError, AssertionError) as e:
            logger.warning(f"Failed to parse coordinates '{coord_str}': {e}")
            return []

class BGUGateData:
    """BGU University gate/entrance data from BeerSheva Mobility project"""
    
    # BGU Gates from filtered entrances shapefile
    GATES = {
        'uni_south_3': Coordinate(31.261222, 34.801138, "University South Gate 3"),
        'uni_north_3': Coordinate(31.263911, 34.799290, "University North Gate 3"),
        'uni_west': Coordinate(31.262500, 34.805528, "University West Gate")
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
                        logger.warning("OTP returned no itineraries")
                        return None
                        
                elif response.status_code == 429:  # Rate limited
                    wait_time = (attempt + 1) * self.retry_delay
                    logger.warning(f"Rate limited, waiting {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.warning(f"OTP request failed: {response.status_code}")
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"OTP request error: {e}")
                
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
            logger.error(f"Error combining routes: {e}")
            return None

def interpolate_color(color1: str, color2: str, factor: float) -> str:
    """Interpolate between two hex colors based on factor (0-1)"""
    # Convert hex to RGB
    def hex_to_rgb(hex_color):
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    def rgb_to_hex(rgb):
        return '#{:02x}{:02x}{:02x}'.format(int(rgb[0]), int(rgb[1]), int(rgb[2]))
    
    # Get RGB values
    rgb1 = hex_to_rgb(color1)
    rgb2 = hex_to_rgb(color2)
    
    # Interpolate each channel
    interpolated = tuple(
        rgb1[i] + (rgb2[i] - rgb1[i]) * factor 
        for i in range(3)
    )
    
    return rgb_to_hex(interpolated)

def get_intensity_color(intensity: float) -> str:
    """Get smooth gradient color based on intensity level using green palette (darker = less, lighter = more)"""
    # Define color stops for smooth gradient (inverted: darker = less usage)
    color_stops = [
        (0.0, '#006400'),    # Dark Green - Low usage
        (0.25, '#228B22'),   # Forest Green - Low-medium usage
        (0.5, '#32CD32'),    # Lime Green - Medium usage
        (0.75, '#90EE90'),   # Light Green - High-medium usage
        (1.0, '#E8F5E8')     # Very Light Green - High usage
    ]
    
    # Clamp intensity to 0-1 range
    intensity = max(0.0, min(1.0, intensity))
    
    # Find the appropriate color segment
    for i in range(len(color_stops) - 1):
        if intensity <= color_stops[i + 1][0]:
            # Calculate local factor within this segment
            segment_start, color1 = color_stops[i]
            segment_end, color2 = color_stops[i + 1]
            
            if segment_end == segment_start:
                return color1
            
            local_factor = (intensity - segment_start) / (segment_end - segment_start)
            return interpolate_color(color1, color2, local_factor)
    
    # Fallback to last color
    return color_stops[-1][1]

def get_intensity_color_blend(intensity: float) -> str:
    """Get smooth gradient color for route lines (darker = less, lighter = more)"""
    # Define color stops for route lines (inverted: darker = less usage)
    color_stops = [
        (0.0, '#004D00'),    # Very Dark Green - Low usage
        (0.25, '#006400'),   # Dark Green - Low-medium usage
        (0.5, '#228B22'),    # Forest Green - Medium usage
        (0.75, '#32CD32'),   # Lime Green - High-medium usage
        (1.0, '#90EE90')     # Light Green - High usage
    ]
    
    # Clamp intensity to 0-1 range
    intensity = max(0.0, min(1.0, intensity))
    
    # Find the appropriate color segment
    for i in range(len(color_stops) - 1):
        if intensity <= color_stops[i + 1][0]:
            # Calculate local factor within this segment
            segment_start, color1 = color_stops[i]
            segment_end, color2 = color_stops[i + 1]
            
            if segment_end == segment_start:
                return color1
            
            local_factor = (intensity - segment_start) / (segment_end - segment_start)
            return interpolate_color(color1, color2, local_factor)
    
    # Fallback to last color
    return color_stops[-1][1]

def translate_mode_to_english(mode: str) -> str:
    """Translate Hebrew transportation modes to English"""
    # Handle nan values
    if pd.isna(mode) or str(mode).lower() == 'nan':
        return 'No Mode Data'
    
    translations = {
        'ברגל': 'Walking',
        'אופניים': 'Bicycle',
        'אופניים/קורקינט חשמלי': 'E-bike/Scooter',
        'רכב': 'Car',
        'אוטובוס': 'Bus',
        'רכבת': 'Train',
        '': 'Unknown',
        'Unknown': 'Unknown'
    }
    return translations.get(mode, mode)

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

def find_optimal_poi_stop(otp_simulator: OTPRouteSimulator, origin: Coordinate, destination: Coordinate, 
                         poi_list: List[Coordinate], transportation_mode: str) -> Optional[Coordinate]:
    """Find POI stop with least added travel time and distance under 2km constraint"""
    if not poi_list:
        return None
    
    # Get direct route as baseline
    direct_route = otp_simulator.get_walking_route(origin, destination, None, transportation_mode)
    if not direct_route:
        return None
    
    try:
        direct_duration = direct_route['plan']['itineraries'][0]['legs'][0]['duration']
        direct_distance = direct_route['plan']['itineraries'][0]['legs'][0]['distance']  # in meters
    except (KeyError, IndexError):
        return None
    
    best_poi = None
    min_added_time = float('inf')
    
    for poi in poi_list:
        # Test route via this POI
        poi_route = otp_simulator.get_walking_route(origin, destination, poi, transportation_mode)
        if poi_route:
            try:
                if 'intermediate_stop' in poi_route:
                    # Combined route duration and distance
                    poi_duration = poi_route['plan']['itineraries'][0]['legs'][0]['duration']
                    poi_distance = poi_route['plan']['itineraries'][0]['legs'][0]['distance']  # in meters
                else:
                    continue
                
                # Check distance constraint: POI route shouldn't add more than 2km
                added_distance = poi_distance - direct_distance
                if added_distance > 2000:  # 2km in meters
                    logger.debug(f"POI stop rejected: adds {added_distance/1000:.2f}km (>2km limit)")
                    continue
                
                added_time = poi_duration - direct_duration
                if added_time < min_added_time:
                    min_added_time = added_time
                    best_poi = poi
                    logger.debug(f"POI stop accepted: adds {added_distance/1000:.2f}km, {added_time/60:.1f}min")
                    
            except (KeyError, IndexError):
                continue
    
    return best_poi

def extract_survey_routes_with_otp(df: pd.DataFrame, otp_simulator: OTPRouteSimulator) -> List[Dict]:
    """Extract survey responses with OTP-based routes from residence to campus via POIs"""
    print(f"🛣️  Processing survey routes with OTP routing...")
    
    routes = []
    processed_count = 0
    total_responses = len(df)
    
    for idx, row in df.iterrows():
        # Progress report every 10 responses
        if processed_count % 10 == 0 and processed_count > 0:
            print(f"  📊 Progress: {processed_count}/{total_responses} responses processed ({processed_count/total_responses*100:.1f}%)")
        
        # Parse residence data
        if pd.isna(row['Residence-Info']) or not row['Residence-Info'].strip():
            continue
            
        residences = CoordinateParser.parse_coordinate_string(row['Residence-Info'])
        if not residences:
            continue
        
        residence = residences[0]  # Use first residence
        
        # Parse POI data
        pois = []
        if pd.notna(row['POI']) and row['POI'].strip():
            pois = CoordinateParser.parse_coordinate_string(row['POI'])
        
        # Find closest campus gate
        gate_name, gate_coord = BGUGateData.find_closest_gate(residence)
        
        # Get transportation mode
        transportation_mode = row.get('Transportation-Mode', '')
        
        # Select optimal POI stop with least added time
        intermediate_stop = None
        if pois:
            intermediate_stop = find_optimal_poi_stop(
                otp_simulator, residence, gate_coord, pois, transportation_mode
            )
        
        # Generate route with transportation mode
        route_data = otp_simulator.get_walking_route(
            residence,
            gate_coord,
            intermediate_stop,
            transportation_mode
        )
        
        if route_data:
            try:
                itinerary = route_data['plan']['itineraries'][0]
                leg = itinerary['legs'][0]
                
                # Decode route points
                if isinstance(leg['legGeometry']['points'], str):
                    route_points = polyline.decode(leg['legGeometry']['points'])
                else:
                    route_points = leg['legGeometry']['points']
                
                route_info = {
                    'submission_id': row['Submission ID'],
                    'residence': residence,
                    'pois': pois,
                    'destination_gate': {'name': gate_name, 'coord': gate_coord},
                    'route_coordinates': route_points,
                    'total_distance_km': leg.get('distance', 0) / 1000,
                    'duration_minutes': leg.get('duration', 0) / 60,
                    'transportation_mode': transportation_mode,
                    'num_pois': len(pois),
                    'has_poi_stop': 'intermediate_stop' in route_data,
                    'poi_stop': route_data.get('intermediate_stop')
                }
                
                routes.append(route_info)
                processed_count += 1
                
            except (KeyError, IndexError) as e:
                logger.error(f"Error processing route for submission {row['Submission ID']}: {e}")
        
        # Rate limiting
        time.sleep(0.1)
    
    print(f"✓ Generated {len(routes)} survey routes with OTP routing")
    print(f"  Routes with POI stops: {sum(1 for r in routes if r['has_poi_stop'])}")
    print(f"  Direct routes to campus: {sum(1 for r in routes if not r['has_poi_stop'])}")
    
    return routes

def create_folium_map(poi_df: pd.DataFrame, routes: List[Dict]) -> folium.Map:
    """Create an interactive Folium map with POI points, enhanced widgets, and OTP route lines."""
    
    # Calculate map center (around BGU area)
    center_lat = poi_df['lat'].median() if len(poi_df) > 0 else 31.2627
    center_lng = poi_df['lng'].median() if len(poi_df) > 0 else 34.7983
    
    # Create base map with dark OSM
    m = folium.Map(
        location=[center_lat, center_lng],
        zoom_start=13,
        tiles='CartoDB dark_matter',
        width='100%',
        height='100%'
    )
    
    # Add route lines first (so they appear under markers)
    print(f"🛣️  Adding {len(routes)} route lines to map...")
    
    # Group routes by transportation mode for filtering
    mode_groups = {}
    for route in routes:
        mode = route['transportation_mode'] or 'Unknown'
        if mode not in mode_groups:
            mode_groups[mode] = []
        mode_groups[mode].append(route)
    
    # Create route groups by mode for filtering
    for mode, mode_routes in mode_groups.items():
        print(f"  🎨 Creating {len(mode_routes)} routes for mode: {mode}")
        
        route_group = folium.FeatureGroup(
            name=f'{translate_mode_to_english(mode)}', 
            show=True,
            overlay=True
        )
        
        for route in mode_routes:
            coords = route['route_coordinates']
            if len(coords) >= 2:
                # Create route line coordinates for folium (lat, lng format)
                folium_coords = [[point[0], point[1]] for point in coords]
                
                # Calculate intensity based on route count in this mode
                mode_intensity = len(mode_routes) / len(routes) if routes else 0
                route_color = get_intensity_color_blend(mode_intensity)
                
                # Create route line with enhanced visibility for dark background
                route_line = folium.PolyLine(
                    locations=folium_coords,
                    color=route_color,
                    weight=4,
                    opacity=0.9,
                    popup=folium.Popup(
                        f"""
                        <div style="font-family: Arial, sans-serif; max-width: 150px; text-align: center;">
                            <h4 style="color: #333; margin: 0 0 8px 0; font-size: 14px;">{len(mode_routes)} Routes</h4>
                        </div>
                        """,
                        max_width=160
                    ),
                    tooltip=f"{len(mode_routes)} routes"
                )
                route_line.add_to(route_group)
        
        route_group.add_to(m)
    
    # Calculate gate usage intensity
    gate_usage = {}
    for route in routes:
        gate_name = route['destination_gate']['name']
        if gate_name not in gate_usage:
            gate_usage[gate_name] = 0
        gate_usage[gate_name] += 1
    
    max_gate_usage = max(gate_usage.values()) if gate_usage else 1
    
    # Enhanced POI clustering with better zoom handling
    marker_cluster = plugins.MarkerCluster(
        name='POI Points',
        overlay=True,
        control=True,
        options={
            'disableClusteringAtZoom': 18,  # Higher zoom level for clustering
            'maxClusterRadius': 80,         # Larger cluster radius
            'chunkedLoading': True,
            'spiderfyOnMaxZoom': True,      # Spread out markers at max zoom
            'showCoverageOnHover': True,    # Show cluster area on hover
            'zoomToBoundsOnClick': True,    # Zoom to cluster bounds on click
            'iconCreateFunction': '''
                function(cluster) {
                    var count = cluster.getChildCount();
                    var size = count < 10 ? 'small' : count < 100 ? 'medium' : 'large';
                    return L.divIcon({
                        html: '<div style="background-color: rgba(0, 100, 0, 0.8); color: white; border-radius: 50%; width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 12px;">' + count + '</div>',
                        className: 'marker-cluster-' + size,
                        iconSize: L.point(40, 40)
                    });
                }
            '''
        }
    )
    
    # Add all POI markers to cluster with enhanced styling
    for _, poi in poi_df.iterrows():
        popup_text = f"""
        <div style="font-family: Arial, sans-serif; max-width: 200px;">
            <h4 style="color: #333; margin: 0 0 8px 0;">📍 POI Location</h4>
            <p style="margin: 3px 0; font-style: italic; color: #666;">"{poi['comment']}"</p>
        </div>
        """
        
        folium.Marker(
            location=[poi['lat'], poi['lng']],
            popup=folium.Popup(popup_text, max_width=220),
            tooltip=poi['comment'],
            icon=folium.Icon(
                color='blue',
                icon='map-pin',
                prefix='fa'
            )
        ).add_to(marker_cluster)
    
    marker_cluster.add_to(m)
    
    # Add BGU campus gates with intensity visualization (color only, keep icons)
    gate_group = folium.FeatureGroup(name='Campus Gates', show=True)
    for gate_name, gate_coord in BGUGateData.GATES.items():
        # Calculate gate intensity
        usage_count = gate_usage.get(gate_name, 0)
        intensity = usage_count / max_gate_usage if max_gate_usage > 0 else 0
        gate_color = get_intensity_color(intensity)
        
        # Keep icon but color it based on intensity (inverted logic)
        icon_color = 'green' if intensity >= 0.6 else 'orange' if intensity >= 0.4 else 'red'
        
        folium.Marker(
            location=[gate_coord.lat, gate_coord.lon],
            popup=folium.Popup(
                f"""
                <div style="font-family: Arial, sans-serif; max-width: 150px; text-align: center;">
                    <h4 style="color: #333; margin: 0 0 8px 0; font-size: 14px;">{usage_count} Routes</h4>
                </div>
                """,
                max_width=160
            ),
            tooltip=f"{usage_count} routes",
            icon=folium.Icon(
                color=icon_color,
                icon='university',
                prefix='fa'
            )
        ).add_to(gate_group)
    
    gate_group.add_to(m)
    
    # Add layer control
    folium.LayerControl().add_to(m)
    
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
    
    return m, gate_usage, mode_groups

def export_folium_map(folium_map: folium.Map, filename_base: str, poi_count: int, route_count: int, gate_usage: Dict, mode_groups: Dict) -> None:
    """Export Folium map as HTML with title and full-screen responsive design."""
    html_path = f'outputs/{filename_base}.html'
    
    # Save the map
    folium_map.save(html_path)
    
    # Read the saved HTML and add title
    with open(html_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # Add title and custom CSS with enhanced styling
    title_and_css = f'''
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');
        
        body {{ 
            margin: 0; 
            padding: 0; 
            overflow: hidden; 
            font-family: 'Inter', Arial, sans-serif;
        }}
        #map {{ 
            height: 100vh !important; 
            width: 100vw !important; 
        }}
        .folium-map {{ 
            height: 100vh !important; 
            width: 100vw !important; 
        }}
        
        .map-title {{
            position: fixed;
            top: 20px;
            left: 20px;
            z-index: 9999;
            background: rgba(255, 255, 255, 0.95);
            padding: 15px 20px;
            border-radius: 10px;
            box-shadow: 0 6px 20px rgba(0,0,0,0.15);
            border: 2px solid #e9ecef;
            backdrop-filter: blur(10px);
            max-width: 250px;
        }}
        
        .map-title h1 {{
            margin: 0;
            font-size: 20px;
            font-weight: 700;
            color: #2c3e50;
        }}
        
        .map-title p {{
            margin: 6px 0 0 0;
            font-size: 13px;
            color: #7f8c8d;
        }}
        
        .stats-badge {{
            display: inline-block;
            background: #3498db;
            color: white;
            padding: 3px 6px;
            border-radius: 8px;
            font-size: 11px;
            font-weight: 600;
            margin-left: 6px;
        }}
        
        /* Enhanced legend styling */
        .legend-container {{
            position: fixed;
            bottom: 20px;
            left: 20px;
            z-index: 9999;
            background: rgba(255, 255, 255, 0.95);
            padding: 15px;
            border-radius: 10px;
            box-shadow: 0 6px 20px rgba(0,0,0,0.15);
            border: 2px solid #e9ecef;
            backdrop-filter: blur(10px);
            max-width: 200px;
        }}
        
        .legend-title {{
            font-size: 14px;
            font-weight: 600;
            color: #2c3e50;
            margin: 0 0 10px 0;
            text-align: center;
        }}
        
        .legend-item {{
            display: flex;
            align-items: center;
            margin: 6px 0;
            font-size: 11px;
            color: #555;
        }}
        
        .legend-color {{
            width: 20px;
            height: 8px;
            margin-right: 8px;
            border-radius: 2px;
            border: 1px solid rgba(0,0,0,0.1);
        }}
        
        .legend-label {{
            flex: 1;
            font-weight: 500;
        }}
        
        /* Enhanced cluster styling */
        .marker-cluster-small {{
            background-color: rgba(0, 100, 0, 0.6) !important;
        }}
        
        .marker-cluster-medium {{
            background-color: rgba(0, 100, 0, 0.7) !important;
        }}
        
        .marker-cluster-large {{
            background-color: rgba(0, 100, 0, 0.8) !important;
        }}
        
        /* Deck.gl inspired styling */
        .leaflet-control-layers {{
            background: rgba(255, 255, 255, 0.95) !important;
            border-radius: 8px !important;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15) !important;
            border: 1px solid rgba(255, 255, 255, 0.2) !important;
            backdrop-filter: blur(10px) !important;
        }}
        
        .leaflet-control-layers-list {{
            padding: 8px !important;
        }}
        
        .leaflet-control-layers-base label,
        .leaflet-control-layers-overlays label {{
            font-family: 'Inter', Arial, sans-serif !important;
            font-size: 12px !important;
            font-weight: 500 !important;
            color: #2c3e50 !important;
            margin: 4px 0 !important;
            padding: 4px 8px !important;
            border-radius: 4px !important;
            transition: background-color 0.2s ease !important;
        }}
        
        .leaflet-control-layers-base label:hover,
        .leaflet-control-layers-overlays label:hover {{
            background-color: rgba(52, 152, 219, 0.1) !important;
        }}
        
        .leaflet-control-scale {{
            background: rgba(255, 255, 255, 0.95) !important;
            border-radius: 6px !important;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1) !important;
            border: 1px solid rgba(255, 255, 255, 0.2) !important;
            backdrop-filter: blur(10px) !important;
        }}
        
        .leaflet-popup-content-wrapper {{
            background: rgba(255, 255, 255, 0.95) !important;
            border-radius: 8px !important;
            box-shadow: 0 4px 16px rgba(0,0,0,0.2) !important;
            border: 1px solid rgba(255, 255, 255, 0.2) !important;
            backdrop-filter: blur(10px) !important;
        }}
        
        .leaflet-popup-tip {{
            background: rgba(255, 255, 255, 0.95) !important;
            border: 1px solid rgba(255, 255, 255, 0.2) !important;
        }}
    </style>
    
    <div class="map-title">
        <h1>🗺️ BGU Mobility Survey</h1>
        <p>
            📍 {poi_count} POIs • <span class="stats-badge">{route_count} Routes</span>
        </p>
    </div>
    
    <div class="legend-container">
        <div class="legend-title">Route Intensity</div>
        <div class="legend-item">
            <div class="legend-color" style="background: linear-gradient(to right, #004D00, #006400);"></div>
            <div class="legend-label">Low Usage</div>
        </div>
        <div class="legend-item">
            <div class="legend-color" style="background: linear-gradient(to right, #006400, #228B22);"></div>
            <div class="legend-label">Medium-Low</div>
        </div>
        <div class="legend-item">
            <div class="legend-color" style="background: linear-gradient(to right, #228B22, #32CD32);"></div>
            <div class="legend-label">Medium</div>
        </div>
        <div class="legend-item">
            <div class="legend-color" style="background: linear-gradient(to right, #32CD32, #90EE90);"></div>
            <div class="legend-label">High Usage</div>
        </div>
    </div>
    '''
    
    # Insert the title and CSS after the opening body tag
    html_content = html_content.replace('<body>', '<body>' + title_and_css)
    
    # Write the modified HTML back
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"✓ Saved enhanced map with inverted intensity and improved clustering: {html_path}")

def main():
    """Main function to create enhanced POI visualization with OTP route lines."""
    print("🗺️  Creating BGU Student POI Map with Mode Filtering")
    print("=" * 60)
    
    # Load data
    df = load_processed_data()
    
    # Extract POI data
    poi_df = extract_all_pois(df)
    
    # Initialize OTP simulator (assumes OTP server is running)
    print("🔧 Initializing OTP route simulator...")
    otp_simulator = OTPRouteSimulator()
    
    # Extract route data with OTP routing
    routes = extract_survey_routes_with_otp(df, otp_simulator)
    
    if len(poi_df) == 0 and len(routes) == 0:
        print("⚠️  No valid POI or route data found!")
        return None
    
    # Create enhanced Folium map with mode filtering
    poi_map, gate_usage, mode_groups = create_folium_map(poi_df, routes)
    export_folium_map(poi_map, 'bgu_poi_map', len(poi_df), len(routes), gate_usage, mode_groups)
    
    print("\n🎯 Enhanced POI mapping with mode filtering completed!")
    print("✨ Features:")
    print("   • 🛣️ Route intensity by mode count")
    print("   • 🏛️ Gate usage intensity (color-coded)")
    print("   • 🚇 Transportation mode filtering")
    print("   • 📍 Simplified POI display")
    print("   • 🎨 Clean, minimal design")
    print("   • 📏 Distance and usage statistics")
    print("   • 🧭 Scale bar and north arrow")
    print("   • 📱 Responsive design with layer controls")
    
    # Print route statistics
    if routes:
        avg_distance = np.mean([r['total_distance_km'] for r in routes])
        routes_with_pois = sum(1 for r in routes if r['has_poi_stop'])
        
        print(f"\n📊 Route Statistics:")
        print(f"   • Total routes: {len(routes)}")
        print(f"   • Routes with POI stops: {routes_with_pois}")
        print(f"   • Direct routes to campus: {len(routes) - routes_with_pois}")
        print(f"   • Average route distance: {avg_distance:.2f} km")
        
        # Gate usage statistics
        print(f"\n🏛️ Gate Usage:")
        for gate_name, usage in sorted(gate_usage.items(), key=lambda x: x[1], reverse=True):
            percentage = (usage / len(routes)) * 100
            print(f"   • {gate_name}: {usage} routes ({percentage:.1f}%)")
        
        # Transportation mode statistics
        print(f"\n🚇 Transportation Modes:")
        for mode, mode_routes in sorted(mode_groups.items(), key=lambda x: len(x[1]), reverse=True):
            percentage = (len(mode_routes) / len(routes)) * 100
            print(f"   • {mode}: {len(mode_routes)} routes ({percentage:.1f}%)")
    
    # Save processed POI data
    if len(poi_df) > 0:
        poi_df.to_csv('outputs/processed_poi_data.csv', index=False)
        print("\n💾 Saved processed POI data: outputs/processed_poi_data.csv")
    
    # Save route data
    if routes:
        route_summary = []
        for route in routes:
            route_summary.append({
                'submission_id': route['submission_id'],
                'transportation_mode': route['transportation_mode'],
                'total_distance_km': route['total_distance_km'],
                'duration_minutes': route['duration_minutes'],
                'destination_gate': route['destination_gate']['name'],
                'has_poi_stop': route['has_poi_stop']
            })
        
        pd.DataFrame(route_summary).to_csv('outputs/route_summary_filtered.csv', index=False)
        print("💾 Saved filtered route summary: outputs/route_summary_filtered.csv")
    
    return poi_map

if __name__ == "__main__":
    # Create outputs directory
    os.makedirs('outputs', exist_ok=True)
    
    main()