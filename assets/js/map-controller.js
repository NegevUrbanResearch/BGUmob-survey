/**
 * BGU Mobility Survey - Map Controller (Optimized)
 * Handles interactive map functionality and data visualization
 */

class BGUMapController {
  constructor() {
    this.map = null;
    this.deckOverlay = null;
    this.poisData = [];
    this.routesData = [];
    this.statistics = {};
    this.currentFilters = {
      showPOIs: true,
      showRoutes: true,
      showUniversity: true,
    };

    // Gate color mapping for route coloring
    this.gateColors = {
      "South Gate": "#22a7f0",
      "North Gate": "#9c5dc7",
      "West Gate": "#e14b31",
      south: "#22a7f0",
      north: "#9c5dc7",
      west: "#e14b31",
    };

    // Campus gates data
    this.gatesData = [
      {
        lng: 34.801138,
        lat: 31.261222,
        name: "South Gate",
        type: "gate",
        color: "#22a7f0",
        id: "south",
      },
      {
        lng: 34.79929,
        lat: 31.263911,
        name: "North Gate",
        type: "gate",
        color: "#9c5dc7",
        id: "north",
      },
      {
        lng: 34.805528,
        lat: 31.2625,
        name: "West Gate",
        type: "gate",
        color: "#e14b31",
        id: "west",
      },
    ];
  }

  // Convert hex color to rgba string with given alpha
  hexToRgba(hex, alpha = 1) {
    const clean = hex.replace("#", "");
    const r = parseInt(clean.substring(0, 2), 16);
    const g = parseInt(clean.substring(2, 4), 16);
    const b = parseInt(clean.substring(4, 6), 16);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
  }

  // Setup RTL text plugin for Hebrew text support
  async setupRTLTextPlugin() {
    try {
      console.log("🔤 Setting up RTL text plugin for Hebrew support...");

      // Set the RTL text plugin with lazy loading
      await maplibregl.setRTLTextPlugin(
        "https://cdn.jsdelivr.net/npm/@maplibre/maplibre-gl-rtl-text@1.0.1/dist/maplibre-gl-rtl-text.js",
        true // lazy load - only load when RTL text is encountered
      );

      console.log("✓ RTL text plugin configured successfully");
    } catch (error) {
      console.warn("⚠️ Failed to load RTL text plugin:", error);
      console.log("Hebrew text may not display correctly");
    }
  }

  async initialize() {
    console.log("🗺️ Initializing BGU Mobility Map...");

    // Configure RTL text plugin for Hebrew support
    await this.setupRTLTextPlugin();

    this.initMap();

    await new Promise((resolve) => {
      this.map.on("load", () => {
        this.setupMapLayers();
        this.setupMapInteractions();
        this.initializeDeckGLOverlay();
        resolve();
      });
    });

    await this.loadData();
    this.setupEventListeners();
    this.animateStatistics();
  }

  initMap() {
    this.map = new maplibregl.Map({
      container: "map",
      style: "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
      center: [34.7983, 31.2627], // BGU area
      zoom: 14,
      pitch: 0,
      bearing: 0,
      antialias: true,
    });

    // Add navigation controls
    // Top-right: Zoom only (compass separated)
    this.map.addControl(
      new maplibregl.NavigationControl({ showZoom: true, showCompass: false }),
      "top-right"
    );
    // Bottom-right: Compass only (should appear above the scale bar)
    this.map.addControl(
      new maplibregl.NavigationControl({ showZoom: false, showCompass: true }),
      "bottom-right"
    );
    // Bottom-right: Scale bar
    this.map.addControl(new maplibregl.ScaleControl(), "bottom-right");

    // Ensure compass is above scale in the DOM and highlight its group
    setTimeout(() => {
      const mapContainer = this.map.getContainer();
      const br = mapContainer.querySelector(".maplibregl-ctrl-bottom-right");
      if (!br) return;
      const compassGroup = Array.from(
        br.querySelectorAll(".maplibregl-ctrl-group")
      ).find((g) => g.querySelector(".maplibregl-ctrl-compass"));
      const scaleEl = br.querySelector(".maplibregl-ctrl-scale");
      if (compassGroup) {
        compassGroup.classList.add("compass-group");
      }
      if (compassGroup && scaleEl && compassGroup.nextSibling !== scaleEl) {
        br.insertBefore(compassGroup, scaleEl);
      }
    }, 0);
  }

  setupMapLayers() {
    // Routes source
    this.map.addSource("routes", {
      type: "geojson",
      data: { type: "FeatureCollection", features: [] },
    });

    // Background stroke layer for smoother visual appearance
    this.map.addLayer({
      id: "routes-background",
      type: "line",
      source: "routes",
      layout: {
        "line-join": "round",
        "line-cap": "round",
      },
      paint: {
        "line-color": "rgba(255, 255, 255, 0.3)", // Light background stroke
        "line-width": [
          "interpolate",
          ["exponential", 1.2],
          ["zoom"],
          10,
          [
            "interpolate",
            ["linear"],
            ["get", "localDensity"],
            1,
            3.0,
            2,
            4.0,
            3,
            5.5,
            5,
            7.5,
            10,
            10.5,
          ],
          16,
          [
            "interpolate",
            ["linear"],
            ["get", "localDensity"],
            1,
            4.5,
            2,
            5.5,
            3,
            7.0,
            5,
            9.5,
            10,
            14.0,
          ],
        ],
        "line-opacity": 0.6,
        "line-blur": 1.0,
        "line-offset": [
          "interpolate",
          ["exponential", 1.1],
          ["zoom"],
          10,
          [
            "*",
            [
              "*",
              [
                "match",
                ["get", "gateKey"],
                "south",
                -0.3,
                "north",
                0,
                "west",
                0.3,
                0,
              ],
              [
                "interpolate",
                ["linear"],
                ["get", "localDensity"],
                1,
                0.8,
                3,
                1.0,
                5,
                1.2,
                10,
                1.5,
              ],
            ],
            1.8,
          ],
          16,
          [
            "*",
            [
              "*",
              [
                "match",
                ["get", "gateKey"],
                "south",
                -0.4,
                "north",
                0,
                "west",
                0.4,
                0,
              ],
              [
                "interpolate",
                ["linear"],
                ["get", "localDensity"],
                1,
                0.8,
                3,
                1.0,
                5,
                1.2,
                10,
                1.5,
              ],
            ],
            3.5,
          ],
        ],
      },
    });

    // Colored route lines with smooth curved junctions
    this.map.addLayer({
      id: "routes",
      type: "line",
      source: "routes",
      layout: {
        "line-join": "round", // Use round for smooth curves
        "line-cap": "round", // Round caps for smooth endings
        "line-sort-key": ["get", "renderOrder"], // Control drawing order
      },
      paint: {
        "line-color": ["get", "gateColor"],
        // Zoom-aware thickness with smoother transitions
        "line-width": [
          "interpolate",
          ["exponential", 1.2],
          ["zoom"],
          10,
          [
            "interpolate",
            ["linear"],
            ["get", "localDensity"],
            1,
            1.8,
            2,
            2.5,
            3,
            3.5,
            5,
            5.0,
            10,
            7.5,
          ],
          16,
          [
            "interpolate",
            ["linear"],
            ["get", "localDensity"],
            1,
            2.5,
            2,
            3.5,
            3,
            5.0,
            5,
            7.5,
            10,
            12.0,
          ],
        ],
        "line-opacity": [
          "interpolate",
          ["linear"],
          ["get", "localDensity"],
          1,
          0.8,
          5,
          0.9,
          10,
          0.95,
        ],
        "line-blur": [
          // Minimal blur for crisp lines
          "interpolate",
          ["linear"],
          ["zoom"],
          10,
          0.1,
          16,
          0.2,
        ],
        // Much smaller, dynamic offset based on density to minimize artifacts
        "line-offset": [
          "interpolate",
          ["exponential", 1.1],
          ["zoom"],
          10,
          [
            "*",
            [
              "*",
              [
                "match",
                ["get", "gateKey"],
                "south",
                -0.3, // Much smaller offsets
                "north",
                0,
                "west",
                0.3,
                0,
              ],
              // Scale offset by density to spread high-traffic routes
              [
                "interpolate",
                ["linear"],
                ["get", "localDensity"],
                1,
                0.8,
                3,
                1.0,
                5,
                1.2,
                10,
                1.5,
              ],
            ],
            1.8, // Reduced base multiplier
          ],
          16,
          [
            "*",
            [
              "*",
              [
                "match",
                ["get", "gateKey"],
                "south",
                -0.4,
                "north",
                0,
                "west",
                0.4,
                0,
              ],
              [
                "interpolate",
                ["linear"],
                ["get", "localDensity"],
                1,
                0.8,
                3,
                1.0,
                5,
                1.2,
                10,
                1.5,
              ],
            ],
            3.5, // Reduced max multiplier
          ],
        ],
      },
    });

    // University polygon source
    this.map.addSource("university", {
      type: "geojson",
      data: { type: "FeatureCollection", features: [] },
    });

    // University polygon outline layer (bright yellow, no fill)
    this.map.addLayer({
      id: "university-outline",
      type: "line",
      source: "university",
      paint: {
        "line-color": "#FFD700", // Bright yellow
        "line-width": ["interpolate", ["linear"], ["zoom"], 10, 3, 16, 5],
        "line-opacity": 0.9,
      },
    });

    // University label layer (white "BGU" text)
    this.map.addLayer({
      id: "university-label",
      type: "symbol",
      source: "university",
      layout: {
        "text-field": "BGU",
        "text-font": ["Open Sans Bold", "Arial Unicode MS Bold"],
        "text-size": ["interpolate", ["linear"], ["zoom"], 10, 16, 16, 24],
        "text-anchor": "center",
        "text-justify": "center",
        "symbol-placement": "point",
      },
      paint: {
        "text-color": "#FFFFFF", // White text
        "text-halo-color": "#000000", // Black outline for better visibility
        "text-halo-width": 2,
        "text-opacity": 0.9,
      },
    });
  }

  initializeDeckGLOverlay() {
    this.deckOverlay = new deck.MapboxOverlay({
      interleaved: true,
      layers: [],
      getTooltip: this.getDeckGLTooltip.bind(this),
    });

    this.map.addControl(this.deckOverlay, "top-right");

    // Style deck.gl controls after initialization
    setTimeout(() => this.styleDeckGLControls(), 500);

    // Update layers on zoom
    this.map.on("zoom", () => this.updateDeckGLLayers());

    console.log("✓ deck.gl overlay initialized");
  }

  styleDeckGLControls() {
    const mapContainer = document.getElementById("map");
    if (!mapContainer) return;

    const deckControls = mapContainer.querySelectorAll(
      '.deck-widget, .deck-tooltip, [class*="deck"]'
    );
    deckControls.forEach((control) => {
      Object.assign(control.style, {
        background: "rgba(0, 0, 0, 0.8)",
        backdropFilter: "blur(20px)",
        border: "1px solid rgba(255, 255, 255, 0.3)",
        borderRadius: "12px",
        color: "rgba(255, 255, 255, 0.95)",
        boxShadow: "0 4px 12px rgba(0, 0, 0, 0.15)",
      });
    });

    // Position below MapLibre controls
    const topRightControls = mapContainer.querySelector(
      ".maplibregl-ctrl-top-right"
    );
    if (topRightControls) {
      const maplibreHeight = topRightControls.offsetHeight;
      deckControls.forEach((control) => {
        if (
          control.style.position === "absolute" ||
          window.getComputedStyle(control).position === "absolute"
        ) {
          Object.assign(control.style, {
            top: `${100 + maplibreHeight + 10}px`,
            right: "20px",
            zIndex: "1000",
          });
        }
      });
    }
  }

  getDeckGLTooltip({ object, layer }) {
    if (!object) return null;

    const baseStyle = {
      backgroundColor: "rgba(0, 0, 0, 0.92)",
      color: "rgba(255, 255, 255, 0.95)",
      backdropFilter: "blur(10px)",
      border: "1px solid rgba(255, 255, 255, 0.2)",
      borderRadius: "8px",
      boxShadow: "0 4px 12px rgba(0, 0, 0, 0.35)",
    };

    if (layer.id === "poi-icons") {
      return {
        html: `
                    <div style="font-family: Inter, sans-serif; padding: 10px; max-width: 220px;">
                        <div style="font-weight: 600; color: #8ab4f8; margin-bottom: 6px; font-size: 13px;">
                            📍 POI Location
                        </div>
                        <div style="color: #dfe5ec; font-style: italic; font-size: 12px; line-height: 1.4; font-weight: 300;">
                            "${
                              object.comment || "No specific comment provided"
                            }"
                        </div>
                    </div>
                `,
        style: baseStyle,
      };
    }

    if (layer.id === "gate-icons") {
      const tripsToGate = this.routesData.filter(
        (route) => route.destination.name === object.name
      ).length;

      return {
        html: `
                    <div style="font-family: Inter, sans-serif; padding: 10px; max-width: 200px;">
                        <div style="font-weight: 600; color: #e8eaed; margin-bottom: 6px; font-size: 13px;">
                            🏛️ ${object.name}
                        </div>
                        <div style="color: #cfd8dc; font-size: 12px; margin-bottom: 4px;">
                            University Campus Gate
                        </div>
                        <div style="color: ${object.color}; font-weight: 600; font-size: 12px;">
                            ${tripsToGate} trips end here
                        </div>
                    </div>
                `,
        style: baseStyle,
      };
    }

    return null;
  }

  // Optimized icon creation functions
  createPOIIcon() {
    if (!this._poiIconCache) {
      const svg = `
                <svg width="24" height="24" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">
                    <defs>
                        <filter id="shadow" x="-50%" y="-50%" width="200%" height="200%">
                            <feDropShadow dx="0" dy="2" stdDeviation="2" flood-color="rgba(0,0,0,0.35)"/>
                        </filter>
                    </defs>
                    <g filter="url(#shadow)">
                        <path d="M32 6c-8.8 0-16 7.2-16 16 0 11.046 16 30 16 30s16-18.954 16-30c0-8.8-7.2-16-16-16z" fill="#4CAF50" stroke="#1B5E20" stroke-width="2"/>
                        <circle cx="32" cy="22" r="7" fill="#FFFFFF"/>
                        <path d="M26 16c2-3 7-4 10-2" stroke="rgba(255,255,255,0.65)" stroke-width="2" stroke-linecap="round" fill="none"/>
                    </g>
                </svg>
            `;
      this._poiIconCache =
        "data:image/svg+xml;charset=utf-8," + encodeURIComponent(svg);
    }
    return this._poiIconCache;
  }

  createClusterIcon(count) {
    if (!this._clusterIconCache) this._clusterIconCache = {};
    if (!this._clusterIconCache[count]) {
      const svg = `
                <svg width="32" height="32" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M10 22L16 28L22 22" stroke="#4CAF50" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    <path d="M16 4V28" stroke="#4CAF50" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    <text x="16" y="20" font-family="Inter, Arial, sans-serif" font-size="8" font-weight="bold" text-anchor="middle" fill="#4CAF50">${count}</text>
                </svg>
            `;
      this._clusterIconCache[count] =
        "data:image/svg+xml;charset=utf-8," + encodeURIComponent(svg);
    }
    return this._clusterIconCache[count];
  }

  createTargetIcon(color) {
    if (!this._targetIconCache) this._targetIconCache = {};
    if (!this._targetIconCache[color]) {
      const svg = `
                <svg width="48" height="48" viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <circle cx="24" cy="24" r="20" stroke="${color}" stroke-width="4" fill="rgba(255, 255, 255, 0.95)"/>
                    <circle cx="24" cy="24" r="12" stroke="${color}" stroke-width="4" fill="none"/>
                    <circle cx="24" cy="24" r="4" stroke="${color}" stroke-width="4" fill="${color}"/>
                </svg>
            `;
      this._targetIconCache[color] =
        "data:image/svg+xml;charset=utf-8," + encodeURIComponent(svg);
    }
    return this._targetIconCache[color];
  }

  createPOIIconLayer() {
    const filteredPOIs = this.poisData.filter(
      (poi) => this.currentFilters.showPOIs
    );

    return new deck.IconLayer({
      id: "poi-icons",
      data: filteredPOIs,
      getPosition: (d) => [d.lng, d.lat],
      getIcon: () => ({
        url: this.createPOIIcon(),
        width: 24,
        height: 24,
        anchorY: 24,
      }),
      getSize: 28,
      pickable: true,
      sizeScale: 1,
      billboard: true,
      onClick: ({ object }) => {
        if (!object) return;
        this.showPOIPopup(object);
      },
    });
  }

  // Clustered POI layers removed: all POIs use the same icon layer

  createGateIconLayer() {
    return new deck.IconLayer({
      id: "gate-icons",
      data: this.gatesData,
      getPosition: (d) => [d.lng, d.lat, 100],
      getIcon: (d) => ({
        url: this.createTargetIcon(d.color),
        width: 48,
        height: 48,
        anchorY: 24,
      }),
      getSize: 20,
      sizeMinPixels: 16,
      sizeMaxPixels: 36,
      pickable: true,
      billboard: true,
      sizeScale: 1,
      onClick: ({ object }) => {
        if (!object) return;
        this.showGatePopup(object);
      },
    });
  }

  // Clustering removed

  // Optimized distance calculation
  getDistance(lat1, lng1, lat2, lng2) {
    const R = 6371000; // Earth's radius in meters
    const dLat = ((lat2 - lat1) * Math.PI) / 180;
    const dLng = ((lng2 - lng1) * Math.PI) / 180;
    const a =
      Math.sin(dLat / 2) * Math.sin(dLat / 2) +
      Math.cos((lat1 * Math.PI) / 180) *
        Math.cos((lat2 * Math.PI) / 180) *
        Math.sin(dLng / 2) *
        Math.sin(dLng / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    return R * c;
  }

  // Cluster interactions removed

  updateDeckGLLayers() {
    if (!this.deckOverlay) {
      console.log("⚠️ Deck overlay not ready yet");
      return;
    }

    const layers = [];

    // Always show individual POI icons (no clustering)
    if (this.currentFilters.showPOIs) {
      layers.push(this.createPOIIconLayer());
    }

    // Always show campus gates on top
    layers.push(this.createGateIconLayer());

    this.deckOverlay.setProps({ layers });

    setTimeout(() => this.styleDeckGLControls(), 100);

    console.log(
      `✓ Updated deck.gl with ${layers.length} layers at zoom ${this.map
        .getZoom()
        .toFixed(1)}`
    );
  }

  setupMapInteractions() {
    // Route hover handlers for both layers
    const routeLayers = ["routes", "routes-background"];

    routeLayers.forEach((layerId) => {
      this.map.on("mouseenter", layerId, (e) => {
        this.map.getCanvas().style.cursor = "pointer";
        if (layerId === "routes") {
          // Only show popup for main routes layer
          this.showRoutePopup(e);
        }
      });

      this.map.on("mouseleave", layerId, () => {
        this.map.getCanvas().style.cursor = "";
        if (layerId === "routes") {
          // Only handle popup removal for main routes layer
          document
            .querySelectorAll(".maplibregl-popup")
            .forEach((popup) => popup.remove());
        }
      });
    });

    // Mobile/tap support: show route usage on tap/click
    this.map.on("click", "routes", (e) => {
      this.showRoutePopup(e);
    });
    this.map.on("click", "routes-background", (e) => {
      this.showRoutePopup(e);
    });

    this.map.on("mouseenter", "gates", () => {
      this.map.getCanvas().style.cursor = "pointer";
    });

    this.map.on("mouseleave", "gates", () => {
      this.map.getCanvas().style.cursor = "";
    });
  }

  // FIXED: Compact popup for crowded locations
  showRoutePopup(e) {
    // Expand query to a small pixel buffer to capture adjacent offset routes
    const buffer = 10; // pixels
    const min = [e.point.x - buffer, e.point.y - buffer];
    const max = [e.point.x + buffer, e.point.y + buffer];
    const features = this.map.queryRenderedFeatures([min, max], {
      layers: ["routes"],
    });

    console.log(
      `🔍 Found ${features.length} individual route segments at this location`
    );

    if (features.length === 0) return;

    // Group by transport mode + destination
    const segmentGroups = new Map();

    features.forEach((feature) => {
      const props = feature.properties;
      const groupKey = `${props.transportMode}_${props.destinationGate}`;

      if (!segmentGroups.has(groupKey)) {
        segmentGroups.set(groupKey, {
          transportMode: props.transportMode,
          destinationGate: props.destinationGate,
          gateColor: props.gateColor,
          count: 0,
        });
      }

      segmentGroups.get(groupKey).count++;
    });

    const totalTrips = features.length;
    const uniqueColors = [
      ...new Set(features.map((f) => f.properties.gateColor)),
    ];
    const blendedColor = this.blendColors(uniqueColors);

    const modeLabels = {
      walking: "Walking",
      bicycle: "Bicycle",
      ebike: "E-bike",
      car: "Driving",
      bus: "Bus",
      train: "Train",
      unknown: "Mode N/A",
    };

    // Sort groups by count (highest first)
    const sortedGroups = Array.from(segmentGroups.values()).sort(
      (a, b) => b.count - a.count
    );

    // Build compact popup - show ALL routes now
    let popupContent = `
            <div style="font-family: Inter, sans-serif; padding: 12px; min-width: 180px; max-width: 240px; background: rgba(0,0,0,0.95); color: #e8eaed; border-radius: 8px; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);">
                <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
                    <span style="font-weight: 600; color: #e8eaed; font-size: 13px;">Routes Here</span>
                    <span style="font-size: 11px; color: #cfd8dc; margin-left: auto; font-weight: 600;">${totalTrips} trips</span>
                </div>
        `;

    // Show ALL routes in compact format
    sortedGroups.forEach((group) => {
      const modeLabel = modeLabels[group.transportMode] || "Mode N/A";
      const gateName = group.destinationGate.replace(" Gate", "");

      popupContent += `
                <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px; padding: 6px 8px; background: ${this.hexToRgba(
                  group.gateColor,
                  0.1
                )}; border-radius: 6px;">
                    <span style="width: 8px; height: 8px; border-radius: 50%; background: ${
                      group.gateColor
                    }; display: inline-block;"></span>
                    <span style="font-size: 11px; color: #e8eaed; font-weight: 500;">${modeLabel}</span>
                    <span style="font-size: 11px; color: #b0bec5; flex: 1;">→ ${gateName}</span>
                    <span style="font-size: 11px; font-weight: 600; color: #fff; background: ${
                      group.gateColor
                    }; padding: 2px 6px; border-radius: 8px;">${
        group.count
      }</span>
                </div>
            `;
    });

    new maplibregl.Popup({
      maxWidth: "280px",
      closeButton: false,
      closeOnClick: false,
    })
      .setLngLat(e.lngLat)
      .setHTML(popupContent)
      .addTo(this.map);
  }

  // Show POI popup on click/tap
  showPOIPopup(poi) {
    const comment = poi.comment || "No specific comment provided";
    const html = `
      <div style="font-family: Inter, sans-serif; padding: 10px; max-width: 240px;">
        <div style="font-weight: 600; color: #2c3e50; margin-bottom: 6px; font-size: 13px;">
          POI Comment
        </div>
        <div style="color: #444; font-size: 12px; line-height: 1.4;">
          "${comment}"
        </div>
      </div>`;
    new maplibregl.Popup({ closeButton: true, maxWidth: "260px" })
      .setLngLat([poi.lng, poi.lat])
      .setHTML(html)
      .addTo(this.map);
  }

  // Show Gate popup on click/tap
  showGatePopup(gate) {
    const tripsToGate = this.routesData.filter(
      (route) => route.destination.name === gate.name
    ).length;
    const html = `
      <div style="font-family: Inter, sans-serif; padding: 10px; max-width: 240px;">
        <div style="font-weight: 600; color: #2c3e50; margin-bottom: 6px; font-size: 13px;">
          ${gate.name}
        </div>
        <div style="color: ${gate.color}; font-weight: 600; font-size: 12px;">
          ${tripsToGate} trips end here
        </div>
      </div>`;
    new maplibregl.Popup({ closeButton: true, maxWidth: "260px" })
      .setLngLat([gate.lng, gate.lat])
      .setHTML(html)
      .addTo(this.map);
  }

  // Optimized color blending
  blendColors(colors) {
    if (colors.length === 0) return "#9E9E9E";
    if (colors.length === 1) return colors[0];

    const rgbColors = colors.map((color) => {
      const hex = color.replace("#", "");
      return [
        parseInt(hex.substr(0, 2), 16),
        parseInt(hex.substr(2, 2), 16),
        parseInt(hex.substr(4, 2), 16),
      ];
    });

    const blended = rgbColors
      .reduce(
        (acc, rgb) => [acc[0] + rgb[0], acc[1] + rgb[1], acc[2] + rgb[2]],
        [0, 0, 0]
      )
      .map((sum) => Math.round(sum / rgbColors.length));

    return `#${blended.map((c) => c.toString(16).padStart(2, "0")).join("")}`;
  }

  async loadData() {
    try {
      console.log("📊 Loading mobility data...");

      // Load main data and university polygon in parallel
      const [dataResponse, universityResponse] = await Promise.all([
        fetch("outputs/bgu_mobility_data.json").catch(() => null),
        fetch("outputs/university_polygon.json").catch(() => null),
      ]);

      // Process main mobility data
      if (dataResponse && dataResponse.ok) {
        const data = await dataResponse.json();
        this.poisData = data.pois || [];
        this.routesData = data.routes || [];
        this.statistics = data.statistics || {};
        console.log(
          `✓ Loaded ${this.poisData.length} POIs and ${this.routesData.length} routes`
        );
      } else {
        console.log("⚠️ Main data file not found, using sample data");
        this.poisData = this.generateSamplePOIs();
        this.routesData = this.generateSampleRoutes();
        this.statistics = this.calculateStatistics();
      }

      // Process University Polygon
      if (universityResponse && universityResponse.ok) {
        this.universityPolygon = await universityResponse.json();
        console.log("✓ Loaded university polygon");
      } else {
        console.log("⚠️ University polygon file not found");
        this.universityPolygon = null;
      }

      this.updateUI();
      setTimeout(() => {
        this.updateMap();
        this.updateDeckGLLayers();
      }, 100);
      this.hideLoading();
    } catch (error) {
      console.error("❌ Error loading data:", error);
      this.loadSampleData();
    }
  }

  loadSampleData() {
    console.log("⚠️ Loading sample data as fallback...");
    this.poisData = this.generateSamplePOIs();
    this.routesData = this.generateSampleRoutes();
    this.statistics = this.calculateStatistics();

    this.updateUI();
    setTimeout(() => {
      this.updateMap();
      this.updateDeckGLLayers();
    }, 100);
    this.hideLoading();
  }

  generateSamplePOIs() {
    const samples = [];
    const center = [34.7983, 31.2627];
    const comments = [
      "Great coffee shop for studying",
      "Quiet library spot",
      "Best falafel in town",
      "Convenient bus stop",
      "Nice park for breaks",
      "24/7 grocery store",
      "Affordable lunch spot",
      "Good wifi cafe",
    ];

    for (let i = 0; i < 50; i++) {
      const offset = [
        (Math.random() - 0.5) * 0.02,
        (Math.random() - 0.5) * 0.02,
      ];
      samples.push({
        id: `poi_${i}`,
        lat: center[1] + offset[1],
        lng: center[0] + offset[0],
        comment: comments[Math.floor(Math.random() * comments.length)],
        hasComment: Math.random() > 0.3,
      });
    }
    return samples;
  }

  generateSampleRoutes() {
    const modes = ["walking", "bicycle", "ebike", "car", "bus"];
    const samples = [];

    for (let i = 0; i < 30; i++) {
      const gate =
        this.gatesData[Math.floor(Math.random() * this.gatesData.length)];
      samples.push({
        id: `route_${i}`,
        transportMode: modes[Math.floor(Math.random() * modes.length)],
        distance: Math.random() * 5 + 1,
        residence: {
          lat: 31.2627 + (Math.random() - 0.5) * 0.02,
          lng: 34.7983 + (Math.random() - 0.5) * 0.02,
        },
        destination: {
          lat: gate.lat,
          lng: gate.lng,
          name: gate.name,
          id: gate.id,
        },
      });
    }
    return samples;
  }

  calculateStatistics() {
    const poisWithComments = this.poisData.filter(
      (poi) => poi.hasComment
    ).length;
    const avgDistance =
      this.routesData.length > 0
        ? this.routesData.reduce((sum, route) => sum + route.distance, 0) /
          this.routesData.length
        : 0;

    return {
      totalPois: this.poisData.length,
      totalRoutes: this.routesData.length,
      poisWithComments: poisWithComments,
      commentPercentage:
        this.poisData.length > 0
          ? Math.round((poisWithComments / this.poisData.length) * 100)
          : 0,
      averageDistance: avgDistance.toFixed(1),
      transportModes: {
        walking: this.routesData.filter((r) => r.transportMode === "walking")
          .length,
        bicycle: this.routesData.filter((r) => r.transportMode === "bicycle")
          .length,
        ebike: this.routesData.filter((r) => r.transportMode === "ebike")
          .length,
        car: this.routesData.filter((r) => r.transportMode === "car").length,
        bus: this.routesData.filter((r) => r.transportMode === "bus").length,
      },
    };
  }

  updateMap() {
    if (!this.map.getSource("routes")) {
      console.log("⚠️ Map sources not ready yet, skipping update");
      return;
    }

    this.updateDeckGLLayers();

    const filteredRoutes = this.routesData.filter(
      (route) => this.currentFilters.showRoutes
    );
    const routeSegments = this.createRouteSegments(filteredRoutes);

    console.log(
      `📊 Processed ${filteredRoutes.length} routes into ${routeSegments.length} segments`
    );

    // Smooth transition when updating route data
    if (this.map.getLayer("routes")) {
      this.map.setPaintProperty("routes", "line-opacity", 0.3);
      this.map.setPaintProperty("routes-background", "line-opacity", 0.2);
    }

    this.map.getSource("routes").setData({
      type: "FeatureCollection",
      features: routeSegments,
    });

    // Update university polygon if available
    if (this.universityPolygon && this.map.getSource("university")) {
      if (this.currentFilters.showUniversity) {
        this.map.getSource("university").setData(this.universityPolygon);
        this.map.setLayoutProperty(
          "university-outline",
          "visibility",
          "visible"
        );
        this.map.setLayoutProperty("university-label", "visibility", "visible");
        console.log("✓ Updated university polygon on map");
      } else {
        this.map.setLayoutProperty("university-outline", "visibility", "none");
        this.map.setLayoutProperty("university-label", "visibility", "none");
      }
    }

    // Fade lines back in smoothly
    setTimeout(() => {
      if (this.map.getLayer("routes")) {
        this.map.setPaintProperty("routes", "line-opacity", 0.85);
        this.map.setPaintProperty("routes-background", "line-opacity", 0.6);
      }
    }, 150);
  }

  // Smooth route coordinates to reduce sharp angles and junction artifacts
  smoothRouteCoordinates(coordinates) {
    if (coordinates.length <= 2) {
      return coordinates; // Can't smooth lines with 2 or fewer points
    }

    const smoothed = [coordinates[0]]; // Always keep first point

    for (let i = 1; i < coordinates.length - 1; i++) {
      const prev = coordinates[i - 1];
      const curr = coordinates[i];
      const next = coordinates[i + 1];

      // Calculate a slightly smoothed point that reduces sharp angles
      const smoothingFactor = 0.15; // Subtle smoothing
      const smoothedLng =
        curr[0] + (prev[0] + next[0] - 2 * curr[0]) * smoothingFactor;
      const smoothedLat =
        curr[1] + (prev[1] + next[1] - 2 * curr[1]) * smoothingFactor;

      smoothed.push([smoothedLng, smoothedLat]);
    }

    smoothed.push(coordinates[coordinates.length - 1]); // Always keep last point
    return smoothed;
  }

  // Fixed route segment creation - each route = 1 trip
  createRouteSegments(routes) {
    const routeFeatures = [];

    // Create individual segments for each route (each route = 1 trip)
    routes.forEach((route) => {
      const transportMode = route.transportMode || "unknown";
      const destinationGate =
        route.destination.name || route.destination.id || "Unknown";
      const destIdLc = (route.destination.id || "").toLowerCase();
      const destNameLc = (route.destination.name || "").toLowerCase();
      const gateKey =
        destIdLc.includes("south") || destNameLc.includes("south")
          ? "south"
          : destIdLc.includes("west") || destNameLc.includes("west")
          ? "west"
          : destIdLc.includes("north") || destNameLc.includes("north")
          ? "north"
          : "north";
      const gateColor =
        this.gateColors[route.destination.name] ||
        this.gateColors[gateKey] ||
        "#9E9E9E";

      const coordinates = this.smoothRouteCoordinates(
        route.routePath || [
          [route.residence.lng, route.residence.lat],
          [route.destination.lng, route.destination.lat],
        ]
      );

      // Check for overlapping segments at this location
      const overlappingSegments = this.findOverlappingSegments(
        coordinates,
        routeFeatures
      );
      const overlapCount = overlappingSegments.length;

      // Calculate intensity based on how many routes will be at this location
      const localDensity = 1 + overlapCount; // This route + overlapping ones
      const intensity = Math.min(0.2 + localDensity * 0.15, 1.0); // kept for backwards compat, not used in styling

      let blendedColor = gateColor;
      if (overlapCount > 0) {
        const overlapColors = [
          gateColor,
          ...overlappingSegments.map((s) => s.properties.gateColor),
        ];
        blendedColor = this.blendColors(overlapColors);
      }

      routeFeatures.push({
        type: "Feature",
        geometry: {
          type: "LineString",
          coordinates: coordinates,
        },
        properties: {
          id: route.id,
          transportMode: transportMode,
          distance: route.distance,
          poiCount: route.poiCount,
          intensity: intensity,
          localDensity: localDensity,
          usage: 1, // Each route represents exactly 1 trip
          destinationGate: destinationGate,
          destinationId: route.destination.id,
          gateKey: gateKey,
          gateColor: gateColor,
          blendedColor: blendedColor,
          overlapCount: overlapCount,
          renderOrder: localDensity, // Higher density routes render on top
          // Store additional route info for popup
          routeInfo: {
            startPoint: `${route.residence.lat.toFixed(
              4
            )}, ${route.residence.lng.toFixed(4)}`,
            endPoint: `${route.destination.lat.toFixed(
              4
            )}, ${route.destination.lng.toFixed(4)}`,
            distance: route.distance
              ? `${route.distance.toFixed(1)}km`
              : "Unknown",
          },
        },
      });
    });

    console.log(
      `📊 Created ${routeFeatures.length} individual route segments (1 trip each)`
    );
    return routeFeatures;
  }

  // Simplified overlap detection for better performance
  findOverlappingSegments(coordinates, existingFeatures) {
    const overlapping = [];
    const tolerance = 50; // meters

    const start = coordinates[0];
    const end = coordinates[coordinates.length - 1];

    existingFeatures.forEach((feature) => {
      const existingCoords = feature.geometry.coordinates;
      const existingStart = existingCoords[0];
      const existingEnd = existingCoords[existingCoords.length - 1];

      // Quick check: are start and end points close?
      const startDist = this.getDistance(
        start[1],
        start[0],
        existingStart[1],
        existingStart[0]
      );
      const endDist = this.getDistance(
        end[1],
        end[0],
        existingEnd[1],
        existingEnd[0]
      );

      if (startDist < tolerance && endDist < tolerance) {
        overlapping.push(feature);
      }
    });

    return overlapping;
  }

  updateUI() {
    // Update statistics display if elements exist
    const elements = {
      "total-pois": this.statistics.totalPois,
      "total-routes": this.statistics.totalRoutes,
      "comment-percentage": this.statistics.commentPercentage,
      "average-distance": this.statistics.averageDistance,
    };

    Object.entries(elements).forEach(([id, value]) => {
      const element = document.getElementById(id);
      if (element) element.textContent = value;
    });
  }

  hideLoading() {
    const loading = document.getElementById("loading");
    if (loading) {
      loading.style.opacity = "0";
      setTimeout(() => (loading.style.display = "none"), 500);
    }
  }

  animateStatistics() {
    const counters = document.querySelectorAll(".stat-number");
    counters.forEach((counter) => {
      const target = parseFloat(counter.textContent);
      if (isNaN(target)) return;

      let current = 0;
      const increment = target / 60;
      const timer = setInterval(() => {
        current += increment;
        if (current >= target) {
          counter.textContent = target;
          clearInterval(timer);
        } else {
          counter.textContent = Math.floor(current);
        }
      }, 16);
    });
  }

  setupEventListeners() {
    // Make functions globally accessible
    window.resetMap = () => this.resetMap();
    window.toggleFullscreen = () => this.toggleFullscreen();
    window.toggleUniversityBoundary = () => this.toggleUniversityBoundary();
  }

  resetMap() {
    this.map.flyTo({
      center: [34.7983, 31.2627],
      zoom: 14,
      pitch: 0,
      bearing: 0,
    });
  }

  toggleFullscreen() {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen();
    } else {
      document.exitFullscreen();
    }
  }
}

// Initialize when DOM is loaded
document.addEventListener("DOMContentLoaded", () => {
  const mapController = new BGUMapController();
  mapController.initialize();
});
