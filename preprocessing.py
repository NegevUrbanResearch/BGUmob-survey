#!/usr/bin/env python3
"""
BGU Mobility Survey - Data Exploration and Validation
This script performs initial data exploration and validation of the survey responses.
"""

import pandas as pd
import numpy as np
import json
import re
from typing import Dict, List, Tuple, Any

def load_and_validate_data(file_path: str) -> pd.DataFrame:
    """Load CSV data and perform basic validation."""
    assert file_path.endswith('.csv'), "File must be a CSV"
    
    df = pd.read_csv(file_path)
    print(f"✓ Loaded data: {df.shape[0]} rows, {df.shape[1]} columns")
    
    # Basic validation
    assert df.shape[0] > 0, "Dataset cannot be empty"
    assert 'Submission ID' in df.columns, "Missing Submission ID column"
    assert 'Submission Completed' in df.columns, "Missing completion status column"
    
    return df

def analyze_completion_rates(df: pd.DataFrame) -> Dict[str, Any]:
    """Analyze survey completion patterns."""
    completion_stats = {
        'total_submissions': len(df),
        'completed_count': len(df[df['Submission Completed'] == True]),
        'incomplete_count': len(df[df['Submission Completed'] == False]),
        'completion_rate': len(df[df['Submission Completed'] == True]) / len(df) * 100
    }
    
    print(f"\n📊 COMPLETION ANALYSIS:")
    print(f"Total submissions: {completion_stats['total_submissions']}")
    print(f"Completed surveys: {completion_stats['completed_count']}")
    print(f"Incomplete surveys: {completion_stats['incomplete_count']}")
    print(f"Completion rate: {completion_stats['completion_rate']:.1f}%")
    
    return completion_stats

def validate_transportation_modes(df: pd.DataFrame) -> None:
    """Validate transportation mode data."""
    transport_col = 'Transportation-Mode'
    if transport_col in df.columns:
        valid_modes = df[transport_col].dropna()
        print(f"\n🚶 TRANSPORTATION MODES:")
        print(f"Valid responses: {len(valid_modes)}")
        
        # Expected Hebrew values mapping
        mode_mapping = {
            'ברגל': 'Walking',
            'אופניים חשמליים/קורקינט': 'Electric Bicycle/Scooter', 
            'רכב': 'Car',
            'אופניים': 'Bicycle',
            'אוטובוס': 'Bus',
            'רכיבה על סוסים': 'Horseback riding',
            'אחר': 'Other'
        }
        
        unique_modes = valid_modes.unique()
        print(f"Unique values found: {unique_modes}")
        
        for mode in unique_modes:
            count = (valid_modes == mode).sum()
            english_name = mode_mapping.get(mode, mode)
            print(f"  {mode} ({english_name}): {count}")

def parse_coordinates(coord_string: str) -> List[Tuple[float, float]]:
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
                # Split lat,lng
                lat, lng = map(float, coord_str.split(','))
                coordinates.append((lat, lng))
                
        return coordinates
    except (json.JSONDecodeError, ValueError, KeyError) as e:
        print(f"⚠️  Error parsing coordinates: {coord_string[:50]}... - {e}")
        return []

def analyze_poi_data(df: pd.DataFrame) -> Dict[str, Any]:
    """Analyze Points of Interest data."""
    poi_col = 'POI'
    if poi_col not in df.columns:
        return {}
    
    poi_data = df[poi_col].dropna()
    print(f"\n📍 POINTS OF INTEREST:")
    print(f"Responses with POI data: {len(poi_data)}")
    
    total_pois = 0
    valid_coordinates = 0
    
    for poi_string in poi_data:
        coordinates = parse_coordinates(poi_string)
        total_pois += len(coordinates)
        valid_coordinates += len([c for c in coordinates if c[0] != 0 and c[1] != 0])
    
    print(f"Total POI points: {total_pois}")
    print(f"Valid coordinates: {valid_coordinates}")
    
    return {
        'responses_with_poi': len(poi_data),
        'total_pois': total_pois,
        'valid_coordinates': valid_coordinates
    }

def analyze_route_choice_factors(df: pd.DataFrame) -> Dict[str, Any]:
    """Analyze route choice factor rankings."""
    route_factors = [
        'Routechoice-Distance', 'Routechoice-Time', 'Routechoice-Shadow',
        'Routechoice-Stores', 'Routechoice-Friends', 'Routechoice-Convenience',
        'Routechoice-Work'
    ]
    
    print(f"\n🛣️  ROUTE CHOICE FACTORS:")
    factor_stats = {}
    
    for factor in route_factors:
        if factor in df.columns:
            valid_responses = df[factor].dropna()
            if len(valid_responses) > 0:
                try:
                    # Convert to numeric, handling any non-numeric values
                    numeric_responses = pd.to_numeric(valid_responses, errors='coerce').dropna()
                    factor_stats[factor] = {
                        'count': len(numeric_responses),
                        'mean': numeric_responses.mean(),
                        'std': numeric_responses.std(),
                        'value_counts': numeric_responses.value_counts().sort_index().to_dict()
                    }
                    print(f"  {factor}: {len(numeric_responses)} responses, mean={numeric_responses.mean():.2f}")
                except:
                    print(f"  {factor}: Error processing numeric data")
    
    return factor_stats

def merge_binary_questions(df: pd.DataFrame) -> pd.DataFrame:
    """Merge split binary questions into single variables."""
    df_merged = df.copy()
    
    # Merge further study interest
    df_merged['Further_Study_Interest'] = 'No Response'
    df_merged.loc[df_merged['Further-yes'].notna(), 'Further_Study_Interest'] = 'Yes'
    df_merged.loc[df_merged['Further-no'].notna(), 'Further_Study_Interest'] = 'No'
    
    # Merge week tracking interest  
    df_merged['Week_Tracking_Interest'] = 'No Response'
    df_merged.loc[df_merged['FurtherWeek-yes'].notna(), 'Week_Tracking_Interest'] = 'Yes'
    df_merged.loc[df_merged['FurtherWeek-no'].notna(), 'Week_Tracking_Interest'] = 'No'
    df_merged.loc[df_merged['FurtherWeek-other'].notna(), 'Week_Tracking_Interest'] = 'Other'
    
    print(f"\n🔄 MERGED BINARY QUESTIONS:")
    print("Further Study Interest:")
    print(df_merged['Further_Study_Interest'].value_counts())
    print("\nWeek Tracking Interest:")
    print(df_merged['Week_Tracking_Interest'].value_counts())
    df_merged.drop(columns=['Further-yes', 'Further-no', 'FurtherWeek-yes', 'FurtherWeek-no', 'FurtherWeek-other'], inplace=True)
    
    return df_merged

def analyze_text_responses(df: pd.DataFrame) -> None:
    """Analyze open-text response fields."""
    text_fields = ['Challenges', 'Suggestions']
    
    print(f"\n📝 TEXT RESPONSES:")
    for field in text_fields:
        if field in df.columns:
            valid_responses = df[field].dropna()
            if len(valid_responses) > 0:
                avg_length = valid_responses.str.len().mean()
                print(f"  {field}: {len(valid_responses)} responses, avg length: {avg_length:.1f} chars")
                
                # Show a few examples
                print(f"    Examples:")
                for i, response in enumerate(valid_responses.head(3)):
                    print(f"      {i+1}. {response[:100]}{'...' if len(response) > 100 else ''}")

def main():
    """Main data exploration pipeline."""
    print("🔍 BGU Mobility Survey - Data Exploration")
    print("=" * 50)
    
    # Load and validate data
    df = load_and_validate_data('data/mobility-data.csv')
    
    # Analyze completion rates
    completion_stats = analyze_completion_rates(df)
    
    # Validate transportation modes
    validate_transportation_modes(df)
    
    # Analyze POI data
    poi_stats = analyze_poi_data(df)
    
    # Analyze route choice factors
    route_stats = analyze_route_choice_factors(df)
    
    # Merge binary questions
    df_merged = merge_binary_questions(df)
    
    # Analyze text responses
    analyze_text_responses(df)
    
    print(f"\n✅ Data exploration completed successfully!")
    
    # Save processed data
    df_merged.to_csv('data/processed_mobility_data.csv', index=False)
    print(f"💾 Processed data saved to: data/processed_mobility_data.csv")

if __name__ == "__main__":
    main() 