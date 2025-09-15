#!/usr/bin/env python3
"""
BGU Mobility Survey - Unified Data Manager
Consolidated data loading, processing, and validation for all survey analysis.
"""

import pandas as pd
import json
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
import logging
from dataclasses import dataclass
from datetime import datetime

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

    def distance_to(self, other: "Coordinate") -> float:
        """Calculate distance in kilometers using Haversine formula"""
        assert isinstance(
            other, Coordinate
        ), "Distance calculation requires Coordinate object"

        from math import radians, cos, sin, asin, sqrt

        lat1, lon1, lat2, lon2 = map(
            radians, [self.lat, self.lon, other.lat, other.lon]
        )
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        return 2 * asin(sqrt(a)) * 6371  # Earth radius in km


class BGUGateData:
    """BGU University gate/entrance data"""

    GATES = {
        "uni_south_3": Coordinate(31.261222, 34.801138, "South Gate 3"),
        "uni_north_3": Coordinate(31.263911, 34.799290, "North Gate 3"),
        "uni_west": Coordinate(31.262500, 34.805528, "West Gate"),
    }

    @classmethod
    def find_closest_gate(cls, residence: Coordinate) -> Tuple[str, Coordinate]:
        """Find closest university gate to residence"""
        assert isinstance(residence, Coordinate), "Residence must be Coordinate object"

        closest_gate = None
        closest_distance = float("inf")
        closest_name = None

        for gate_name, gate_coord in cls.GATES.items():
            distance = residence.distance_to(gate_coord)
            if distance < closest_distance:
                closest_distance = distance
                closest_gate = gate_coord
                closest_name = gate_name

        assert closest_gate is not None, "No closest gate found"
        return closest_name, closest_gate


class DataManager:
    """Unified data management with caching and validation."""

    # Data paths
    RAW_DATA_PATH = "data/mobility-data.csv"
    PROCESSED_DATA_PATH = "data/processed_mobility_data.csv"
    MOBILITY_JSON_PATH = "outputs/bgu_mobility_data.json"
    OUTPUTS_DIR = "outputs"

    # Transportation mode mappings
    TRANSPORT_MODE_MAPPING = {
        "ברגל": "walking",
        "אופניים": "bicycle",
        "אופניים/קורקינט חשמלי": "ebike",
        "אופניים חשמליים/קורקינט": "ebike",
        "רכב": "car",
        "אוטובוס": "bus",
        "רכבת": "train",
        "רכיבה על סוסים": "horseback",
        "אחר": "other",
    }

    # Route choice factors
    ROUTE_CHOICE_FACTORS = {
        "Routechoice-Distance": "Distance",
        "Routechoice-Time": "Time",
        "Routechoice-Shadow": "Shade",
        "Routechoice-Stores": "Stores",
        "Routechoice-Friends": "Friends",
        "Routechoice-Convenience": "Convenience",
        "Routechoice-Work": "Work",
    }

    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self._ensure_outputs_dir()

    def _ensure_outputs_dir(self):
        """Ensure outputs directory exists"""
        Path(self.OUTPUTS_DIR).mkdir(exist_ok=True)

    def load_raw_data(self) -> pd.DataFrame:
        """Load raw survey data with validation."""
        cache_key = "raw_data"

        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            df = pd.read_csv(self.RAW_DATA_PATH)
            logger.info(f"✓ Loaded raw data: {df.shape[0]} rows, {df.shape[1]} columns")

            # Basic validation
            assert df.shape[0] > 0, "Dataset cannot be empty"
            assert "Submission ID" in df.columns, "Missing Submission ID column"
            assert (
                "Submission Completed" in df.columns
            ), "Missing completion status column"

            self._cache[cache_key] = df
            return df

        except FileNotFoundError:
            logger.error(f"Raw data file not found: {self.RAW_DATA_PATH}")
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"Error loading raw data: {e}")
            return pd.DataFrame()

    def load_processed_data(self) -> pd.DataFrame:
        """Load processed survey data with fallback to raw data."""
        cache_key = "processed_data"

        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            df = pd.read_csv(self.PROCESSED_DATA_PATH)
            logger.info(f"✓ Loaded processed data: {df.shape[0]} rows")
            self._cache[cache_key] = df
            return df

        except FileNotFoundError:
            logger.warning(
                "⚠️  Processed data not found, loading and processing raw data..."
            )
            df = self.load_raw_data()
            if not df.empty:
                df = self.process_raw_data(df)
                self._cache[cache_key] = df
            return df

    def process_raw_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Process raw data into clean format."""
        df_processed = df.copy()

        # Merge binary questions
        df_processed = self._merge_binary_questions(df_processed)

        # Clean transportation modes
        df_processed = self._clean_transportation_modes(df_processed)

        # Validate coordinate data
        df_processed = self._validate_coordinate_data(df_processed)

        # Save processed data
        df_processed.to_csv(self.PROCESSED_DATA_PATH, index=False)
        logger.info(f"✓ Processed data saved to: {self.PROCESSED_DATA_PATH}")

        return df_processed

    def _merge_binary_questions(self, df: pd.DataFrame) -> pd.DataFrame:
        """Merge split binary questions into single variables."""
        df_merged = df.copy()

        # Merge further study interest
        if "Further-yes" in df.columns or "Further-no" in df.columns:
            df_merged["Further_Study_Interest"] = "No Response"
            if "Further-yes" in df.columns:
                df_merged.loc[
                    df_merged["Further-yes"].notna(), "Further_Study_Interest"
                ] = "Yes"
            if "Further-no" in df.columns:
                df_merged.loc[
                    df_merged["Further-no"].notna(), "Further_Study_Interest"
                ] = "No"

        # Merge week tracking interest
        if any(col.startswith("FurtherWeek-") for col in df.columns):
            df_merged["Week_Tracking_Interest"] = "No Response"
            if "FurtherWeek-yes" in df.columns:
                df_merged.loc[
                    df_merged["FurtherWeek-yes"].notna(), "Week_Tracking_Interest"
                ] = "Yes"
            if "FurtherWeek-no" in df.columns:
                df_merged.loc[
                    df_merged["FurtherWeek-no"].notna(), "Week_Tracking_Interest"
                ] = "No"
            if "FurtherWeek-other" in df.columns:
                df_merged.loc[
                    df_merged["FurtherWeek-other"].notna(), "Week_Tracking_Interest"
                ] = "Other"

        return df_merged

    def _clean_transportation_modes(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and standardize transportation mode data."""
        df_clean = df.copy()

        if "Transportation-Mode" in df.columns:
            # Map Hebrew modes to English
            df_clean["Transportation_Mode_English"] = df_clean[
                "Transportation-Mode"
            ].map(self.TRANSPORT_MODE_MAPPING)
            df_clean["Transportation_Mode_English"] = df_clean[
                "Transportation_Mode_English"
            ].fillna(df_clean["Transportation-Mode"])

        return df_clean

    def _validate_coordinate_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Validate coordinate data integrity."""
        # This could include coordinate validation logic
        # For now, just return the dataframe
        return df

    def get_transportation_modes(self) -> Dict[str, int]:
        """Get transportation mode distribution."""
        df = self.load_processed_data()

        if df.empty or "Transportation-Mode" not in df.columns:
            return {}

        # Count modes using English mapping
        mode_counts = {}
        for mode in df["Transportation-Mode"].dropna():
            english_mode = self.TRANSPORT_MODE_MAPPING.get(mode, "unknown")
            mode_counts[english_mode] = mode_counts.get(english_mode, 0) + 1

        return mode_counts

    def get_participation_data(self) -> Dict[str, Any]:
        """Get participation interest data from completed surveys only."""
        df = self.load_processed_data()

        if df.empty:
            return {}

        # Filter only completed surveys
        completed_df = df[df["Submission Completed"] == True]

        if len(completed_df) == 0:
            return {}

        participation_data = {}

        # Further study interest
        if "Further_Study_Interest" in completed_df.columns:
            study_counts = (
                completed_df["Further_Study_Interest"].value_counts().to_dict()
            )
            participation_data["further_study"] = {
                "counts": study_counts,
                "total": len(completed_df),
                "percentages": {
                    k: (v / len(completed_df) * 100) for k, v in study_counts.items()
                },
            }

        # Week tracking interest
        if "Week_Tracking_Interest" in completed_df.columns:
            week_counts = (
                completed_df["Week_Tracking_Interest"].value_counts().to_dict()
            )
            participation_data["week_tracking"] = {
                "counts": week_counts,
                "total": len(completed_df),
                "percentages": {
                    k: (v / len(completed_df) * 100) for k, v in week_counts.items()
                },
            }

        return participation_data

    def get_route_choice_data(self) -> Dict[str, Any]:
        """Get route choice factor analysis data."""
        df = self.load_processed_data()

        if df.empty:
            return {}

        factor_stats = {}

        for factor_col, factor_name in self.ROUTE_CHOICE_FACTORS.items():
            if factor_col in df.columns:
                valid_responses = pd.to_numeric(
                    df[factor_col], errors="coerce"
                ).dropna()

                if len(valid_responses) > 0:
                    factor_stats[factor_name] = {
                        "count": len(valid_responses),
                        "mean": float(valid_responses.mean()),
                        "std": float(valid_responses.std()),
                        "value_counts": valid_responses.value_counts()
                        .sort_index()
                        .to_dict(),
                    }

        return factor_stats

    def parse_coordinates(self, coord_string: str) -> List[Dict]:
        """Parse coordinate strings from JSON format."""
        if pd.isna(coord_string) or coord_string == "":
            return []

        try:
            coord_data = json.loads(coord_string)
            coordinates = []

            for item in coord_data:
                if "coordinate" in item:
                    coord_str = item["coordinate"]
                    comment = item.get("comment", "").strip()
                    lat, lng = map(float, coord_str.split(","))

                    # Validate coordinates are in Israel bounds
                    if 29.5 <= lat <= 33.3 and 34.2 <= lng <= 35.9:
                        coordinates.append(
                            {
                                "lat": lat,
                                "lng": lng,
                                "comment": (
                                    comment if comment else "No comment provided"
                                ),
                            }
                        )

            return coordinates
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.warning(f"Error parsing coordinates: {e}")
            return []

    def get_poi_data(self) -> List[Dict]:
        """Extract all POI points with metadata."""
        df = self.load_processed_data()

        if df.empty or "POI" not in df.columns:
            return []

        poi_data = df[df["POI"].notna()]["POI"].copy()
        submission_ids = df[df["POI"].notna()]["Submission ID"].copy()

        all_pois = []

        for submission_id, poi_string in zip(submission_ids, poi_data):
            coordinates = self.parse_coordinates(poi_string)

            for i, coord in enumerate(coordinates):
                all_pois.append(
                    {
                        "id": f"{submission_id}_{i}",
                        "submissionId": submission_id,
                        "lat": coord["lat"],
                        "lng": coord["lng"],
                        "comment": coord["comment"],
                        "hasComment": len(coord["comment"]) > 0
                        and coord["comment"] != "No comment provided",
                    }
                )

        logger.info(f"✓ Extracted {len(all_pois)} POI points")
        return all_pois

    def get_completion_stats(self) -> Dict[str, Any]:
        """Get survey completion statistics."""
        df = self.load_processed_data()

        if df.empty:
            return {}

        completion_stats = {
            "total_submissions": len(df),
            "completed_count": len(df[df["Submission Completed"] == True]),
            "incomplete_count": len(df[df["Submission Completed"] == False]),
            "completion_rate": len(df[df["Submission Completed"] == True])
            / len(df)
            * 100,
        }

        return completion_stats

    def get_gate_distribution(self) -> Dict[str, Any]:
        """Get BGU gate usage distribution."""
        df = self.load_processed_data()

        if df.empty or "Residence-Info" not in df.columns:
            return {}

        gate_usage = {}

        for idx, row in df.iterrows():
            if pd.isna(row["Residence-Info"]):
                continue

            residences = self.parse_coordinates(row["Residence-Info"])
            if not residences:
                continue

            residence = residences[0]  # Use first residence
            residence_coord = Coordinate(residence["lat"], residence["lng"])

            # Find closest gate
            closest_gate_name, closest_gate = BGUGateData.find_closest_gate(
                residence_coord
            )

            # Extract gate name from ID
            gate_name = closest_gate.comment
            gate_usage[gate_name] = gate_usage.get(gate_name, 0) + 1

        return gate_usage

    def load_mobility_json(self) -> Dict[str, Any]:
        """Load exported mobility data JSON."""
        cache_key = "mobility_json"

        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            with open(self.MOBILITY_JSON_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            logger.info(f"✓ Loaded mobility JSON data")
            self._cache[cache_key] = data
            return data

        except FileNotFoundError:
            logger.warning("⚠️  Mobility JSON data not found")
            return {}

    def get_route_distances(self) -> Dict[str, float]:
        """Extract route distance statistics from mobility data."""
        data = self.load_mobility_json()

        if not data or "routes" not in data:
            return {
                "distances": [],
                "avg_distance": 0.0,
                "median_distance": 0.0,
                "std_distance": 0.0,
            }

        routes = data["routes"]
        distances = [route["distance"] for route in routes if "distance" in route]

        if not distances:
            return {
                "distances": [],
                "avg_distance": 0.0,
                "median_distance": 0.0,
                "std_distance": 0.0,
            }

        return {
            "distances": distances,
            "avg_distance": float(np.mean(distances)),
            "median_distance": float(np.median(distances)),
            "std_distance": float(np.std(distances)),
        }

    def clear_cache(self):
        """Clear the data cache."""
        self._cache.clear()
        logger.info("✓ Data cache cleared")

    def get_summary_stats(self) -> Dict[str, Any]:
        """Get comprehensive summary statistics."""
        df = self.load_processed_data()

        if df.empty:
            return {}

        stats = {
            "data_summary": {
                "total_rows": len(df),
                "total_columns": len(df.columns),
                "completion_rate": self.get_completion_stats().get(
                    "completion_rate", 0
                ),
            },
            "transportation_modes": self.get_transportation_modes(),
            "participation": self.get_participation_data(),
            "route_choice": self.get_route_choice_data(),
            "gate_distribution": self.get_gate_distribution(),
            "poi_count": len(self.get_poi_data()),
            "route_distances": self.get_route_distances(),
        }

        return stats


# Global data manager instance
data_manager = DataManager()
