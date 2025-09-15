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

- Node.js ≥ 14 (for npm scripts) and Python ≥ 3.8 (for the default static server)
- The `outputs/` directory present with the generated data and charts

Setup:

1. Ensure the `outputs/` directory contains the generated data and charts

Run locally:

- Start a local static server:
  - `npm start` (uses `python3 -m http.server 8000`)
  - or `npm run serve`
  - or `npx http-server -p 8000`
- Open `http://localhost:8000`

## Directory structure

- `index.html` — main app and UI
- `assets/js/map-controller.js` — MapLibre/deck.gl logic
- `outputs/` — precomputed data and charts (HTML/JSON)
