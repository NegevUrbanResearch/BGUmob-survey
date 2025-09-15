#!/usr/bin/env python3
"""
BGU Mobility Survey - Main Script
Runs all data processing and visualization scripts.
"""

import os
import sys
import subprocess
from pathlib import Path


def run_script(script_name: str):
    """Run a Python script and print the result."""
    print(f"🚀 Running {script_name}...")

    try:
        result = subprocess.run(
            [sys.executable, script_name], capture_output=True, text=True, timeout=300
        )

        if result.returncode == 0:
            print(f"✅ {script_name} completed successfully")
            # Print important output lines
            for line in result.stdout.split("\n"):
                if line.strip() and ("✓" in line or "⚠️" in line or "❌" in line):
                    print(f"   {line.strip()}")
        else:
            print(f"❌ {script_name} failed")
            if result.stderr:
                print(f"   Error: {result.stderr}")

    except subprocess.TimeoutExpired:
        print(f"❌ {script_name} timed out")
    except Exception as e:
        print(f"❌ {script_name} failed: {e}")


def main():
    """Run all visualization scripts in order."""
    print("🎯 BGU Mobility Survey - Running All Visualizations")
    print("=" * 50)

    # Change to parent directory (project root)
    os.chdir(Path(__file__).parent.parent)

    # Scripts to run in order
    scripts = [
        "src/data_exporter.py",
        "src/viz_transport_donut.py",
        "src/viz_transportation.py",
        "src/viz_participation.py",
        "src/viz_gate_distribution.py",
        "src/viz_walking_distance.py",
        "src/viz_route_choice.py",
        "src/viz_distance_comparison.py",
        "src/viz_poi_map.py",
        "src/generate_trips_visualization.py",
    ]

    # Run each script
    for script in scripts:
        if os.path.exists(script):
            run_script(script)
        else:
            print(f"⚠️  Script not found: {script}")

    print("\n🎉 All visualizations completed!")
    print("📁 Check the outputs/ directory for generated files")


if __name__ == "__main__":
    main()
