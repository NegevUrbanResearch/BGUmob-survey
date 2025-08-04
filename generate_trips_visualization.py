#!/usr/bin/env python3
"""
BGU Mobility Survey - Trip Route Visualization Generator

This script processes BGU survey data to generate simulated walking routes 
from residence locations to university entrances with POI stops, creating 
a deck.gl visualization similar to the BeerShevaMobility project approach.

Author: Noam Gal

notes on starting local otp server: (you'll need to replace this with your own local otp server)
cd /Users/noamgal/Downloads/NUR/otp_project
java -Xmx8G -jar otp-2.5.0-shaded.jar --load --serve graphs
"""


import pandas as pd
import numpy as np
import json
import requests
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import polyline
from math import radians, cos, sin, asin, sqrt
import os

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
    
    def _query_otp_route(self, origin: Coordinate, destination: Coordinate) -> Optional[Dict]:
        """Query OTP server for walking route (legacy method)"""
        params = {
            'fromPlace': f"{origin.lat},{origin.lon}",
            'toPlace': f"{destination.lat},{destination.lon}",
            'mode': 'WALK',
            'date': datetime.now().strftime('%Y-%m-%d'),
            'time': '09:00:00',
            'arriveBy': 'false',
            'walkSpeed': 1.4,  # m/s
            'maxWalkDistance': 10000,
            'locale': 'en'
        }
        
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

class SurveyDataProcessor:
    """Process BGU survey data to extract routes"""
    
    def __init__(self, csv_path: str):
        self.df = pd.read_csv(csv_path)
        assert 'Residence-Info' in self.df.columns, "Residence-Info column missing"
        assert 'POI' in self.df.columns, "POI column missing"
        logger.info(f"Loaded {len(self.df)} survey responses")
    
    def extract_valid_responses(self) -> List[Dict]:
        """Extract responses with valid residence and POI data"""
        valid_responses = []
        
        for idx, row in self.df.iterrows():
            if pd.isna(row['Residence-Info']) or not row['Residence-Info'].strip():
                continue
                
            # Parse residence coordinates
            residences = CoordinateParser.parse_coordinate_string(row['Residence-Info'])
            if not residences:
                continue
            
            # Parse POI coordinates (if any)
            pois = []
            if pd.notna(row['POI']) and row['POI'].strip():
                pois = CoordinateParser.parse_coordinate_string(row['POI'])
            
            # Use first residence location
            primary_residence = residences[0]
            
            response_data = {
                'submission_id': row['Submission ID'],
                'residence': primary_residence,
                'pois': pois,
                'transportation_mode': row.get('Transportation-Mode', ''),
                'completed': row.get('Submission Completed', False)
            }
            
            valid_responses.append(response_data)
        
        logger.info(f"Found {len(valid_responses)} valid survey responses")
        assert len(valid_responses) > 0, "No valid survey responses found"
        return valid_responses

class DeckGLTripGenerator:
    """Generate deck.gl trips layer data"""
    
    def __init__(self, otp_simulator: OTPRouteSimulator):
        self.otp_simulator = otp_simulator
        self.trips = []
    
    def find_optimal_poi_stop(self, origin: Coordinate, destination: Coordinate, 
                             poi_list: List[Coordinate], transportation_mode: str) -> Optional[Coordinate]:
        """Find POI stop with least added travel time and distance under 2km constraint"""
        if not poi_list:
            return None
        
        # Get direct route as baseline
        direct_route = self.otp_simulator.get_walking_route(origin, destination, None, transportation_mode)
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
            poi_route = self.otp_simulator.get_walking_route(origin, destination, poi, transportation_mode)
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
    
    def generate_trips_from_survey(self, survey_responses: List[Dict]) -> List[Dict]:
        """Generate trip data from survey responses"""
        logger.info(f"Generating trips for {len(survey_responses)} survey responses")
        
        for i, response in enumerate(survey_responses):
            # Find closest university gate
            gate_name, gate_coord = BGUGateData.find_closest_gate(response['residence'])
            
            # Get transportation mode
            transportation_mode = response.get('transportation_mode', '')
            
            # Select optimal POI stop with least added time
            intermediate_stop = None
            if response['pois']:
                intermediate_stop = self.find_optimal_poi_stop(
                    response['residence'], 
                    gate_coord, 
                    response['pois'], 
                    transportation_mode
                )
            
            # Generate route with transportation mode
            route_data = self.otp_simulator.get_walking_route(
                response['residence'],
                gate_coord,
                intermediate_stop,
                transportation_mode
            )
            
            if route_data:
                trip = self._create_trip_data(
                    response, gate_name, gate_coord, route_data, i
                )
                self.trips.append(trip)
                
            # Rate limiting
            time.sleep(0.1)
            
            if (i + 1) % 10 == 0:
                logger.info(f"Processed {i + 1}/{len(survey_responses)} responses")
        
        logger.info(f"Generated {len(self.trips)} trips successfully")
        assert len(self.trips) > 0, "No trips were generated"
        return self.trips
    
    def _create_trip_data(self, response: Dict, gate_name: str, 
                         gate_coord: Coordinate, route_data: Dict, trip_id: int) -> Dict:
        """Create deck.gl trip data structure"""
        try:
            itinerary = route_data['plan']['itineraries'][0]
            leg = itinerary['legs'][0]
            
            # Decode route points
            if isinstance(leg['legGeometry']['points'], str):
                route_points = polyline.decode(leg['legGeometry']['points'])
            else:
                route_points = leg['legGeometry']['points']
            
            # Create timestamps for animation (10 seconds total trip time)
            num_points = len(route_points)
            timestamps = [i * (10000 / max(1, num_points - 1)) for i in range(num_points)]
            
            trip_data = {
                'vendor': trip_id,
                'path': [
                    [point[1], point[0], 0, timestamp] 
                    for point, timestamp in zip(route_points, timestamps)
                ],
                'timestamps': timestamps,
                'metadata': {
                    'submission_id': response['submission_id'],
                    'origin': {
                        'lat': response['residence'].lat,
                        'lon': response['residence'].lon,
                        'comment': response['residence'].comment
                    },
                    'destination': {
                        'gate_name': gate_name,
                        'lat': gate_coord.lat,
                        'lon': gate_coord.lon
                    },
                    'transportation_mode': response['transportation_mode'],
                    'distance_km': leg.get('distance', 0) / 1000,
                    'duration_minutes': leg.get('duration', 0) / 60,
                    'has_poi_stop': 'intermediate_stop' in route_data,
                    'poi_stop': route_data.get('intermediate_stop')
                }
            }
            
            return trip_data
            
        except (KeyError, IndexError) as e:
            logger.error(f"Error creating trip data: {e}")
            raise

    def save_deckgl_data(self, output_path: str = "bgu_trips_visualization.json"):
        """Save trips data for deck.gl visualization"""
        assert len(self.trips) > 0, "No trips to save"
        
        deckgl_data = {
            'trips': self.trips,
            'metadata': {
                'total_trips': len(self.trips),
                'generated_at': datetime.now().isoformat(),
                'bounds': self._calculate_bounds(),
                'description': 'BGU Mobility Survey - Simulated Walking Routes to University Gates'
            }
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(deckgl_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Saved {len(self.trips)} trips to {output_path}")
        return output_path
    
    def _calculate_bounds(self) -> Dict:
        """Calculate bounding box for all trips"""
        all_points = []
        for trip in self.trips:
            for point in trip['path']:
                all_points.append([point[1], point[0]])  # [lat, lon]
        
        if not all_points:
            return {}
        
        lats = [p[0] for p in all_points]
        lons = [p[1] for p in all_points]
        
        return {
            'min_lat': min(lats),
            'max_lat': max(lats),
            'min_lon': min(lons),
            'max_lon': max(lons)
        }

def create_html_visualization(trips_data: List[Dict], metadata: Dict, output_path: str = "bgu_trips_map.html"):
    """Create HTML file with deck.gl visualization - FIXED BASEMAP VERSION WITH EXTENSIVE LOGGING"""
    
    # Embed the data directly in the HTML to avoid CORS issues
    trips_json = json.dumps(trips_data, ensure_ascii=False)
    metadata_json = json.dumps(metadata, ensure_ascii=False)
    
    html_template = f"""
<!DOCTYPE html>
<html>
<head>
    <title>BGU Mobility Survey - Trip Routes Visualization</title>
    <script src="https://unpkg.com/deck.gl@^9.0.0/dist.min.js"></script>
    <script src="https://unpkg.com/@deck.gl/carto@^9.0.0/dist.min.js"></script>
    <style>
        body {{ margin: 0; font-family: Arial, sans-serif; }}
        #container {{ position: relative; height: 100vh; }}
        #control-panel {{
            position: absolute;
            top: 10px;
            left: 10px;
            background: rgba(255, 255, 255, 0.9);
            padding: 20px;
            border-radius: 8px;
            z-index: 1;
            max-width: 300px;
        }}
        #time-control {{
            margin-top: 15px;
        }}
        #play-button {{
            padding: 10px 20px;
            font-size: 16px;
            margin-right: 10px;
            cursor: pointer;
        }}
        #time-slider {{
            width: 100%;
            margin-bottom: 5px;
            -webkit-appearance: none;
            height: 6px;
            border-radius: 3px;
            background: rgba(255, 255, 255, 0.2);
            outline: none;
        }}
        
        #time-slider::-webkit-slider-thumb {{
            -webkit-appearance: none;
            appearance: none;
            width: 18px;
            height: 18px;
            border-radius: 50%;
            background: linear-gradient(135deg, #007cbf, #005a87);
            cursor: pointer;
            box-shadow: 0 2px 6px rgba(0, 124, 191, 0.4);
        }}
        
        #time-slider::-moz-range-thumb {{
            width: 18px;
            height: 18px;
            border-radius: 50%;
            background: linear-gradient(135deg, #007cbf, #005a87);
            cursor: pointer;
            border: none;
            box-shadow: 0 2px 6px rgba(0, 124, 191, 0.4);
        }}
        #debug-log {{
            position: absolute;
            bottom: 10px;
            left: 10px;
            background: rgba(0, 0, 0, 0.8);
            color: white;
            padding: 10px;
            border-radius: 5px;
            font-family: monospace;
            font-size: 12px;
            max-width: 500px;
            max-height: 200px;
            overflow-y: auto;
            z-index: 1000;
        }}
    </style>
</head>
<body>
    <div id="container">
        <div id="control-panel">
            <h3>BGU Trip Routes</h3>
            <p>Simulated walking routes from residences to university gates with POI stops</p>
            <div id="time-control">
                <button id="play-button" onclick="toggleAnimation()">Play</button>
                <input id="time-slider" type="range" min="0" max="10000" value="0" step="100">
            </div>
            <div id="stats"></div>
            <div id="legend">
                <h4>Transportation Modes</h4>
                <div style="display: flex; flex-direction: column; gap: 5px;">
                    <div><span style="background: rgb(0,255,0); width: 20px; height: 3px; display: inline-block; margin-right: 8px;"></span>Walking (ברגל)</div>
                    <div><span style="background: rgb(0,150,255); width: 20px; height: 3px; display: inline-block; margin-right: 8px;"></span>Bicycle (אופניים)</div>
                    <div><span style="background: rgb(0,100,255); width: 20px; height: 3px; display: inline-block; margin-right: 8px;"></span>E-bike/Scooter</div>
                    <div><span style="background: rgb(255,0,0); width: 20px; height: 3px; display: inline-block; margin-right: 8px;"></span>Car (רכב)</div>
                    <div><span style="background: rgb(255,255,0); width: 20px; height: 3px; display: inline-block; margin-right: 8px;"></span>Bus (אוטובוס)</div>
                </div>
            </div>
        </div>
        <div id="debug-log"></div>
    </div>

    <script>
        // Debug logging function
        function debugLog(message) {{
            console.log(`[BGU-DEBUG] ${{message}}`);
            const logDiv = document.getElementById('debug-log');
            if (logDiv) {{
                logDiv.innerHTML += `<div>${{new Date().toLocaleTimeString()}}: ${{message}}</div>`;
                logDiv.scrollTop = logDiv.scrollHeight;
            }}
        }}

        // Log initial page load
        debugLog('Page loaded, starting initialization');

        // Check if libraries are loaded
        debugLog(`deck object available: ${{typeof deck !== 'undefined'}}`);
        debugLog(`deck.DeckGL available: ${{typeof deck !== 'undefined' && typeof deck.DeckGL !== 'undefined'}}`);
        debugLog(`deck.carto available: ${{typeof deck !== 'undefined' && typeof deck.carto !== 'undefined'}}`);
        
        if (typeof deck !== 'undefined' && typeof deck.carto !== 'undefined') {{
            debugLog(`deck.carto.BASEMAP available: ${{typeof deck.carto.BASEMAP !== 'undefined'}}`);
            if (typeof deck.carto.BASEMAP !== 'undefined') {{
                debugLog(`Available basemaps: ${{Object.keys(deck.carto.BASEMAP).join(', ')}}`);
                debugLog(`DARK_MATTER value: ${{deck.carto.BASEMAP.DARK_MATTER}}`);
            }}
        }}

        // Embedded trip data (no CORS issues)
        const tripsData = {trips_json};
        const metadata = {metadata_json};
        debugLog(`Loaded ${{tripsData.length}} trips from embedded data`);

        // Initialize immediately since data is embedded
        document.addEventListener('DOMContentLoaded', function() {{
            debugLog('DOM Content Loaded event fired');
            updateStats(metadata);
            initializeMap();
        }});

        let currentTime = 0;
        let isPlaying = false;
        let animationId;
        let deckgl;

        // Test different basemap approaches with logging
        function testBasemapOptions() {{
            const basemapOptions = [
                {{ name: 'CARTO Constant DARK_MATTER', value: deck.carto.BASEMAP.DARK_MATTER }},
                {{ name: 'Direct URL Dark Matter', value: 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json' }},
                {{ name: 'CARTO Constant POSITRON', value: deck.carto.BASEMAP.POSITRON }},
                {{ name: 'Direct URL Positron', value: 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json' }}
            ];

            for (let option of basemapOptions) {{
                debugLog(`Testing ${{option.name}}: ${{option.value}}`);
                try {{
                    const testDeck = new deck.DeckGL({{
                        container: 'container',
                        mapStyle: option.value,
                        initialViewState: {{
                            longitude: 34.798,
                            latitude: 31.262,
                            zoom: 13,
                            pitch: 0,
                            bearing: 0
                        }},
                        controller: true,
                        layers: [],
                        onLoad: () => debugLog(`${{option.name}} loaded successfully`),
                        onError: (error) => debugLog(`${{option.name}} error: ${{error.message}}`)
                    }});
                    
                    debugLog(`${{option.name}} DeckGL instance created successfully`);
                    deckgl = testDeck; // Use the first successful one
                    return true;
                }} catch (error) {{
                    debugLog(`${{option.name}} failed: ${{error.message}}`);
                }}
            }}
            return false;
        }}

        function initializeMap() {{
            debugLog('Initializing map...');
            
            try {{
                // Test if we can create a DeckGL instance
                if (typeof deck === 'undefined') {{
                    throw new Error('deck.gl library not loaded');
                }}
                
                if (typeof deck.DeckGL === 'undefined') {{
                    throw new Error('deck.DeckGL not available');
                }}

                // Try the basemap options
                const success = testBasemapOptions();
                if (!success) {{
                    debugLog('All basemap options failed, trying without basemap');
                    deckgl = new deck.DeckGL({{
                        container: 'container',
                        initialViewState: {{
                            longitude: 34.798,
                            latitude: 31.262,
                            zoom: 13,
                            pitch: 0,
                            bearing: 0
                        }},
                        controller: true,
                        layers: []
                    }});
                    debugLog('DeckGL initialized without basemap');
                }}
                
                updateVisualization();
                debugLog('Map initialization complete');
                
            }} catch (error) {{
                debugLog(`Map initialization failed: ${{error.message}}`);
                debugLog(`Stack trace: ${{error.stack}}`);
            }}
        }}

        function initializeMap() {{
            updateVisualization();
        }}

        function getColorByMode(mode) {{
            const colors = {{
                'ברגל': [0, 255, 0],        // Walking - Green
                'אופניים': [0, 150, 255],   // Bicycle - Blue  
                'אופניים/קורקינט חשמלי': [0, 100, 255], // E-bike/Scooter - Dark blue
                'רכב': [255, 0, 0],         // Car - Red
                'אוטובוס': [255, 255, 0],   // Bus - Yellow
                '': [255, 140, 0],          // Default - Orange
                'Walking': [0, 255, 0],
                'Bicycle': [0, 150, 255],
                'E-bike/Scooter': [0, 100, 255],
                'Car': [255, 0, 0],
                'Bus': [255, 255, 0]
            }};
            return colors[mode] || [255, 140, 0];
        }}

        function updateVisualization() {{
            debugLog('Updating visualization...');
            
            try {{
                if (!deckgl) {{
                    debugLog('ERROR: deckgl instance not available');
                    return;
                }}

                debugLog(`Creating trips layer with ${{tripsData.length}} trips`);
                
                const layer = new deck.TripsLayer({{
                    id: 'trips-layer',
                    data: tripsData,
                    getPath: d => d.path,
                    getTimestamps: d => d.path.map(p => p[3]),
                    getColor: d => getColorByMode(d.metadata.transportation_mode),
                    opacity: 0.9,
                    widthMinPixels: 4,
                    capRounded: true,  // Updated from deprecated 'rounded'
                    jointRounded: true, // Updated from deprecated 'rounded'
                    fadeTrail: true,
                    trailLength: 3000,
                    currentTime: currentTime
                }});

                debugLog('Trips layer created, updating deck.gl props');
                deckgl.setProps({{
                    layers: [layer]
                }});
                debugLog('Visualization update complete');
                
            }} catch (error) {{
                debugLog(`Visualization update failed: ${{error.message}}`);
                debugLog(`Stack trace: ${{error.stack}}`);
            }}
        }}

        function toggleAnimation() {{
            debugLog('Toggle animation called');
            const button = document.getElementById('play-button');
            if (isPlaying) {{
                clearInterval(animationId);
                button.textContent = 'Play';
                isPlaying = false;
                debugLog('Animation paused');
            }} else {{
                animationId = setInterval(() => {{
                    currentTime += 100;
                    if (currentTime > 10000) {{
                        currentTime = 0;
                    }}
                    document.getElementById('time-slider').value = currentTime;
                    updateVisualization();
                }}, 50);
                button.textContent = 'Pause';
                isPlaying = true;
                debugLog('Animation started');
            }}
        }}

        document.getElementById('time-slider').addEventListener('input', function(e) {{
            currentTime = parseInt(e.target.value);
            debugLog(`Time slider changed to: ${{currentTime}}`);
            updateVisualization();
        }});

        function updateStats(metadata) {{
            debugLog('Updating stats panel');
            
            try {{
                // Count transportation modes
                const modeCounts = {{}};
                const poisCount = tripsData.filter(d => d.metadata.has_poi_stop).length;
                
                tripsData.forEach(trip => {{
                    const mode = trip.metadata.transportation_mode || 'Unknown';
                    modeCounts[mode] = (modeCounts[mode] || 0) + 1;
                }});
                
                let modeStats = '';
                Object.entries(modeCounts).forEach(([mode, count]) => {{
                    modeStats += `<div>${{mode || 'Unknown'}}: ${{count}}</div>`;
                }});
                
                document.getElementById('stats').innerHTML = `
                    <p><strong>Total Routes:</strong> ${{metadata.total_trips}}</p>
                    <p><strong>Routes with POI stops:</strong> ${{poisCount}}</p>
                    <p><strong>Transportation Modes:</strong></p>
                    ${{modeStats}}
                    <p><small>Generated: ${{new Date(metadata.generated_at).toLocaleString()}}</small></p>
                `;
                
                debugLog(`Stats updated: ${{metadata.total_trips}} total routes, ${{poisCount}} with POI stops`);
                
            }} catch (error) {{
                debugLog(`Stats update failed: ${{error.message}}`);
            }}
        }}

        // Error handling for unhandled errors
        window.addEventListener('error', function(event) {{
            debugLog(`Global error: ${{event.error.message}}`);
            debugLog(`At: ${{event.filename}}:${{event.lineno}}:${{event.colno}}`);
        }});

        // Additional debugging on window load
        window.addEventListener('load', function() {{
            debugLog('Window load event fired');
            debugLog(`Final library check - deck: ${{typeof deck}}, deck.carto: ${{typeof deck !== 'undefined' ? typeof deck.carto : 'undefined'}}`);
        }});
    </script>
</body>
</html>
    """
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_template)
    
    logger.info(f"Created HTML visualization: {output_path}")
    logger.info(f"📊 DEBUG: HTML file details:")
    logger.info(f"   - File size: {len(html_template)} characters")
    logger.info(f"   - Embedded trips count: {len(trips_data)}")
    logger.info(f"   - Sample metadata: {list(metadata.keys())}")
    logger.info(f"🔧 DEBUG: The HTML includes a debug log panel at the bottom of the page")
    logger.info(f"🔧 DEBUG: Check both the debug panel and browser console (F12) for detailed logs")
    return output_path

def create_html_visualization_integrated(trips_data: List[Dict], metadata: Dict, output_path: str = "bgu_trips_map.html"):
    """Create HTML file with properly integrated MapLibre + Deck.gl visualization"""
    
    # Embed the data directly in the HTML to avoid CORS issues
    trips_json = json.dumps(trips_data, ensure_ascii=False)
    metadata_json = json.dumps(metadata, ensure_ascii=False)
    
    html_template = f"""
<!DOCTYPE html>
<html>
<head>
    <title>BGU Mobility Survey - Trip Routes Visualization</title>
    
    <!-- MapLibre GL JS -->
    <script src="https://unpkg.com/maplibre-gl@4.0.2/dist/maplibre-gl.js"></script>
    <link href="https://unpkg.com/maplibre-gl@4.0.2/dist/maplibre-gl.css" rel="stylesheet" />
    
    <!-- Deck.gl -->
    <script src="https://unpkg.com/deck.gl@^9.0.0/dist.min.js"></script>
    <script src="https://unpkg.com/@deck.gl/mapbox@^9.0.0/dist.min.js"></script>
    
    <style>
        body {{ margin: 0; font-family: Arial, sans-serif; }}
        #map {{ width: 100%; height: 100vh; }}
        
        #control-panel {{
            position: absolute;
            top: 10px;
            left: 10px;
            background: rgba(40, 40, 40, 0.95);
            color: #ffffff;
            padding: 20px;
            border-radius: 12px;
            z-index: 1000;
            max-width: 240px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.4);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
        }}
        
        #time-control {{
            margin-top: 15px;
        }}
        
        #play-button {{
            padding: 12px 24px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            background: linear-gradient(135deg, #007cbf, #005a87);
            color: #ffffff;
            border: none;
            border-radius: 8px;
            transition: all 0.3s ease;
            box-shadow: 0 4px 12px rgba(0, 124, 191, 0.3);
        }}
        
        #play-button:hover {{
            background: linear-gradient(135deg, #0099e6, #007cbf);
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(0, 124, 191, 0.4);
        }}
        
        #play-button:active {{
            transform: translateY(0);
        }}
        
        #time-slider {{
            width: 200px;
        }}
        
        #debug-log {{
            display: none; /* Hidden but console logging still works */
        }}
        
        .legend-item {{
            display: flex;
            align-items: center;
            margin: 10px 0;
            font-size: 14px;
            font-weight: 500;
            color: #e0e0e0;
            transition: all 0.3s ease;
            padding: 6px 0;
        }}
        
        .legend-item:hover {{
            color: #ffffff;
            transform: translateX(4px);
        }}
        
        .legend-color {{
            width: 28px;
            height: 4px;
            margin-right: 14px;
            border-radius: 2px;
            box-shadow: 0 2px 6px rgba(0,0,0,0.3);
        }}
    </style>
</head>
<body>
    <div id="map"></div>
    
    <div id="control-panel">
        <h3 style="margin-top: 0; color: #ffffff; font-size: 18px; font-weight: 600;">BGU Trip Routes</h3>
        <p style="margin: 8px 0 20px 0; color: #b0b0b0; font-size: 13px;">Simulated routes from residences to university gates</p>
        
        <div id="time-control">
            <button id="play-button" onclick="toggleAnimation()">▶ Play</button>
            <br><br>
            <label for="time-slider" style="color: #e0e0e0; font-size: 12px; display: block; margin-bottom: 8px;">Animation Time:</label>
            <input id="time-slider" type="range" min="0" max="10000" value="0" step="100" style="width: 100%; margin-bottom: 5px;">
            <span id="time-display" style="color: #b0b0b0; font-size: 11px;">0ms</span>
        </div>
        
        <div id="legend" style="margin-top: 32px;">
            <h4 style="margin-bottom: 16px; color: #ffffff; font-size: 15px; font-weight: 600;">Transportation Modes</h4>
            <div class="legend-item">
                <div class="legend-color" style="background: linear-gradient(90deg, rgb(0,255,0), rgb(0,200,0));"></div>
                <span>Walking</span>
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background: linear-gradient(90deg, rgb(0,150,255), rgb(0,120,200));"></div>
                <span>Bicycle</span>
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background: linear-gradient(90deg, rgb(0,100,255), rgb(0,80,200));"></div>
                <span>E-bike/Scooter</span>
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background: linear-gradient(90deg, rgb(255,0,0), rgb(200,0,0));"></div>
                <span>Car</span>
            </div>
            <div class="legend-item">
                <div class="legend-color" style="background: linear-gradient(90deg, rgb(255,255,0), rgb(200,200,0));"></div>
                <span>Bus</span>
            </div>
            <div class="legend-item" style="margin-top: 20px; border-top: 1px solid rgba(255,255,255,0.2); padding-top: 15px;">
                <div style="width: 20px; height: 20px; margin-right: 14px; display: flex; align-items: center; justify-content: center;">
                    <svg width="16" height="20" viewBox="0 0 24 32" xmlns="http://www.w3.org/2000/svg">
                        <path d="M12 0C7.029 0 3 4.029 3 9c0 7.5 9 23 9 23s9-15.5 9-23c0-4.971-4.029-9-9-9z" fill="#888888" stroke="#FFFFFF" stroke-width="2"/>
                        <circle cx="12" cy="9" r="4" fill="#FFFFFF"/>
                        <circle cx="12" cy="9" r="2" fill="#888888"/>
                    </svg>
                </div>
                <span>POI Stops with Comments</span>
            </div>
        </div>
    </div>

    <script>
        // Debug logging function (console only)
        function debugLog(message) {{
            console.log(`[BGU] ${{message}}`);
        }}

        // Embedded trip data
        const tripsData = {trips_json};
        const metadata = {metadata_json};
        debugLog(`🎯 Loaded ${{tripsData.length}} trips from embedded data`);

        // Extract POI stops with comments from trips data
        function extractPOIStops() {{
            const poiStops = [];
            tripsData.forEach((trip, tripIndex) => {{
                if (trip.metadata.has_poi_stop && trip.metadata.poi_stop && trip.metadata.poi_stop.comment && trip.metadata.poi_stop.comment.trim() !== '') {{
                    poiStops.push({{
                        tripIndex: tripIndex,
                        lat: trip.metadata.poi_stop.lat,
                        lon: trip.metadata.poi_stop.lon,
                        comment: trip.metadata.poi_stop.comment.trim(),
                        transportation_mode: trip.metadata.transportation_mode,
                        submission_id: trip.metadata.submission_id
                    }});
                }}
            }});
            debugLog(`📍 Extracted ${{poiStops.length}} POI stops with comments`);
            return poiStops;
        }}

        const poiStopsData = extractPOIStops();

        let currentTime = 0;
        let isPlaying = false;
        let animationId;
        let map;
        let deckOverlay;

        // Translation function for transportation modes (used in tooltips)
        function translateModeToEnglish(mode) {{
            const translations = {{
                'ברגל': 'Walking',
                'אופניים': 'Bicycle', 
                'אופניים/קורקינט חשמלי': 'E-bike/Scooter',
                'רכב': 'Car',
                'אוטובוס': 'Bus',
                '': 'Unknown'
            }};
            return translations[mode] || mode || 'Unknown';
        }}

        // Helper function to convert RGB array to CSS color
        function rgbArrayToCss(rgbArray) {{
            return `rgb(${{rgbArray[0]}}, ${{rgbArray[1]}}, ${{rgbArray[2]}})`;
        }}

        // Animation and UI state
        function updateTimeDisplay() {{
            document.getElementById('time-display').textContent = `${{currentTime}}ms`;
        }}

        function getColorByMode(mode) {{
            const colors = {{
                'ברגל': [0, 255, 0],        // Green for walking
                'אופניים': [0, 150, 255],   // Blue for bicycle
                'אופניים/קורקינט חשמלי': [0, 100, 255], // Dark blue for e-bike/scooter
                'רכב': [255, 0, 0],         // Red for car
                'אוטובוס': [255, 255, 0],   // Yellow for bus
                '': [255, 140, 0]           // Default orange
            }};
            return colors[mode] || [255, 140, 0];
        }}

        function createTripsLayer() {{
            debugLog(`🔄 Creating trips layer with time: ${{currentTime}}`);
            
            return new deck.TripsLayer({{
                id: 'trips-layer',
                data: tripsData,
                getPath: d => d.path,
                getTimestamps: d => d.path.map(p => p[3]),
                getColor: d => getColorByMode(d.metadata.transportation_mode),
                opacity: 0.8,
                widthMinPixels: 3,
                widthMaxPixels: 8,
                capRounded: true,
                jointRounded: true,
                fadeTrail: true,
                trailLength: 2000,
                currentTime: currentTime
            }});
        }}

        function createPOIMarkersLayer() {{
            debugLog(`📍 Creating POI markers layer with ${{poiStopsData.length}} stops`);
            
            // Generate colored POI pin icons for each transportation mode
            function createPOIIcon(color) {{
                const svg = `
                    <svg width="24" height="32" viewBox="0 0 24 32" xmlns="http://www.w3.org/2000/svg">
                        <path d="M12 0C7.029 0 3 4.029 3 9c0 7.5 9 23 9 23s9-15.5 9-23c0-4.971-4.029-9-9-9z" fill="rgb(${{color[0]}},${{color[1]}},${{color[2]}})" stroke="#FFFFFF" stroke-width="2"/>
                        <circle cx="12" cy="9" r="4" fill="#FFFFFF"/>
                        <circle cx="12" cy="9" r="2" fill="rgb(${{color[0]}},${{color[1]}},${{color[2]}})"/>
                    </svg>
                `;
                return 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svg);
            }}
            
            // Pre-generate icons for each mode
            const modeIcons = {{
                'ברגל': createPOIIcon([0, 255, 0]),        // Walking - Green
                'אופניים': createPOIIcon([0, 150, 255]),   // Bicycle - Blue  
                'אופניים/קורקינט חשמלי': createPOIIcon([0, 100, 255]), // E-bike/Scooter - Dark blue
                'רכב': createPOIIcon([255, 0, 0]),         // Car - Red
                'אוטובוס': createPOIIcon([255, 255, 0]),   // Bus - Yellow
                '': createPOIIcon([255, 140, 0])           // Default - Orange
            }};
            
            return new deck.IconLayer({{
                id: 'poi-markers-layer',
                data: poiStopsData,
                getPosition: d => [d.lon, d.lat],
                getIcon: d => ({{
                    url: modeIcons[d.transportation_mode] || modeIcons[''],
                    width: 24,
                    height: 32,
                    anchorY: 32 // Anchor at the bottom of the pin
                }}),
                getSize: 18, // Smaller size
                pickable: true,
                sizeScale: 1,
                billboard: true // Always face the camera
            }});
        }}

        function updateVisualization() {{
            if (!deckOverlay) {{
                debugLog('❌ Deck overlay not ready');
                return;
            }}

            const tripsLayer = createTripsLayer();
            const poiLayer = createPOIMarkersLayer();
            deckOverlay.setProps({{ layers: [tripsLayer, poiLayer] }});
            updateTimeDisplay();
        }}

        function toggleAnimation() {{
            const button = document.getElementById('play-button');
            
            if (isPlaying) {{
                clearInterval(animationId);
                button.innerHTML = '▶ Play';
                isPlaying = false;
                debugLog('⏸ Animation paused');
            }} else {{
                animationId = setInterval(() => {{
                    currentTime += 100;
                    if (currentTime > 10000) {{
                        currentTime = 0;
                    }}
                    document.getElementById('time-slider').value = currentTime;
                    updateVisualization();
                }}, 60); // ~16fps
                
                button.innerHTML = '⏸ Pause';
                isPlaying = true;
                debugLog('▶ Animation started');
            }}
        }}

        // Time slider control
        document.getElementById('time-slider').addEventListener('input', function(e) {{
            currentTime = parseInt(e.target.value);
            updateVisualization();
        }});

        // Initialize the application
        function initializeApp() {{
            debugLog('🚀 Initializing BGU Mobility Visualization');
            
            // Check library availability
            debugLog(`📚 MapLibre available: ${{typeof maplibregl !== 'undefined'}}`);
            debugLog(`📚 Deck.gl available: ${{typeof deck !== 'undefined'}}`);
            debugLog(`📚 MapboxOverlay available: ${{typeof deck.MapboxOverlay !== 'undefined'}}`);
            
            if (typeof maplibregl === 'undefined') {{
                debugLog('❌ MapLibre GL not loaded');
                return;
            }}
            
            if (typeof deck === 'undefined' || typeof deck.MapboxOverlay === 'undefined') {{
                debugLog('❌ Deck.gl or MapboxOverlay not loaded');
                return;
            }}

            // Create MapLibre map
            debugLog('🗺 Creating MapLibre map...');
            map = new maplibregl.Map({{
                container: 'map',
                style: 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json',
                center: [34.798, 31.262],
                zoom: 12,
                pitch: 0,
                bearing: 0
            }});

            // Add map controls
            map.addControl(new maplibregl.NavigationControl(), 'top-right');
            map.addControl(new maplibregl.ScaleControl(), 'bottom-right');

            map.on('load', function() {{
                debugLog('✅ MapLibre map loaded successfully');
                
                // Create Deck.gl overlay
                debugLog('🎨 Creating Deck.gl overlay...');
                deckOverlay = new deck.MapboxOverlay({{
                    layers: [createTripsLayer(), createPOIMarkersLayer()],
                    getTooltip: ({{object, layer}}) => {{
                        if (object) {{
                            // Handle POI marker tooltips
                            if (layer.id === 'poi-markers-layer') {{
                                const modeColor = getColorByMode(object.transportation_mode);
                                const bgColor = `rgba(${{modeColor[0]}}, ${{modeColor[1]}}, ${{modeColor[2]}}, 0.95)`;
                                const borderColor = `rgba(${{modeColor[0]}}, ${{modeColor[1]}}, ${{modeColor[2]}}, 0.3)`;
                                
                                return {{
                                    html: `
                                        <div style="padding: 15px; background: ${{bgColor}}; color: #ffffff; border-radius: 10px; font-size: 14px; line-height: 1.5; box-shadow: 0 8px 32px rgba(0,0,0,0.4); backdrop-filter: blur(10px); border: 2px solid ${{borderColor}}; max-width: 280px;">
                                            <div style="display: flex; align-items: center; margin-bottom: 10px;">
                                                <div style="font-size: 20px; margin-right: 8px;">📍</div>
                                                <div style="font-weight: 600; color: #ffffff;">POI Stop</div>
                                            </div>
                                            <div style="background: rgba(255, 255, 255, 0.2); padding: 10px; border-radius: 6px; margin-bottom: 8px;">
                                                <div style="font-style: italic; color: #fff; font-size: 13px;">
                                                    "${{object.comment}}"
                                                </div>
                                            </div>
                                            <div style="color: rgba(255, 255, 255, 0.9); font-size: 12px; margin: 4px 0;">
                                                Mode: ${{translateModeToEnglish(object.transportation_mode) || 'Unknown'}}
                                            </div>
                                            <div style="color: rgba(255, 255, 255, 0.9); font-size: 12px; margin: 4px 0;">
                                                Submission: ${{object.submission_id}}
                                            </div>
                                        </div>
                                    `,
                                }};
                            }}
                            
                            // Handle trip route tooltips
                            if (layer.id === 'trips-layer') {{
                                const {{metadata}} = object;
                                return {{
                                    html: `
                                        <div style="padding: 12px; background: rgba(20, 20, 20, 0.95); color: #ffffff; border-radius: 8px; font-size: 13px; line-height: 1.4; box-shadow: 0 8px 32px rgba(0,0,0,0.4); backdrop-filter: blur(10px); border: 1px solid rgba(255, 255, 255, 0.1);">
                                            <div style="font-weight: 600; margin-bottom: 8px; color: #ffffff;">Route Details</div>
                                            <div style="color: #e0e0e0; margin: 4px 0;">Mode: ${{translateModeToEnglish(metadata.transportation_mode) || 'Unknown'}}</div>
                                            <div style="color: #e0e0e0; margin: 4px 0;">Distance: ${{metadata.distance_km.toFixed(2)}} km</div>
                                            <div style="color: #e0e0e0; margin: 4px 0;">Duration: ${{metadata.duration_minutes.toFixed(1)}} min</div>
                                            <div style="color: #e0e0e0; margin: 4px 0;">Gate: ${{metadata.destination.gate_name}}</div>
                                            ${{metadata.has_poi_stop ? '<div style="color: #4CAF50; margin: 4px 0;">Has POI stop</div>' : ''}}
                                        </div>
                                    `,
                                }};
                            }}
                        }}
                        return null;
                    }}
                }});

                map.addControl(deckOverlay);
                debugLog('✅ Deck.gl overlay added successfully');
                
                debugLog('🎉 Initialization complete! Ready for animation.');
            }});

            map.on('error', function(e) {{
                debugLog(`❌ MapLibre error: ${{e.error?.message || 'Unknown error'}}`);
                debugLog('🔄 Trying fallback to Positron style...');
                
                try {{
                    map.setStyle('https://basemaps.cartocdn.com/gl/positron-gl-style/style.json');
                }} catch (fallbackError) {{
                    debugLog(`❌ Fallback also failed: ${{fallbackError.message}}`);
                }}
            }});
        }}

        // Error handling
        window.addEventListener('error', function(event) {{
            debugLog(`💥 Global error: ${{event.error?.message || event.message}}`);
        }});

        // Start the application when DOM is ready
        document.addEventListener('DOMContentLoaded', function() {{
            debugLog('📄 DOM loaded, starting app...');
            initializeApp();
        }});

        // Additional check when window loads
        window.addEventListener('load', function() {{
            debugLog('🌐 Window fully loaded');
        }});
    </script>
</body>
</html>
    """
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_template)
    
    logger.info(f"Created integrated MapLibre + Deck.gl visualization: {output_path}")
    logger.info(f"📊 Features: MapboxOverlay integration, tooltips, clean UI, POI distance constraint")
    logger.info(f"🎨 Styling: Minimalist dark theme with animation controls and transportation legend")
    logger.info(f"🔧 Debug: Console logging available (F12 to view)")
    return output_path

def create_html_visualization_maplibre(trips_data: List[Dict], metadata: Dict, output_path: str = "bgu_trips_map.html"):
    """Create HTML file with deck.gl + MapLibre visualization - FIXED BASEMAP VERSION"""
    
    # Embed the data directly in the HTML to avoid CORS issues
    trips_json = json.dumps(trips_data, ensure_ascii=False)
    metadata_json = json.dumps(metadata, ensure_ascii=False)
    
    html_template = f"""
<!DOCTYPE html>
<html>
<head>
    <title>BGU Mobility Survey - Trip Routes Visualization</title>
    <!-- MapLibre GL JS -->
    <script src="https://unpkg.com/maplibre-gl@4.0.2/dist/maplibre-gl.js"></script>
    <link href="https://unpkg.com/maplibre-gl@4.0.2/dist/maplibre-gl.css" rel="stylesheet" />
    
    <!-- Deck.gl -->
    <script src="https://unpkg.com/deck.gl@^9.0.0/dist.min.js"></script>
    <script src="https://unpkg.com/@deck.gl/carto@^9.0.0/dist.min.js"></script>
    
    <style>
        body {{ margin: 0; font-family: Arial, sans-serif; }}
        #map {{ position: absolute; top: 0; left: 0; width: 100%; height: 100%; }}
        #deck-canvas {{ position: absolute; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none; }}
        #control-panel {{
            position: absolute;
            top: 10px;
            left: 10px;
            background: rgba(255, 255, 255, 0.9);
            padding: 20px;
            border-radius: 8px;
            z-index: 1000;
            max-width: 300px;
        }}
        #time-control {{
            margin-top: 15px;
        }}
        #play-button {{
            padding: 10px 20px;
            font-size: 16px;
            margin-right: 10px;
            cursor: pointer;
        }}
        #time-slider {{
            width: 200px;
        }}
        #debug-log {{
            position: absolute;
            bottom: 10px;
            left: 10px;
            background: rgba(0, 0, 0, 0.8);
            color: white;
            padding: 10px;
            border-radius: 5px;
            font-family: monospace;
            font-size: 12px;
            max-width: 500px;
            max-height: 200px;
            overflow-y: auto;
            z-index: 1000;
        }}
    </style>
</head>
<body>
    <div id="map"></div>
    <canvas id="deck-canvas"></canvas>
    
    <div id="control-panel">
        <h3>BGU Trip Routes</h3>
        <p>Simulated walking routes from residences to university gates with POI stops</p>
        <div id="time-control">
            <button id="play-button" onclick="toggleAnimation()">Play</button>
            <input id="time-slider" type="range" min="0" max="10000" value="0" step="100">
        </div>
        <div id="stats"></div>
        <div id="legend">
            <h4>Transportation Modes</h4>
            <div style="display: flex; flex-direction: column; gap: 5px;">
                <div><span style="background: rgb(0,255,0); width: 20px; height: 3px; display: inline-block; margin-right: 8px;"></span>Walking (ברגל)</div>
                <div><span style="background: rgb(0,150,255); width: 20px; height: 3px; display: inline-block; margin-right: 8px;"></span>Bicycle (אופניים)</div>
                <div><span style="background: rgb(0,100,255); width: 20px; height: 3px; display: inline-block; margin-right: 8px;"></span>E-bike/Scooter</div>
                <div><span style="background: rgb(255,0,0); width: 20px; height: 3px; display: inline-block; margin-right: 8px;"></span>Car (רכב)</div>
                <div><span style="background: rgb(255,255,0); width: 20px; height: 3px; display: inline-block; margin-right: 8px;"></span>Bus (אוטובוס)</div>
            </div>
        </div>
    </div>
    <div id="debug-log"></div>

    <script>
        // Debug logging function
        function debugLog(message) {{
            console.log(`[BGU-DEBUG] ${{message}}`);
            const logDiv = document.getElementById('debug-log');
            if (logDiv) {{
                logDiv.innerHTML += `<div>${{new Date().toLocaleTimeString()}}: ${{message}}</div>`;
                logDiv.scrollTop = logDiv.scrollHeight;
            }}
        }}

        // Log initial page load
        debugLog('Page loaded, starting MapLibre + Deck.gl initialization');

        // Check if libraries are loaded
        debugLog(`maplibregl available: ${{typeof maplibregl !== 'undefined'}}`);
        debugLog(`deck available: ${{typeof deck !== 'undefined'}}`);
        debugLog(`deck.DeckGL available: ${{typeof deck !== 'undefined' && typeof deck.DeckGL !== 'undefined'}}`);

        // Embedded trip data
        const tripsData = {trips_json};
        const metadata = {metadata_json};
        debugLog(`Loaded ${{tripsData.length}} trips from embedded data`);

        let currentTime = 0;
        let isPlaying = false;
        let animationId;
        let map;
        let deckgl;

        // Initialize MapLibre map
        function initializeMap() {{
            debugLog('Initializing MapLibre map...');
            
            try {{
                // Create MapLibre map with CARTO Dark Matter style
                map = new maplibregl.Map({{
                    container: 'map',
                    style: 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json',
                    center: [34.798, 31.262],
                    zoom: 13,
                    interactive: true
                }});

                map.on('load', function() {{
                    debugLog('MapLibre map loaded successfully');
                    initializeDeckGL();
                }});

                map.on('error', function(e) {{
                    debugLog(`MapLibre error: ${{e.error.message}}`);
                    // Try fallback with Positron style
                    debugLog('Trying fallback to Positron style...');
                    map.setStyle('https://basemaps.cartocdn.com/gl/positron-gl-style/style.json');
                }});

            }} catch (error) {{
                debugLog(`MapLibre initialization failed: ${{error.message}}`);
                debugLog('Trying without basemap...');
                initializeDeckGLStandalone();
            }}
        }}

        // Initialize Deck.GL overlaid on MapLibre
        function initializeDeckGL() {{
            debugLog('Initializing Deck.GL overlay...');
            
            try {{
                deckgl = new deck.DeckGL({{
                    canvas: 'deck-canvas',
                    initialViewState: {{
                        longitude: 34.798,
                        latitude: 31.262,
                        zoom: 13,
                        pitch: 0,
                        bearing: 0
                    }},
                    controller: false, // Let MapLibre handle interactions
                    onViewStateChange: ({{viewState}}) => {{
                        // Sync Deck.GL view with MapLibre
                        const {{longitude, latitude, zoom, pitch, bearing}} = viewState;
                        map.jumpTo({{
                            center: [longitude, latitude],
                            zoom: zoom,
                            pitch: pitch,
                            bearing: bearing
                        }});
                    }},
                    layers: []
                }});

                // Sync MapLibre view changes to Deck.GL
                map.on('move', () => {{
                    const center = map.getCenter();
                    const zoom = map.getZoom();
                    const pitch = map.getPitch();
                    const bearing = map.getBearing();
                    
                    deckgl.setProps({{
                        viewState: {{
                            longitude: center.lng,
                            latitude: center.lat,
                            zoom: zoom,
                            pitch: pitch,
                            bearing: bearing
                        }}
                    }});
                }});

                debugLog('Deck.GL overlay initialized successfully');
                updateVisualization();
                
            }} catch (error) {{
                debugLog(`Deck.GL overlay initialization failed: ${{error.message}}`);
            }}
        }}

        // Fallback: Initialize Deck.GL standalone (no basemap)
        function initializeDeckGLStandalone() {{
            debugLog('Initializing Deck.GL standalone (no basemap)...');
            
            try {{
                deckgl = new deck.DeckGL({{
                    canvas: 'deck-canvas',
                    initialViewState: {{
                        longitude: 34.798,
                        latitude: 31.262,
                        zoom: 13,
                        pitch: 0,
                        bearing: 0
                    }},
                    controller: true,
                    layers: []
                }});

                debugLog('Deck.GL standalone initialized successfully');
                updateVisualization();
                
            }} catch (error) {{
                debugLog(`Deck.GL standalone initialization failed: ${{error.message}}`);
            }}
        }}

        function getColorByMode(mode) {{
            const colors = {{
                'ברגל': [0, 255, 0],        // Green for walking
                'אופניים': [0, 150, 255],   // Blue for bicycle
                'אופניים/קורקינט חשמלי': [0, 100, 255], // Dark blue for e-bike/scooter
                'רכב': [255, 0, 0],         // Red for car
                'אוטובוס': [255, 255, 0],   // Yellow for bus
                '': [255, 140, 0]           // Default orange
            }};
            return colors[mode] || [255, 140, 0];
        }}

        function updateVisualization() {{
            debugLog('Updating visualization...');
            
            try {{
                if (!deckgl) {{
                    debugLog('ERROR: deckgl instance not available');
                    return;
                }}

                debugLog(`Creating trips layer with ${{tripsData.length}} trips`);
                
                const layer = new deck.TripsLayer({{
                    id: 'trips-layer',
                    data: tripsData,
                    getPath: d => d.path,
                    getTimestamps: d => d.path.map(p => p[3]),
                    getColor: d => getColorByMode(d.metadata.transportation_mode),
                    opacity: 0.9,
                    widthMinPixels: 4,
                    capRounded: true,  // Updated from deprecated 'rounded'
                    jointRounded: true, // Updated from deprecated 'rounded'
                    fadeTrail: true,
                    trailLength: 3000,
                    currentTime: currentTime
                }});

                debugLog('Trips layer created, updating deck.gl props');
                deckgl.setProps({{
                    layers: [layer]
                }});
                debugLog('Visualization update complete');
                
            }} catch (error) {{
                debugLog(`Visualization update failed: ${{error.message}}`);
                debugLog(`Stack trace: ${{error.stack}}`);
            }}
        }}

        function toggleAnimation() {{
            debugLog('Toggle animation called');
            const button = document.getElementById('play-button');
            if (isPlaying) {{
                clearInterval(animationId);
                button.textContent = 'Play';
                isPlaying = false;
                debugLog('Animation paused');
            }} else {{
                animationId = setInterval(() => {{
                    currentTime += 100;
                    if (currentTime > 10000) {{
                        currentTime = 0;
                    }}
                    document.getElementById('time-slider').value = currentTime;
                    updateVisualization();
                }}, 50);
                button.textContent = 'Pause';
                isPlaying = true;
                debugLog('Animation started');
            }}
        }}

        document.getElementById('time-slider').addEventListener('input', function(e) {{
            currentTime = parseInt(e.target.value);
            debugLog(`Time slider changed to: ${{currentTime}}`);
            updateVisualization();
        }});

        function updateStats(metadata) {{
            debugLog('Updating stats panel');
            
            try {{
                // Count transportation modes
                const modeCounts = {{}};
                const poisCount = tripsData.filter(d => d.metadata.has_poi_stop).length;
                
                tripsData.forEach(trip => {{
                    const mode = trip.metadata.transportation_mode || 'Unknown';
                    modeCounts[mode] = (modeCounts[mode] || 0) + 1;
                }});
                
                let modeStats = '';
                Object.entries(modeCounts).forEach(([mode, count]) => {{
                    modeStats += `<div>${{mode || 'Unknown'}}: ${{count}}</div>`;
                }});
                
                document.getElementById('stats').innerHTML = `
                    <p><strong>Total Routes:</strong> ${{metadata.total_trips}}</p>
                    <p><strong>Routes with POI stops:</strong> ${{poisCount}}</p>
                    <p><strong>Transportation Modes:</strong></p>
                    ${{modeStats}}
                    <p><small>Generated: ${{new Date(metadata.generated_at).toLocaleString()}}</small></p>
                `;
                
                debugLog(`Stats updated: ${{metadata.total_trips}} total routes, ${{poisCount}} with POI stops`);
                
            }} catch (error) {{
                debugLog(`Stats update failed: ${{error.message}}`);
            }}
        }}

        // Error handling for unhandled errors
        window.addEventListener('error', function(event) {{
            debugLog(`Global error: ${{event.error.message}}`);
            debugLog(`At: ${{event.filename}}:${{event.lineno}}:${{event.colno}}`);
        }});

        // Initialize when DOM is ready
        document.addEventListener('DOMContentLoaded', function() {{
            debugLog('DOM Content Loaded event fired');
            updateStats(metadata);
            initializeMap();
        }});

        // Additional debugging on window load
        window.addEventListener('load', function() {{
            debugLog('Window load event fired');
            debugLog(`Final library check - maplibregl: ${{typeof maplibregl}}, deck: ${{typeof deck}}`);
        }});
    </script>
</body>
</html>
    """
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_template)
    
    logger.info(f"Created MapLibre HTML visualization: {output_path}")
    logger.info(f"📊 DEBUG: MapLibre HTML file details:")
    logger.info(f"   - File size: {len(html_template)} characters")
    logger.info(f"   - Embedded trips count: {len(trips_data)}")
    logger.info(f"   - Uses MapLibre GL JS for basemap rendering")
    logger.info(f"🔧 DEBUG: The HTML includes a debug log panel at the bottom of the page")
    logger.info(f"🔧 DEBUG: Check both the debug panel and browser console (F12) for detailed logs")
    return output_path

def main():
    """Main execution function"""
    logger.info("Starting BGU Mobility Survey Trip Route Generation")
    
    # Initialize components
    csv_path = "data/processed_mobility_data.csv"
    assert os.path.exists(csv_path), f"Survey data file not found: {csv_path}"
    
    # Process survey data
    processor = SurveyDataProcessor(csv_path)
    survey_responses = processor.extract_valid_responses()
    
    # Initialize OTP simulator (assumes OTP server is running)
    otp_simulator = OTPRouteSimulator()
    
    # Generate trips
    trip_generator = DeckGLTripGenerator(otp_simulator)
    trips = trip_generator.generate_trips_from_survey(survey_responses)
    
    # Save visualization data
    json_output = trip_generator.save_deckgl_data("outputs/bgu_trips_data.json")
    
    # Create HTML with embedded data (no CORS issues)
    metadata = {
        'total_trips': len(trips),
        'generated_at': datetime.now().isoformat(),
        'bounds': trip_generator._calculate_bounds(),
        'description': 'BGU Mobility Survey - Simulated Walking Routes to University Gates'
    }
    
    # Debug logging for data structure
    logger.info(f"📊 DEBUG: Sample trip structure:")
    if trips:
        sample_trip = trips[0]
        logger.info(f"   - Trip keys: {list(sample_trip.keys())}")
        logger.info(f"   - Path length: {len(sample_trip.get('path', []))}")
        logger.info(f"   - Metadata keys: {list(sample_trip.get('metadata', {}).keys())}")
        logger.info(f"   - Transportation mode: {sample_trip.get('metadata', {}).get('transportation_mode', 'N/A')}")
        logger.info(f"   - First path point: {sample_trip.get('path', [[0,0,0,0]])[0]}")
    
    logger.info(f"📊 DEBUG: Metadata structure:")
    logger.info(f"   - Keys: {list(metadata.keys())}")
    logger.info(f"   - Bounds: {metadata.get('bounds', {})}")
    
    html_output = create_html_visualization_integrated(trips, metadata, "outputs/bgu_trips_visualization.html")
    
    logger.info(f"✅ Trip route visualization complete!")
    logger.info(f"   📊 Data: {json_output}")
    logger.info(f"   🗺️  Map: {html_output}")
    logger.info(f"   🏃 Generated {len(trips)} simulated walking routes")
    
    # Print summary statistics
    with_poi_stops = sum(1 for trip in trips if trip['metadata']['has_poi_stop'])
    avg_distance = np.mean([trip['metadata']['distance_km'] for trip in trips])
    avg_duration = np.mean([trip['metadata']['duration_minutes'] for trip in trips])
    
    logger.info(f"   📈 Statistics:")
    logger.info(f"      - Routes with POI stops: {with_poi_stops}/{len(trips)} ({with_poi_stops/len(trips)*100:.1f}%)")
    logger.info(f"      - POI constraint: max +2km additional distance")
    logger.info(f"      - Average distance: {avg_distance:.2f} km")
    logger.info(f"      - Average duration: {avg_duration:.1f} minutes")
    
    # Additional debugging information
    logger.info(f"🔍 DEBUG: File locations:")
    logger.info(f"   - JSON output exists: {os.path.exists(json_output)}")
    logger.info(f"   - HTML output exists: {os.path.exists(html_output)}")
    if os.path.exists(html_output):
        with open(html_output, 'r') as f:
            content = f.read()
            logger.info(f"   - HTML file size: {len(content)} characters")
            logger.info(f"   - Contains 'deck.gl': {'deck.gl' in content}")
            logger.info(f"   - Contains '@deck.gl/carto': {'@deck.gl/carto' in content}")
            logger.info(f"   - Contains trip data: {'tripsData' in content}")
    
    logger.info("🚀 Open the HTML file in your browser to view the visualization!")
    logger.info("📊 Debug logs are available in the browser console (F12 → Console tab).")

if __name__ == "__main__":
    main()