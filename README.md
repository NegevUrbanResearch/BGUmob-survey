# BGU Mobility Survey Dashboard

Interactive visualization platform for analyzing student transportation patterns around Ben-Gurion University (BGU) campus collected via submissions through ZenCity Surveys.

🌐 **Live Site**: [https://neveurbanresearch.github.io/BGUmob-survey/](https://neveurbanresearch.github.io/BGUmob-survey/)

## Project overview

This site presents campus mobility insights collected from BGU students to understand the relationship between the university and the city:

- Students' modes of travel to and from campus
- Common routes and entry gates
- Amenities students engage with along the way

## Deployment (GitHub Pages)

This is a static site that can be deployed directly to GitHub Pages without any special configuration.

## Local development

Prerequisites:

- Node.js ≥ 14 (for npm scripts) and Python ≥ 3.8 (for data processing and static server)
- The `outputs/` directory present with the generated data and charts

Setup:

1. Ensure the `outputs/` directory contains the generated data and charts
2. If you need to regenerate the data and visualizations, run the Python scripts from the `src/` directory

Run locally:

- Start a local static server:
  - `npm start` (uses `python3 -m http.server 8000`)
  - or `npm run serve`
  - or `npx http-server -p 8000`
- Open `http://localhost:8000`

## Data processing and visualization

The Python scripts in the `src/` directory handle data processing and visualization generation. Use the main pipeline script to run everything:

### Quick Start

```bash
# Run all visualizations
cd src
python main.py
```

### Required Data Files

The project requires several data files to function properly:

**Input Data:**

- `data/mobility-data.csv` — Original survey responses from ZenCity
- `data/university_polygon.json` — University boundary in GeoJSON format (committed to repo)

**University Gate Locations:**
The following gate coordinates are hardcoded in the scripts (from BeerSheva Mobility project):

- **South Gate**: 31.261222, 34.801138
- **North Gate**: 31.263911, 34.799290
- **West Gate**: 31.262500, 34.805528

**External Dependencies:**

- **OpenTripPlanner (OTP) Server** — Required for route generation (optional, will skip routes if unavailable)
  - Default URL: `http://localhost:8080/otp/routers/default`
  - Used for generating realistic walking/cycling routes between residences and university gates

### Data Processing Workflow

The preprocessing pipeline follows this sequence:

1. **Raw Data** (`data/mobility-data.csv`) — Original survey responses from ZenCity
2. **Preprocessing** (`preprocessing.py`) — Data validation, cleaning, and merging
   - Validates survey completion rates and data integrity
   - Merges split binary questions (Further-yes/Further-no → Further_Study_Interest)
   - Translates Hebrew modes to English
   - Parses coordinate data from JSON format
   - Outputs: `data/processed_mobility_data.csv`
3. **Data Export** (`data_exporter.py`) — Exports clean JSON for web visualization
   - Extracts POI (Points of Interest) data with coordinates
   - Generates route data with university gate assignments
   - Calculates statistics and metadata
   - Outputs: `outputs/bgu_mobility_data.json`, `outputs/pois.json`, `outputs/routes.json`

### Visualization Scripts

- `viz_transport_donut.py` — Transportation mode distribution (donut chart)
- `viz_transportation.py` — Transportation modes (bar chart)
- `viz_participation.py` — Future participation willingness analysis
- `viz_gate_distribution.py` — University gate usage patterns
- `viz_walking_distance.py` — Walking distance statistics and analysis
- `viz_route_choice.py` — Route choice factors and preferences
- `viz_distance_comparison.py` — Actual vs straight-line distance comparison
- `viz_poi_map.py` — Interactive POI map generation
- `generate_trips_visualization.py` — Comprehensive trip visualization

## Directory structure

- `index.html` — main app and UI
- `assets/js/map-controller.js` — MapLibre/deck.gl logic
- `src/` — Python scripts for data processing and visualization generation
- `outputs/` — precomputed data and charts (HTML/JSON)
- `data/` — raw survey data and university boundary
