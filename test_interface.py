#!/usr/bin/env python3
"""
BGU Mobility Survey - Interface Test Suite
Comprehensive testing for data export and web interface
"""

import json
import os
import sys
import webbrowser
from pathlib import Path
import pandas as pd
import numpy as np

def test_data_export():
    """Test that all exported JSON files are valid and contain expected data"""
    print("🧪 Testing Data Export...")
    
    required_files = [
        'outputs/bgu_mobility_data.json',
        'outputs/pois.json', 
        'outputs/routes.json',
        'outputs/statistics.json'
    ]
    
    for file_path in required_files:
        if not os.path.exists(file_path):
            print(f"❌ Missing required file: {file_path}")
            return False
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            print(f"✓ {file_path} - Valid JSON")
        except json.JSONDecodeError as e:
            print(f"❌ {file_path} - Invalid JSON: {e}")
            return False
        except Exception as e:
            print(f"❌ {file_path} - Error reading file: {e}")
            return False
    
    return True

def test_web_interface():
    """Test that web interface files exist and are accessible"""
    print("\n🌐 Testing Web Interface...")
    
    required_files = [
        'index.html',
        'assets/js/map-controller.js',
        'assets/css/dashboard.css'
    ]
    
    for file_path in required_files:
        if not os.path.exists(file_path):
            print(f"❌ Missing required file: {file_path}")
            return False
        else:
            print(f"✓ {file_path} - Found")
    
    return True

def test_data_integrity():
    """Test data integrity and structure"""
    print("\n📊 Testing Data Integrity...")
    
    try:
        # Load main data file
        with open('outputs/bgu_mobility_data.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Check required top-level keys
        required_keys = ['metadata', 'statistics', 'pois', 'routes']
        for key in required_keys:
            if key not in data:
                print(f"❌ Missing required key: {key}")
                return False
        
        # Check POI structure
        pois = data['pois']
        if not isinstance(pois, list):
            print("❌ POIs should be a list")
            return False
        
        for poi in pois:
            required_poi_keys = ['id', 'lat', 'lng', 'comment', 'hasComment']
            for key in required_poi_keys:
                if key not in poi:
                    print(f"❌ POI missing required key: {key}")
                    return False
        
        # Check route structure
        routes = data['routes']
        if not isinstance(routes, list):
            print("❌ Routes should be a list")
            return False
        
        for route in routes:
            required_route_keys = ['id', 'residence', 'destination', 'pois', 'routePath', 'transportMode', 'originalMode', 'poiCount', 'distance']
            for key in required_route_keys:
                if key not in route:
                    print(f"❌ Route missing required key: {key}")
                    return False
        
        print(f"✓ Data integrity check passed: {len(pois)} POIs, {len(routes)} routes")
        return True
        
    except Exception as e:
        print(f"❌ Data integrity test failed: {e}")
        return False

def test_nan_values():
    """Test for NaN values in JSON data that could cause parsing errors"""
    print("\n🔍 Testing for NaN Values...")
    
    try:
        # Check routes.json specifically for NaN values
        with open('outputs/routes.json', 'r', encoding='utf-8') as f:
            content = f.read()
        
        if 'NaN' in content:
            print("❌ Found 'NaN' values in routes.json - this will cause JSON parsing errors!")
            return False
        
        # Check all JSON files for NaN
        json_files = [
            'outputs/bgu_mobility_data.json',
            'outputs/pois.json',
            'outputs/routes.json',
            'outputs/statistics.json'
        ]
        
        for file_path in json_files:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            if 'NaN' in content:
                print(f"❌ Found 'NaN' values in {file_path}")
                return False
        
        print("✓ No NaN values found in JSON files")
        return True
        
    except Exception as e:
        print(f"❌ NaN test failed: {e}")
        return False

def test_statistics():
    """Test that statistics are reasonable"""
    print("\n📈 Testing Statistics...")
    
    try:
        with open('outputs/statistics.json', 'r', encoding='utf-8') as f:
            stats = json.load(f)
        
        # Check basic statistics
        if stats['totalPois'] <= 0:
            print("❌ Total POIs should be > 0")
            return False
        
        if stats['totalRoutes'] <= 0:
            print("❌ Total routes should be > 0")
            return False
        
        if stats['averageDistance'] < 0:
            print("❌ Average distance should be >= 0")
            return False
        
        print(f"✓ Statistics look good: {stats['totalPois']} POIs, {stats['totalRoutes']} routes")
        return True
        
    except Exception as e:
        print(f"❌ Statistics test failed: {e}")
        return False

def test_maplibre_compatibility():
    """Test that the JavaScript code is compatible with MapLibre"""
    print("\n🗺️ Testing MapLibre Compatibility...")
    
    try:
        with open('assets/js/map-controller.js', 'r', encoding='utf-8') as f:
            js_content = f.read()
        
        # Check for MapLibre usage
        if 'maplibregl' not in js_content:
            print("❌ MapLibre not found in JavaScript code")
            return False
        
        # Check for Mapbox references (should be removed)
        if 'mapboxgl' in js_content:
            print("❌ Found Mapbox references - should be using MapLibre")
            return False
        
        # Check for glyphs configuration (optional when using pre-built styles)
        if 'glyphs' not in js_content and 'style.json' not in js_content:
            print("❌ Missing glyphs configuration for MapLibre")
            return False
        
        print("✓ MapLibre compatibility check passed")
        return True
        
    except Exception as e:
        print(f"❌ MapLibre compatibility test failed: {e}")
        return False

def launch_interface():
    """Launch the web interface using Python's HTTP server"""
    print("\n🚀 Launching Web Interface...")
    
    try:
        # Start HTTP server in background
        import subprocess
        import time
        
        # Start server in background
        server_process = subprocess.Popen(
            ['python', '-m', 'http.server', '8000'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        # Wait a moment for server to start
        time.sleep(1)
        
        # Open in browser
        webbrowser.open('http://localhost:8000')
        print("✓ Interface launched: http://localhost:8000")
        print("   Server running in background. Press Ctrl+C to stop.")
        return True
    except Exception as e:
        print(f"❌ Failed to launch interface: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 BGU Mobility Survey Interface Test Suite")
    print("=" * 50)
    
    tests = [
        test_data_export,
        test_web_interface,
        test_data_integrity,
        test_nan_values,
        test_statistics,
        test_maplibre_compatibility
    ]
    
    all_passed = True
    for test in tests:
        if not test():
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 All tests passed! Interface is ready to use.")
        launch_interface()
    else:
        print("❌ Some tests failed. Please fix the issues above.")
        sys.exit(1)

if __name__ == "__main__":
    main() 