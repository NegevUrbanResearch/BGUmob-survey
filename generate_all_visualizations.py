#!/usr/bin/env python3
"""
BGU Mobility Survey - Master Visualization Generator
Generates all visualization modules for the web application.
"""

import os
import sys
import subprocess
from datetime import datetime

def run_script(script_name: str, description: str) -> bool:
    """Run a Python script and return success status."""
    print(f"\n🔄 {description}")
    print("-" * 50)
    
    try:
        result = subprocess.run([sys.executable, script_name], 
                              capture_output=True, text=True, check=True)
        print(result.stdout)
        if result.stderr:
            print(f"⚠️  Warnings: {result.stderr}")
        print(f"✅ {description} completed successfully!")
        return True
    
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed!")
        print(f"Error: {e}")
        if e.stdout:
            print(f"Output: {e.stdout}")
        if e.stderr:
            print(f"Error details: {e.stderr}")
        return False
    
    except FileNotFoundError:
        print(f"❌ Script {script_name} not found!")
        return False

def main():
    """Generate all visualizations for the BGU Mobility Survey app."""
    print("🎯 BGU Mobility Survey - Master Visualization Generator")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Ensure outputs directory exists
    os.makedirs('outputs', exist_ok=True)
    
    # List of visualizations to generate
    visualizations = [
        ("viz_gate_distribution.py", "Gate Distribution Pie Chart"),
        ("viz_transport_donut.py", "Transportation Modes Donut Chart"),
        ("viz_distance_comparison.py", "Distance Comparison Analysis"),
        ("viz_route_choice.py", "Route Choice Factors (Spider & Bar Charts)")
    ]
    
    # Track success/failure
    results = {}
    
    for script, description in visualizations:
        success = run_script(script, description)
        results[description] = success
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 VISUALIZATION GENERATION SUMMARY")
    print("=" * 60)
    
    successful = sum(results.values())
    total = len(results)
    
    for description, success in results.items():
        status = "✅ SUCCESS" if success else "❌ FAILED"
        print(f"{status} - {description}")
    
    print(f"\n📈 Overall: {successful}/{total} visualizations generated successfully")
    
    if successful == total:
        print("🎉 All visualizations generated successfully!")
        print("\n📁 Generated files in outputs/ directory:")
        
        # List generated files
        try:
            output_files = [f for f in os.listdir('outputs') if f.endswith(('.html', '.png'))]
            output_files.sort()
            
            for file in output_files:
                file_path = os.path.join('outputs', file)
                file_size = os.path.getsize(file_path) / 1024  # KB
                print(f"   📄 {file} ({file_size:.1f} KB)")
        
        except Exception as e:
            print(f"⚠️  Error listing files: {e}")
    
    else:
        print("⚠️  Some visualizations failed to generate. Check the errors above.")
    
    print(f"\nCompleted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return successful == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 