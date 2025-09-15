ata s cleangone"""
Data loading and validation utilities for BGU Mobility Survey.
"""

import pandas as pd
import json
import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import logging

from .config import config

logger = logging.getLogger(__name__)


class DataLoader:
    """Centralized data loading with validation and caching."""

    def __init__(self):
        self._cache: Dict[str, Any] = {}

    def load_processed_data(self) -> pd.DataFrame:
        """Load processed survey data with fallback to raw data."""
        cache_key = "processed_data"

        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            df = pd.read_csv(config.paths.processed_data)
            logger.info(f"✓ Loaded processed data: {df.shape[0]} rows")
            self._cache[cache_key] = df
            return df

        except FileNotFoundError:
            logger.warning("⚠️  Processed data not found, loading raw data...")
            df = pd.read_csv(config.paths.raw_data)

            # Apply basic preprocessing if needed
            df = self._apply_basic_preprocessing(df)
            self._cache[cache_key] = df
            return df

    def load_mobility_json(self) -> Dict[str, Any]:
        """Load exported mobility data JSON."""
        cache_key = "mobility_json"

        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            with open(config.paths.mobility_json, "r", encoding="utf-8") as f:
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

    def get_transport_modes(self) -> Dict[str, int]:
        """Extract transportation mode data."""
        data = self.load_mobility_json()

        if "statistics" in data and "transportModes" in data["statistics"]:
            return data["statistics"]["transportModes"]

        # Fallback: calculate from raw data
        df = self.load_processed_data()
        return self._calculate_transport_modes(df)

    def _apply_basic_preprocessing(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply basic preprocessing to raw data."""
        # Handle future study interest columns
        if "Further-yes" in df.columns or "Further-no" in df.columns:
            df["Further_Study_Interest"] = "No Response"
            if "Further-yes" in df.columns:
                df.loc[df["Further-yes"].notna(), "Further_Study_Interest"] = "Yes"
            if "Further-no" in df.columns:
                df.loc[df["Further-no"].notna(), "Further_Study_Interest"] = "No"

        # Handle week tracking interest columns
        if any(col.startswith("FurtherWeek-") for col in df.columns):
            df["Week_Tracking_Interest"] = "No Response"
            if "FurtherWeek-yes" in df.columns:
                df.loc[df["FurtherWeek-yes"].notna(), "Week_Tracking_Interest"] = "Yes"
            if "FurtherWeek-no" in df.columns:
                df.loc[df["FurtherWeek-no"].notna(), "Week_Tracking_Interest"] = "No"
            if "FurtherWeek-other" in df.columns:
                df.loc[df["FurtherWeek-other"].notna(), "Week_Tracking_Interest"] = (
                    "Other"
                )

        return df

    def _calculate_transport_modes(self, df: pd.DataFrame) -> Dict[str, int]:
        """Calculate transport modes from raw data."""
        mode_translation = {
            "ברגל": "walking",
            "אופניים": "bicycle",
            "אופניים/קורקינט חשמלי": "ebike",
            "רכב": "car",
            "אוטובוס": "bus",
            "רכבת": "train",
        }

        mode_counts = {
            "walking": 0,
            "bicycle": 0,
            "ebike": 0,
            "car": 0,
            "bus": 0,
            "train": 0,
            "unknown": 0,
        }

        transport_col = "Transportation-Mode"
        if transport_col not in df.columns:
            return mode_counts

        for mode in df[transport_col].dropna():
            mode_en = mode_translation.get(mode, "unknown")
            mode_counts[mode_en] += 1

        return mode_counts

    def clear_cache(self):
        """Clear the data cache."""
        self._cache.clear()


# Global data loader instance
data_loader = DataLoader()
