/**
 * BGU Mobility Survey - Map Controller
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
            gateDestination: 'all',
            transportMode: 'all',
            showPOIs: true,
            showRoutes: true
        };
        
        // MapLibre configuration - no token required!
        // Using free OpenStreetMap tiles
    }

    async initialize() {
        console.log('🗺️ Initializing BGU Mobility Map...');
        
        this.initMap();
        
        // Wait for map to load before loading data
        await new Promise(resolve => {
            this.map.on('load', () => {
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
            container: 'map',
            style: 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json',
            center: [34.7983, 31.2627], // BGU area
            zoom: 14,
            pitch: 45,
            bearing: 0,
            antialias: true
        });

        // Map layers and interactions will be set up after map loads

        // Add navigation controls - moved to right side to avoid UI panel conflicts
        this.map.addControl(new maplibregl.NavigationControl(), 'top-right');
        this.map.addControl(new maplibregl.ScaleControl(), 'bottom-right');
        
    }

    setupMapLayers() {
        // Routes source (add first so it appears under POIs)
        this.map.addSource('routes', {
            type: 'geojson',
            data: { type: 'FeatureCollection', features: [] }
        });

        // Route lines with gate-based coloring and usage-based intensity
        this.map.addLayer({
            id: 'routes',
            type: 'line',
            source: 'routes',
            layout: {
                'line-join': 'round',
                'line-cap': 'round'
            },
            paint: {
                'line-color': ['get', 'gateColor'], // Use the gate color directly
                'line-width': [
                    'interpolate',
                    ['linear'],
                    ['get', 'intensity'],
                    0.2, 3,
                    1, 10
                ],
                'line-opacity': [
                    'interpolate',
                    ['linear'],
                    ['get', 'intensity'],
                    0.2, 0.4,
                    1, 0.9
                ],
                'line-blur': 0.5
            }
        });

        // Add a second route layer for enhanced blending effect
        this.map.addLayer({
            id: 'routes-blend',
            type: 'line',
            source: 'routes',
            layout: {
                'line-join': 'round',
                'line-cap': 'round'
            },
            paint: {
                'line-color': ['get', 'gateColor'], // Same gate color
                'line-width': [
                    'interpolate',
                    ['linear'],
                    ['get', 'intensity'],
                    0.2, 6,
                    1, 16
                ],
                'line-opacity': [
                    'interpolate',
                    ['linear'],
                    ['get', 'intensity'],
                    0.2, 0.15,
                    1, 0.35
                ],
                'line-blur': 3.0
            }
        });

        // Campus gates data with color coding
        this.gatesData = [
            { lng: 34.801138, lat: 31.261222, name: 'South Gate', type: 'gate', color: '#E91E63', id: 'south' }, // Pink
            { lng: 34.799290, lat: 31.263911, name: 'North Gate', type: 'gate', color: '#9C27B0', id: 'north' }, // Purple  
            { lng: 34.805528, lat: 31.262500, name: 'West Gate', type: 'gate', color: '#FF9800', id: 'west' } // Orange
        ];
        
        // Gate color mapping for route coloring
        this.gateColors = {
            'South Gate': '#E91E63',
            'North Gate': '#9C27B0', 
            'West Gate': '#FF9800',
            'south': '#E91E63',
            'north': '#9C27B0',
            'west': '#FF9800'
        };
    }

    initializeDeckGLOverlay() {
        // Initialize deck.gl overlay for MapLibre
        this.deckOverlay = new deck.MapboxOverlay({
            interleaved: true,
            layers: [],
            getTooltip: this.getDeckGLTooltip.bind(this)
        });
        
        // Add the overlay to the map - position it to appear below other controls
        this.map.addControl(this.deckOverlay, 'top-right');
        
        // Add custom CSS to position deck.gl controls below MapLibre controls
        setTimeout(() => {
            this.styleDeckGLControls();
        }, 500);
        
        // Listen for zoom changes to update clustering
        this.map.on('zoom', () => {
            this.updateDeckGLLayers();
        });
        
        console.log('✓ deck.gl overlay initialized');
    }

    styleDeckGLControls() {
        // Find and style deck.gl control elements
        const mapContainer = document.getElementById('map');
        if (mapContainer) {
            // Look for deck.gl control containers
            const deckControls = mapContainer.querySelectorAll('.deck-widget, .deck-tooltip, [class*="deck"]');
            deckControls.forEach(control => {
                control.style.background = 'rgba(0, 0, 0, 0.8)';
                control.style.backdropFilter = 'blur(20px)';
                control.style.border = '1px solid rgba(255, 255, 255, 0.3)';
                control.style.borderRadius = '12px';
                control.style.color = 'rgba(255, 255, 255, 0.95)';
                control.style.boxShadow = '0 4px 12px rgba(0, 0, 0, 0.15)';
            });

            // Adjust positioning to place deck.gl controls below MapLibre controls
            const topRightControls = mapContainer.querySelector('.maplibregl-ctrl-top-right');
            if (topRightControls) {
                const maplibreHeight = topRightControls.offsetHeight;
                // Position deck.gl controls below MapLibre controls
                deckControls.forEach(control => {
                    if (control.style.position === 'absolute' || window.getComputedStyle(control).position === 'absolute') {
                        control.style.top = `${100 + maplibreHeight + 10}px`;
                        control.style.right = '20px';
                        control.style.zIndex = '1000';
                    }
                });
            }
        }
    }

    getDeckGLTooltip({object, layer}) {
        if (!object) return null;
        
        if (layer.id === 'poi-icons') {
            return {
                html: `
                    <div style="font-family: Inter, sans-serif; padding: 10px; max-width: 220px;">
                        <div style="font-weight: 600; color: #2c3e50; margin-bottom: 6px; font-size: 13px;">
                            📍 POI Location
                        </div>
                        <div style="color: #666; font-style: italic; font-size: 12px; line-height: 1.4;">
                            "${object.comment || 'No specific comment provided'}"
                        </div>
                    </div>
                `,
                style: {
                    backgroundColor: 'rgba(255, 255, 255, 0.95)',
                    backdropFilter: 'blur(10px)',
                    border: '1px solid rgba(255, 255, 255, 0.2)',
                    borderRadius: '8px',
                    boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)'
                }
            };
        }
        
        if (layer.id === 'poi-clusters') {
            return {
                html: `
                    <div style="font-family: Inter, sans-serif; padding: 10px; max-width: 200px;">
                        <div style="font-weight: 600; color: #2c3e50; margin-bottom: 6px; font-size: 13px;">
                            📍 POI Cluster
                        </div>
                        <div style="color: #666; font-size: 12px;">
                            ${object.points.length} POI points
                        </div>
                        <div style="color: #888; font-size: 10px; margin-top: 4px;">
                            Click to zoom in
                        </div>
                    </div>
                `,
                style: {
                    backgroundColor: 'rgba(255, 255, 255, 0.95)',
                    backdropFilter: 'blur(10px)',
                    border: '1px solid rgba(255, 255, 255, 0.2)',
                    borderRadius: '8px',
                    boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)'
                }
            };
        }
        
        if (layer.id === 'gate-icons') {
            // Count trips to this gate
            const tripsToGate = this.routesData.filter(route => 
                route.destination.name === object.name
            ).length;
            
            return {
                html: `
                    <div style="font-family: Inter, sans-serif; padding: 10px; max-width: 200px;">
                        <div style="font-weight: 600; color: #2c3e50; margin-bottom: 6px; font-size: 13px;">
                            🏛️ ${object.name}
                        </div>
                        <div style="color: #666; font-size: 12px; margin-bottom: 4px;">
                            University Campus Gate
                        </div>
                        <div style="color: ${object.color}; font-weight: 600; font-size: 12px;">
                            ${tripsToGate} trips end here
                        </div>
                    </div>
                `,
                style: {
                    backgroundColor: 'rgba(255, 255, 255, 0.95)',
                    backdropFilter: 'blur(10px)',
                    border: '1px solid rgba(255, 255, 255, 0.2)',
                    borderRadius: '8px',
                    boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)'
                }
            };
        }
        
        if (layer.id === 'poi-individuals-in-cluster-mode') {
            return {
                html: `
                    <div style="font-family: Inter, sans-serif; padding: 10px; max-width: 220px;">
                        <div style="font-weight: 600; color: #2c3e50; margin-bottom: 6px; font-size: 13px;">
                            📍 POI Location
                        </div>
                        <div style="color: #666; font-style: italic; font-size: 12px; line-height: 1.4;">
                            "${object.comment || 'No specific comment provided'}"
                        </div>
                    </div>
                `,
                style: {
                    backgroundColor: 'rgba(255, 255, 255, 0.95)',
                    backdropFilter: 'blur(10px)',
                    border: '1px solid rgba(255, 255, 255, 0.2)',
                    borderRadius: '8px',
                    boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)'
                }
            };
        }
        
        return null;
    }

    createPOIIconLayer() {
        // Filter POI data based on current filters
        const filteredPOIs = this.poisData.filter(poi => this.currentFilters.showPOIs);

        // Create Lucide move-down icon SVG 
        function createPOIIcon() {
            const svg = `
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M8 18L12 22L16 18" stroke="#4CAF50" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
                    <path d="M12 2V22" stroke="#4CAF50" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
                </svg>
            `;
            return 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svg);
        }

        return new deck.IconLayer({
            id: 'poi-icons',
            data: filteredPOIs,
            getPosition: d => [d.lng, d.lat],
            getIcon: d => ({
                url: createPOIIcon(),
                width: 24,
                height: 24,
                anchorY: 12 // Anchor at center
            }),
            getSize: 28,
            pickable: true,
            sizeScale: 1,
            billboard: true // Always face the camera
        });
    }

    createPOIClusterLayer() {
        // Filter POI data based on current filters
        const filteredPOIs = this.poisData.filter(poi => this.currentFilters.showPOIs);

        // Create clusters from POI data
        const clusters = this.clusterPOIs(filteredPOIs);
        
        // Create cluster icon SVG dynamically with count - using Lucide move-down style
        function createClusterIcon(count) {
            const svg = `
                <svg width="32" height="32" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M10 22L16 28L22 22" stroke="#4CAF50" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
                    <path d="M16 4V28" stroke="#4CAF50" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
                    <text x="16" y="20" font-family="Inter, Arial, sans-serif" font-size="8" font-weight="bold" text-anchor="middle" fill="#4CAF50">${count}</text>
                </svg>
            `;
            return 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svg);
        }
        
        return new deck.IconLayer({
            id: 'poi-clusters',
            data: clusters.filter(cluster => cluster.points.length > 1), // Only show actual clusters
            getPosition: d => [d.lng, d.lat],
            getIcon: d => ({
                url: createClusterIcon(d.points.length),
                width: 32,
                height: 32,
                anchorY: 16 // Anchor at center
            }),
            getSize: 36,
            pickable: true,
            sizeScale: 1,
            billboard: true,
            onClick: (info) => this.handleClusterClick(info)
        });
    }

    createIndividualPOIsInClusterMode() {
        // Filter POI data based on current filters
        const filteredPOIs = this.poisData.filter(poi => this.currentFilters.showPOIs);

        // Get clusters to identify which POIs are individual
        const clusters = this.clusterPOIs(filteredPOIs);
        const individualPOIs = clusters
            .filter(cluster => cluster.points.length === 1)
            .map(cluster => cluster.points[0]);

        // Create Lucide move-down icon SVG - same as individual mode
        function createPOIIcon() {
            const svg = `
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M8 18L12 22L16 18" stroke="#4CAF50" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
                    <path d="M12 2V22" stroke="#4CAF50" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
                </svg>
            `;
            return 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svg);
        }

        return new deck.IconLayer({
            id: 'poi-individuals-in-cluster-mode',
            data: individualPOIs,
            getPosition: d => [d.lng, d.lat],
            getIcon: d => ({
                url: createPOIIcon(),
                width: 24,
                height: 24,
                anchorY: 12 // Anchor at center
            }),
            getSize: 28,
            pickable: true,
            sizeScale: 1,
            billboard: true
        });
    }

    createGateIconLayer() {
        const currentZoom = this.map.getZoom();
        
        // Only show gates at zoom 14 and above
        if (currentZoom < 14) {
            return null;
        }

        // Create Lucide target icon SVG for each gate with color - high resolution for crisp rendering
        function createTargetIcon(color) {
            const svg = `
                <svg width="48" height="48" viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <circle cx="24" cy="24" r="20" stroke="${color}" stroke-width="4" fill="rgba(255, 255, 255, 0.95)"/>
                    <circle cx="24" cy="24" r="12" stroke="${color}" stroke-width="4" fill="none"/>
                    <circle cx="24" cy="24" r="4" stroke="${color}" stroke-width="4" fill="${color}"/>
                </svg>
            `;
            return 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svg);
        }

        return new deck.IconLayer({
            id: 'gate-icons',
            data: this.gatesData,
            getPosition: d => [d.lng, d.lat, 100], // Higher z-coordinate to ensure it's above everything
            getIcon: d => ({
                url: createTargetIcon(d.color),
                width: 48,
                height: 48,
                anchorY: 24 // Anchor at center
            }),
            getSize: 32, // Smaller size than before
            sizeMinPixels: 24, // Minimum size in pixels (when zoomed out)
            sizeMaxPixels: 48, // Maximum size in pixels (caps growth when zoomed in)
            pickable: true,
            billboard: true,
            sizeScale: 1
        });
    }

    clusterPOIs(pois) {
        // Dynamic cluster radius based on zoom level
        const currentZoom = this.map.getZoom();
        const clusterRadius = Math.max(30, 100 - (currentZoom * 8)); // Smaller radius at higher zoom
        
        const clusters = [];
        const clustered = new Set();
        
        pois.forEach((poi, index) => {
            if (clustered.has(index)) return;
            
            const cluster = {
                lng: poi.lng,
                lat: poi.lat,
                points: [poi]
            };
            
            clustered.add(index);
            
            // Find nearby POIs to cluster
            pois.forEach((otherPoi, otherIndex) => {
                if (clustered.has(otherIndex) || index === otherIndex) return;
                
                const distance = this.getDistance(poi.lat, poi.lng, otherPoi.lat, otherPoi.lng);
                
                // Cluster if within radius (in meters)
                if (distance < clusterRadius) {
                    cluster.points.push(otherPoi);
                    clustered.add(otherIndex);
                    
                    // Update cluster center to average position
                    cluster.lng = cluster.points.reduce((sum, p) => sum + p.lng, 0) / cluster.points.length;
                    cluster.lat = cluster.points.reduce((sum, p) => sum + p.lat, 0) / cluster.points.length;
                }
            });
            
            clusters.push(cluster);
        });
        
        return clusters;
    }

    getDistance(lat1, lng1, lat2, lng2) {
        // Haversine formula to calculate distance between two points
        const R = 6371000; // Earth's radius in meters
        const dLat = (lat2 - lat1) * Math.PI / 180;
        const dLng = (lng2 - lng1) * Math.PI / 180;
        const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
                Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
                Math.sin(dLng / 2) * Math.sin(dLng / 2);
        const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
        return R * c;
    }

    handleClusterClick(info) {
        if (info.object && info.object.points.length > 1) {
            // Zoom into the cluster to show individual POIs
            const cluster = info.object;
            const bounds = this.calculateClusterBounds(cluster.points);
            
            this.map.fitBounds([
                [bounds.minLng, bounds.minLat],
                [bounds.maxLng, bounds.maxLat]
            ], {
                padding: 100,
                maxZoom: 17 // Zoom high enough to show individual pins
            });
        }
    }

    calculateClusterBounds(points) {
        const lngs = points.map(p => p.lng);
        const lats = points.map(p => p.lat);
        
        return {
            minLng: Math.min(...lngs),
            maxLng: Math.max(...lngs),
            minLat: Math.min(...lats),
            maxLat: Math.max(...lats)
        };
    }



    updateDeckGLLayers() {
        if (!this.deckOverlay) {
            console.log('⚠️ Deck overlay not ready yet');
            return;
        }

        const layers = [];
        
        // Add POI layers (clustered or individual based on zoom) - bottom layer
        if (this.currentFilters.showPOIs) {
            const currentZoom = this.map.getZoom();
            
            // Show clusters at lower zoom levels, individual icons at higher zoom
            if (currentZoom < 15) {
                layers.push(this.createPOIClusterLayer());
                // Add individual POIs that aren't clustered
                layers.push(this.createIndividualPOIsInClusterMode());
            } else {
                layers.push(this.createPOIIconLayer());
            }
        }
        
        // Always show campus gates on top - added last so they appear above all other layers (only if zoom >= 13)
        const gateLayer = this.createGateIconLayer();
        if (gateLayer) {
            layers.push(gateLayer);
        }
        
        // Update the overlay with new layers
        this.deckOverlay.setProps({
            layers: layers
        });
        
        // Re-apply styling to any new deck.gl controls
        setTimeout(() => {
            this.styleDeckGLControls();
        }, 100);
        
        console.log(`✓ Updated deck.gl with ${layers.length} layers at zoom ${this.map.getZoom().toFixed(1)}`);
    }

    setupMapInteractions() {

        // Route hover handler with combined data for overlapping routes
        this.map.on('mouseenter', 'routes', (e) => {
            this.map.getCanvas().style.cursor = 'pointer';
            this.showRoutePopup(e);
        });

        this.map.on('mouseenter', 'routes-blend', (e) => {
            this.map.getCanvas().style.cursor = 'pointer';
            this.showRoutePopup(e);
        });

        this.map.on('mouseleave', 'routes', () => {
            this.map.getCanvas().style.cursor = '';
            // Remove popup when mouse leaves
            const popups = document.querySelectorAll('.maplibregl-popup');
            popups.forEach(popup => popup.remove());
        });

        this.map.on('mouseleave', 'routes-blend', () => {
            this.map.getCanvas().style.cursor = '';
            // Remove popup when mouse leaves
            const popups = document.querySelectorAll('.maplibregl-popup');
            popups.forEach(popup => popup.remove());
        });


        this.map.on('mouseenter', 'gates', () => {
            this.map.getCanvas().style.cursor = 'pointer';
        });
        this.map.on('mouseleave', 'gates', () => {
            this.map.getCanvas().style.cursor = '';
        });
    }

    showRoutePopup(e) {
        // Get all features at this point to handle overlapping routes
        const features = this.map.queryRenderedFeatures(e.point, { layers: ['routes', 'routes-blend'] });
        
        if (features.length > 0) {
            // Get route information from the first feature
            const firstFeature = features[0].properties;
            const usage = firstFeature.usage;
            const destinationGate = firstFeature.destinationGate;
            const gateColor = firstFeature.gateColor;
            const transportMode = firstFeature.transportMode;
            
            // Get transportation mode display info
            const modeDisplayNames = {
                'walking': '🚶 Walking',
                'bicycle': '🚴 Bicycle',
                'ebike': '🛴 E-bike',
                'car': '🚗 Car',
                'bus': '🚌 Bus',
                'train': '🚆 Train',
                'unknown': '❓ Unknown'
            };
            
            const modeDisplay = modeDisplayNames[transportMode] || `❓ ${transportMode}`;
            
            // Create simplified popup content
            let popupContent = `
                <div style="font-family: Inter, sans-serif; padding: 8px; min-width: 120px;">
                    <div style="font-weight: 600; color: #2c3e50; margin-bottom: 6px; font-size: 14px;">
                        ${modeDisplay}
                    </div>
                    <div style="color: #666; font-size: 12px; margin-bottom: 4px;">
                        → ${destinationGate}
                    </div>
                    <div style="color: ${gateColor}; font-weight: 600; font-size: 13px;">
                        ${usage} trips
                    </div>
                </div>
            `;
            
            new maplibregl.Popup()
                .setLngLat(e.lngLat)
                .setHTML(popupContent)
                .addTo(this.map);
        }
    }

    generateModePieChart(modeCounts) {
        const total = Object.values(modeCounts).reduce((sum, count) => sum + count, 0);
        const colors = {
            'walking': '#4CAF50',
            'bicycle': '#FF9800',
            'ebike': '#9C27B0',
            'car': '#F44336',
            'bus': '#2196F3',
            'train': '#795548',
            'unknown': '#9E9E9E'
        };
        
        let chartHTML = '<div class="mode-pie-chart">';
        Object.entries(modeCounts).forEach(([mode, count]) => {
            const percentage = (count / total * 100).toFixed(1);
            const color = colors[mode] || '#9E9E9E';
            chartHTML += `
                <div class="mode-item">
                    <div class="mode-color" style="background: ${color}"></div>
                    <span>${mode}: ${count} (${percentage}%)</span>
                </div>
            `;
        });
        chartHTML += '</div>';
        return chartHTML;
    }

    async loadData() {
        try {
            console.log('📊 Loading mobility data...');
            const response = await fetch('outputs/bgu_mobility_data.json');
            const data = await response.json();
            
            this.poisData = data.pois || [];
            this.routesData = data.routes || [];
            this.statistics = data.statistics || {};
            
            console.log(`✓ Loaded ${this.poisData.length} POIs and ${this.routesData.length} routes`);
            
            this.updateUI();
            // Small delay to ensure map sources are ready
            setTimeout(() => {
                this.updateMap();
                this.updateDeckGLLayers();
            }, 100);
            this.hideLoading();
        } catch (error) {
            console.error('❌ Error loading data:', error);
            this.loadSampleData();
        }
    }

    loadSampleData() {
        console.log('⚠️ Loading sample data as fallback...');
        this.poisData = this.generateSamplePOIs();
        this.routesData = this.generateSampleRoutes();
        this.statistics = this.calculateStatistics();
        
        this.updateUI();
        // Small delay to ensure map sources are ready
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
            "Good wifi cafe"
        ];

        for (let i = 0; i < 50; i++) {
            const offset = [(Math.random() - 0.5) * 0.02, (Math.random() - 0.5) * 0.02];
            samples.push({
                id: `poi_${i}`,
                lat: center[1] + offset[1],
                lng: center[0] + offset[0],
                comment: comments[Math.floor(Math.random() * comments.length)],
                hasComment: Math.random() > 0.3
            });
        }
        return samples;
    }

    generateSampleRoutes() {
        const modes = ['walking', 'bicycle', 'ebike', 'car', 'bus'];
        const samples = [];
        
        for (let i = 0; i < 30; i++) {
            samples.push({
                id: `route_${i}`,
                transportMode: modes[Math.floor(Math.random() * modes.length)],
                distance: Math.random() * 5 + 1,
                residence: { lat: 31.2627 + (Math.random() - 0.5) * 0.02, lng: 34.7983 + (Math.random() - 0.5) * 0.02 },
                destination: { lat: 31.261222, lng: 34.801138 }
            });
        }
        return samples;
    }

    calculateStatistics() {
        const poisWithComments = this.poisData.filter(poi => poi.hasComment).length;
        const avgDistance = this.routesData.reduce((sum, route) => sum + route.distance, 0) / this.routesData.length;
        
        return {
            totalPois: this.poisData.length,
            totalRoutes: this.routesData.length,
            poisWithComments: poisWithComments,
            commentPercentage: Math.round((poisWithComments / this.poisData.length) * 100),
            averageDistance: avgDistance.toFixed(1),
            transportModes: {
                walking: this.routesData.filter(r => r.transportMode === 'walking').length,
                bicycle: this.routesData.filter(r => r.transportMode === 'bicycle').length,
                ebike: this.routesData.filter(r => r.transportMode === 'ebike').length,
                car: this.routesData.filter(r => r.transportMode === 'car').length,
                bus: this.routesData.filter(r => r.transportMode === 'bus').length
            }
        };
    }

    updateMap() {
        // Check if map sources exist before updating routes
        if (!this.map.getSource('routes')) {
            console.log('⚠️ Map sources not ready yet, skipping update');
            return;
        }

        // Update deck.gl POI layers
        this.updateDeckGLLayers();

        // Filter routes based on current filters
        const filteredRoutes = this.routesData
            .filter(route => this.currentFilters.showRoutes)
            .filter(route => this.currentFilters.gateDestination === 'all' || route.destination.name === this.currentFilters.gateDestination)
            .filter(route => this.currentFilters.transportMode === 'all' || route.transportMode === this.currentFilters.transportMode);

        // Group routes by transportation mode and destination gate for proper aggregation
        const routeGroups = {};
        
        filteredRoutes.forEach(route => {
            const groupKey = `${route.transportMode || 'unknown'}_${route.destination.name || 'Unknown'}`;
            
            if (!routeGroups[groupKey]) {
                routeGroups[groupKey] = {
                    routes: [],
                    transportMode: route.transportMode || 'unknown',
                    destinationGate: route.destination.name || 'Unknown',
                    gateColor: this.gateColors[route.destination.name] || this.gateColors[route.destination.id] || '#9E9E9E'
                };
            }
            routeGroups[groupKey].routes.push(route);
        });

        // Find max group size for intensity calculation
        const maxGroupSize = Math.max(...Object.values(routeGroups).map(group => group.routes.length), 1);
        
        // Create route features from groups - aggregate similar routes
        const routeFeatures = [];
        Object.values(routeGroups).forEach(group => {
            const groupSize = group.routes.length;
            const intensity = 0.2 + (groupSize / maxGroupSize) * 0.8;
            
            // For each route in the group, create a feature but with group statistics
            group.routes.forEach(route => {
                // Use route path if available, otherwise fall back to straight line
                const coordinates = route.routePath || [
                    [route.residence.lng, route.residence.lat],
                    [route.destination.lng, route.destination.lat]
                ];
                
                routeFeatures.push({
                    type: 'Feature',
                    geometry: {
                        type: 'LineString',
                        coordinates: coordinates
                    },
                    properties: {
                        id: route.id,
                        transportMode: group.transportMode,
                        distance: route.distance,
                        poiCount: route.poiCount,
                        intensity: intensity,
                        usage: groupSize, // Show group size instead of individual count
                        destinationGate: group.destinationGate,
                        gateColor: group.gateColor,
                        // Additional properties for debugging
                        groupKey: `${group.transportMode}_${group.destinationGate}`,
                        totalInGroup: groupSize
                    }
                });
            });
        });

        console.log(`📊 Route aggregation: ${filteredRoutes.length} individual routes grouped into ${Object.keys(routeGroups).length} transport-gate combinations`);

        this.map.getSource('routes').setData({
            type: 'FeatureCollection',
            features: routeFeatures
        });
    }

    updateUI() {

        // Create gate destination dropdown options
        const gateOptions = document.getElementById('gate-options');
        gateOptions.innerHTML = '';
        
        // Gate destination options
        const gateRoutes = {};
        this.routesData.forEach(route => {
            const gateName = route.destination.name || 'Unknown';
            gateRoutes[gateName] = (gateRoutes[gateName] || 0) + 1;
        });
        
        Object.entries(gateRoutes).forEach(([gateName, count]) => {
            if (count > 0) {
                const gateColor = this.gateColors[gateName] || '#9E9E9E';
                const option = document.createElement('div');
                option.className = 'transport-option';
                option.innerHTML = `
                    <span style="display: inline-block; width: 8px; height: 8px; background: ${gateColor}; border-radius: 50%; margin-right: 6px;"></span>
                    ${gateName} (${count})
                `;
                option.onclick = () => {
                    this.setGateFilter(gateName);
                    document.getElementById('gate-options').classList.remove('show');
                };
                gateOptions.appendChild(option);
            }
        });

        // Create transport mode dropdown options
        const transportOptions = document.getElementById('transport-options');
        transportOptions.innerHTML = '';
        
        // Transportation mode colors
        const modeColors = {
            walking: '#4CAF50',
            bicycle: '#FF9800',
            ebike: '#9C27B0',
            car: '#F44336',
            bus: '#2196F3',
            train: '#795548',
            unknown: '#9E9E9E'
        };
        
        Object.entries(this.statistics.transportModes).forEach(([mode, count]) => {
            if (count > 0) {
                const option = document.createElement('div');
                option.className = 'transport-option';
                option.innerHTML = `
                    <span style="display: inline-block; width: 8px; height: 8px; background: ${modeColors[mode] || modeColors.unknown}; border-radius: 50%; margin-right: 6px;"></span>
                    ${mode} (${count})
                `;
                option.onclick = () => {
                    this.setTransportFilter(mode);
                    document.getElementById('transport-options').classList.remove('show');
                };
                transportOptions.appendChild(option);
            }
        });
    }

    setGateFilter(gateName) {
        this.currentFilters.gateDestination = gateName;
        
        // Update button states for gate menu
        document.querySelectorAll('#gate-menu .transport-menu-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        
        if (gateName === 'all') {
            document.querySelector('#gate-menu .transport-menu-btn').classList.add('active');
        } else {
            // Update the dropdown button text
            const dropdownBtn = document.querySelector('#gate-menu .transport-dropdown .transport-menu-btn');
            const gateColor = this.gateColors[gateName] || '#9E9E9E';
            dropdownBtn.innerHTML = `
                <span style="display: inline-block; width: 8px; height: 8px; background: ${gateColor}; border-radius: 50%; margin-right: 6px;"></span>
                ${gateName}
                <i class="fas fa-chevron-down"></i>
            `;
            dropdownBtn.classList.add('active');
        }
        
        this.updateMap();
    }

    setTransportFilter(mode) {
        this.currentFilters.transportMode = mode;
        
        // Update button states for transport menu
        document.querySelectorAll('#transport-menu .transport-menu-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        
        if (mode === 'all') {
            document.querySelector('#transport-menu .transport-menu-btn').classList.add('active');
        } else {
            // Update the dropdown button text
            const dropdownBtn = document.querySelector('#transport-menu .transport-dropdown .transport-menu-btn');
            const modeColors = {
                walking: '#4CAF50',
                bicycle: '#FF9800',
                ebike: '#9C27B0',
                car: '#F44336',
                bus: '#2196F3',
                train: '#795548',
                unknown: '#9E9E9E'
            };
            dropdownBtn.innerHTML = `
                <span style="display: inline-block; width: 8px; height: 8px; background: ${modeColors[mode] || modeColors.unknown}; border-radius: 50%; margin-right: 6px;"></span>
                ${mode}
                <i class="fas fa-chevron-down"></i>
            `;
            dropdownBtn.classList.add('active');
        }
        
        this.updateMap();
    }

    togglePOIs() {
        this.currentFilters.showPOIs = !this.currentFilters.showPOIs;
        document.querySelector('[data-filter="pois"]').classList.toggle('active', this.currentFilters.showPOIs);
        this.updateMap();
    }

    toggleRoutes() {
        this.currentFilters.showRoutes = !this.currentFilters.showRoutes;
        document.querySelector('[data-filter="routes"]').classList.toggle('active', this.currentFilters.showRoutes);
        this.updateMap();
    }



    hideLoading() {
        const loading = document.getElementById('loading');
        loading.style.opacity = '0';
        setTimeout(() => {
            loading.style.display = 'none';
        }, 500);
    }

    animateStatistics() {
        const counters = document.querySelectorAll('.stat-number');
        counters.forEach(counter => {
            const target = parseFloat(counter.textContent);
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
        // Make filter functions globally accessible
        window.togglePOIs = () => this.togglePOIs();
        window.toggleRoutes = () => this.toggleRoutes();
        window.resetMap = () => this.resetMap();
        window.toggleFullscreen = () => this.toggleFullscreen();
        window.setGateFilter = (gateName) => this.setGateFilter(gateName);
        window.setTransportFilter = (mode) => this.setTransportFilter(mode);
        
        // Add gate dropdown functionality
        window.toggleGateDropdown = () => {
            const options = document.getElementById('gate-options');
            options.classList.toggle('show');
        };
        
        // Add transport dropdown functionality
        window.toggleTransportDropdown = () => {
            const options = document.getElementById('transport-options');
            options.classList.toggle('show');
        };

        // Close dropdown when clicking outside
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.transport-dropdown')) {
                const gateOptions = document.getElementById('gate-options');
                const transportOptions = document.getElementById('transport-options');
                if (gateOptions) {
                    gateOptions.classList.remove('show');
                }
                if (transportOptions) {
                    transportOptions.classList.remove('show');
                }
            }
        });
    }

    resetMap() {
        this.map.flyTo({
            center: [34.7983, 31.2627],
            zoom: 14,
            pitch: 45,
            bearing: 0
        });
    }

    toggleFullscreen() {
        if (!document.fullscreenElement) {
            document.documentElement.requestFullscreen();
        } else {
            document.exitFullscreen();
        }
    }

    // Mode-based intensity calculation (same as original viz_poi_map.py)
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    const mapController = new BGUMapController();
    mapController.initialize();
}); 