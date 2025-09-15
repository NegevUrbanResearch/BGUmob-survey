#!/usr/bin/env python3
"""
BGU Mobility Survey - Route Simulation Module
Handles OpenTripPlanner integration for route generation.
"""

import requests
import time
import logging
import polyline
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

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


class OTPRouteSimulator:
    """Simulate routes using OpenTripPlanner server"""

    def __init__(
        self,
        base_url: str = "http://localhost:8080/otp/routers/default",
        max_retries: int = 5,
        retry_delay: float = 0.1,
    ):
        self.base_url = base_url
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    def get_walking_route(
        self,
        origin: Coordinate,
        destination: Coordinate,
        intermediate_stop: Optional[Coordinate] = None,
        transportation_mode: str = "WALK",
    ) -> Optional[Dict]:
        """Get route from OTP server with retry logic and small location variations"""
        assert isinstance(origin, Coordinate), "Origin must be Coordinate"
        assert isinstance(destination, Coordinate), "Destination must be Coordinate"

        # Try multiple small variations of the origin location if initial attempts fail
        variations = self._generate_location_variations(origin, num_variations=3)

        for attempt, origin_variant in enumerate(variations):
            if intermediate_stop:
                # Route via intermediate stop: origin -> stop -> destination
                route1 = self._query_otp_route_with_mode(
                    origin_variant, intermediate_stop, transportation_mode
                )
                if not route1:
                    continue

                route2 = self._query_otp_route_with_mode(
                    intermediate_stop, destination, transportation_mode
                )
                if not route2:
                    continue

                result = self._combine_routes(route1, route2, intermediate_stop)
                if result:
                    return result
            else:
                # Direct route
                result = self._query_otp_route_with_mode(
                    origin_variant, destination, transportation_mode
                )
                if result:
                    return result

        return None

    def _generate_location_variations(
        self, coord: Coordinate, num_variations: int = 3
    ) -> List[Coordinate]:
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
            "ברגל": "WALK",
            "אופניים": "BICYCLE",
            "אופניים/קורקינט חשמלי": "BICYCLE",
            "רכב": "CAR",
            "אוטובוס": "TRANSIT,WALK",
            "רכבת": "TRANSIT,WALK",
            "": "WALK",  # Default to walking
        }
        return mode_mapping.get(hebrew_mode, "WALK")

    def _query_otp_route_with_mode(
        self, origin: Coordinate, destination: Coordinate, transportation_mode: str
    ) -> Optional[Dict]:
        """Query OTP server for route with specific transportation mode"""
        otp_mode = self._map_transportation_mode(transportation_mode)

        params = {
            "fromPlace": f"{origin.lat},{origin.lon}",
            "toPlace": f"{destination.lat},{destination.lon}",
            "mode": otp_mode,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "time": "09:00:00",
            "arriveBy": "false",
            "walkSpeed": 1.4,  # m/s
            "maxWalkDistance": 10000,
            "locale": "en",
        }

        # Add mode-specific parameters
        if "BICYCLE" in otp_mode:
            params.update(
                {"bikeSpeed": 4.0, "bikeSwitchTime": 0, "bikeSwitchCost": 0}  # m/s
            )
        elif "CAR" in otp_mode:
            params.update({"carSpeed": 40.0, "maxCarDistance": 50000})  # km/h

        return self._query_otp_route_base(params)

    def _query_otp_route_base(self, params: Dict) -> Optional[Dict]:
        """Base OTP query method"""

        for attempt in range(self.max_retries):
            try:
                response = requests.get(
                    f"{self.base_url}/plan", params=params, timeout=10
                )

                if response.status_code == 200:
                    data = response.json()
                    if (
                        "plan" in data
                        and "itineraries" in data["plan"]
                        and data["plan"]["itineraries"]
                    ):
                        return data
                    else:
                        logger.debug(
                            f"OTP returned no itineraries for {params['fromPlace']} to {params['toPlace']}"
                        )
                        return None

                elif response.status_code == 429:  # Rate limited
                    wait_time = (attempt + 1) * self.retry_delay
                    logger.warning(f"Rate limited, waiting {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.warning(f"OTP request failed: {response.status_code}")

            except requests.exceptions.RequestException as e:
                logger.warning(f"OTP request error: {e}")

            if attempt < self.max_retries - 1:
                time.sleep((attempt + 1) * self.retry_delay)

        return None

    def _combine_routes(
        self, route1: Dict, route2: Dict, intermediate: Coordinate
    ) -> Dict:
        """Combine two route segments via intermediate stop"""
        try:
            leg1 = route1["plan"]["itineraries"][0]["legs"][0]
            leg2 = route2["plan"]["itineraries"][0]["legs"][0]

            points1 = polyline.decode(leg1["legGeometry"]["points"])
            points2 = polyline.decode(leg2["legGeometry"]["points"])

            # Combine points, skip first point of second segment to avoid duplication
            combined_points = points1 + points2[1:]

            return {
                "plan": {
                    "itineraries": [
                        {
                            "legs": [
                                {
                                    "legGeometry": {"points": combined_points},
                                    "duration": leg1["duration"] + leg2["duration"],
                                    "distance": leg1["distance"] + leg2["distance"],
                                }
                            ]
                        }
                    ]
                },
                "intermediate_stop": {
                    "lat": intermediate.lat,
                    "lon": intermediate.lon,
                    "comment": intermediate.comment,
                },
            }
        except (KeyError, IndexError) as e:
            logger.warning(f"Error combining routes: {e}")
            return None


class RouteGenerator:
    """High-level route generation with multiple retry strategies"""

    def __init__(self, otp_simulator: Optional[OTPRouteSimulator] = None):
        self.otp_simulator = otp_simulator or OTPRouteSimulator()

    def generate_route_path(
        self, residence: Dict, destination: Dict, pois: List[Dict], transport_mode: str
    ) -> Optional[List[List[float]]]:
        """Generate route path using OTP server with multiple retry attempts"""

        # Convert to Coordinate objects
        residence_coord = Coordinate(
            residence["lat"], residence["lng"], residence.get("comment", "")
        )
        destination_coord = Coordinate(
            destination["lat"], destination["lng"], destination.get("comment", "")
        )

        # Convert POIs to Coordinate objects
        poi_coords = [
            Coordinate(poi["lat"], poi["lng"], poi.get("comment", "")) for poi in pois
        ]

        # Select intermediate stop (use first POI if available)
        intermediate_stop = poi_coords[0] if poi_coords else None

        # Try multiple location variations for both origin and destination
        origin_variations = self._generate_location_variations(
            residence_coord, num_variations=5
        )
        dest_variations = self._generate_location_variations(
            destination_coord, num_variations=3
        )

        # Try different combinations of origin and destination variations
        for origin_var in origin_variations:
            for dest_var in dest_variations:
                # Generate route with OTP
                route_data = self.otp_simulator.get_walking_route(
                    origin_var, dest_var, intermediate_stop, transport_mode
                )

                if route_data:
                    try:
                        itinerary = route_data["plan"]["itineraries"][0]
                        leg = itinerary["legs"][0]

                        # Decode route points from polyline
                        if isinstance(leg["legGeometry"]["points"], str):
                            route_points = polyline.decode(leg["legGeometry"]["points"])
                        else:
                            route_points = leg["legGeometry"]["points"]

                        # Convert to [lng, lat] format for GeoJSON
                        return [[point[1], point[0]] for point in route_points]

                    except (KeyError, IndexError) as e:
                        continue  # Try next variation

        # If all attempts fail, return None to skip this route
        logger.warning(
            f"Could not generate OTP route for {residence['lat']:.6f},{residence['lng']:.6f} to {destination['lat']:.6f},{destination['lng']:.6f}"
        )
        return None

    def _generate_location_variations(
        self, coord: Coordinate, num_variations: int = 5
    ) -> List[Coordinate]:
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


# Global route generator instance
route_generator = RouteGenerator()
