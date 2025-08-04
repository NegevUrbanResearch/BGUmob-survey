/**
 * BGU Mobility Survey - Map Controller
 * Handles interactive map functionality and data visualization
 */

class BGUMapController {
    constructor() {
        this.map = null;
        this.poisData = [];
        this.routesData = [];
        this.statistics = {};
        this.currentFilters = {
            transportMode: 'all',
            showPOIs: true,
            showRoutes: true,
            commentsOnly: false
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
            zoom: 12,
            pitch: 45,
            bearing: 0,
            antialias: true
        });

        // Map layers and interactions will be set up after map loads

        // Add navigation controls
        this.map.addControl(new maplibregl.NavigationControl(), 'top-left');
        this.map.addControl(new maplibregl.ScaleControl(), 'bottom-left');
    }

    setupMapLayers() {
        // Routes source (add first so it appears under POIs)
        this.map.addSource('routes', {
            type: 'geojson',
            data: { type: 'FeatureCollection', features: [] }
        });

        // Route lines with intensity-based coloring and blending
        this.map.addLayer({
            id: 'routes',
            type: 'line',
            source: 'routes',
            layout: {
                'line-join': 'round',
                'line-cap': 'round'
            },
            paint: {
                'line-color': [
                    'interpolate',
                    ['linear'],
                    ['get', 'intensity'],
                    0, '#004D00',    // Very Dark Green - Low usage
                    0.25, '#006400', // Dark Green - Low-medium usage
                    0.5, '#228B22',  // Forest Green - Medium usage
                    0.75, '#32CD32', // Lime Green - High-medium usage
                    1, '#90EE90'     // Light Green - High usage
                ],
                'line-width': [
                    'interpolate',
                    ['linear'],
                    ['get', 'intensity'],
                    0, 2,
                    1, 8
                ],
                'line-opacity': 0.6,
                'line-blur': 1.0
            }
        });

        // Add a second route layer for blending effect
        this.map.addLayer({
            id: 'routes-blend',
            type: 'line',
            source: 'routes',
            layout: {
                'line-join': 'round',
                'line-cap': 'round'
            },
            paint: {
                'line-color': [
                    'interpolate',
                    ['linear'],
                    ['get', 'intensity'],
                    0, '#90EE90',    // Light Green - Low usage (inverted for blending)
                    0.25, '#32CD32', // Lime Green - Low-medium usage
                    0.5, '#228B22',  // Forest Green - Medium usage
                    0.75, '#006400', // Dark Green - High-medium usage
                    1, '#004D00'     // Very Dark Green - High usage
                ],
                'line-width': [
                    'interpolate',
                    ['linear'],
                    ['get', 'intensity'],
                    0, 1,
                    1, 4
                ],
                'line-opacity': 0.4,
                'line-blur': 2.0
            }
        });

        // POI source with clustering - inspired by deck.gl IconLayer
        this.map.addSource('pois', {
            type: 'geojson',
            data: { type: 'FeatureCollection', features: [] },
            cluster: true,
            clusterMaxZoom: 18,  // Higher max zoom for better clustering
            clusterRadius: 80,   // Larger radius for better grouping
            clusterMinPoints: 2  // Minimum points to form a cluster
        });

        // Cluster circles with Deck.gl-style design
        this.map.addLayer({
            id: 'clusters',
            type: 'circle',
            source: 'pois',
            filter: ['has', 'point_count'],
            paint: {
                'circle-color': [
                    'step',
                    ['get', 'point_count'],
                    '#4CAF50',  // Green for small clusters
                    3,
                    '#2196F3',  // Blue for medium clusters
                    10,
                    '#FF9800',  // Orange for large clusters
                    20,
                    '#F44336'   // Red for very large clusters
                ],
                'circle-radius': [
                    'step',
                    ['get', 'point_count'],
                    12,  // Small clusters
                    3,
                    18,  // Medium clusters
                    10,
                    24,  // Large clusters
                    20,
                    30   // Very large clusters
                ],
                'circle-opacity': 0.95,
                'circle-stroke-width': 2,
                'circle-stroke-color': '#ffffff',
                'circle-stroke-opacity': 0.9
            }
        });

        // Cluster labels with better visibility
        this.map.addLayer({
            id: 'cluster-count',
            type: 'symbol',
            source: 'pois',
            filter: ['has', 'point_count'],
            layout: {
                'text-field': '{point_count_abbreviated}',
                'text-font': ['Inter', 'Arial Unicode MS Bold'],
                'text-size': [
                    'step',
                    ['get', 'point_count'],
                    10,  // Small clusters
                    5,
                    12,  // Medium clusters
                    15,
                    14,  // Large clusters
                    30,
                    16   // Very large clusters
                ],
                'text-allow-overlap': true
            },
            paint: {
                'text-color': '#ffffff',
                'text-halo-color': '#000000',
                'text-halo-width': 2
            }
        });

        // Individual POI points with Deck.gl-style icon design
        this.map.addLayer({
            id: 'unclustered-point',
            type: 'circle',
            source: 'pois',
            filter: ['!', ['has', 'point_count']],
            paint: {
                'circle-color': '#4CAF50',
                'circle-radius': 8,
                'circle-stroke-width': 2,
                'circle-stroke-color': '#ffffff',
                'circle-stroke-opacity': 0.9,
                'circle-opacity': 0.95
            }
        });

        // Campus gates
        this.map.addSource('gates', {
            type: 'geojson',
            data: {
                type: 'FeatureCollection',
                features: [
                    {
                        type: 'Feature',
                        geometry: { type: 'Point', coordinates: [34.801138, 31.261222] },
                        properties: { name: 'South Gate 3', type: 'gate' }
                    },
                    {
                        type: 'Feature',
                        geometry: { type: 'Point', coordinates: [34.799290, 31.263911] },
                        properties: { name: 'North Gate 3', type: 'gate' }
                    },
                    {
                        type: 'Feature',
                        geometry: { type: 'Point', coordinates: [34.805528, 31.262500] },
                        properties: { name: 'West Gate', type: 'gate' }
                    }
                ]
            }
        });

        this.map.addLayer({
            id: 'gates',
            type: 'circle',
            source: 'gates',
            paint: {
                'circle-color': '#ff6b6b',
                'circle-radius': 12,
                'circle-stroke-width': 3,
                'circle-stroke-color': '#ffffff',
                'circle-opacity': 0.9
            }
        });
    }

    setupMapInteractions() {
        // POI click handler
        this.map.on('click', 'unclustered-point', (e) => {
            const coordinates = e.features[0].geometry.coordinates.slice();
            const properties = e.features[0].properties;
            
            new maplibregl.Popup()
                .setLngLat(coordinates)
                .setHTML(`
                    <div class="poi-popup">
                        <h4><i class="fas fa-map-pin"></i> POI Location</h4>
                        <p class="poi-comment">"${properties.comment}"</p>
                    </div>
                `)
                .addTo(this.map);
        });

        // Gate click handler
        this.map.on('click', 'gates', (e) => {
            const coordinates = e.features[0].geometry.coordinates.slice();
            const properties = e.features[0].properties;
            
            // Get mode distribution for this gate
            const gateRoutes = this.routesData.filter(route => 
                route.destination.name === properties.name
            );
            
            const modeCounts = {};
            gateRoutes.forEach(route => {
                modeCounts[route.transportMode] = (modeCounts[route.transportMode] || 0) + 1;
            });
            
            const modeChart = this.generateModePieChart(modeCounts);
            
            new maplibregl.Popup()
                .setLngLat(coordinates)
                .setHTML(`
                    <div class="gate-popup">
                        <h4><i class="fas fa-university"></i> ${properties.name}</h4>
                        <p><strong>${gateRoutes.length}</strong> trips</p>
                        <div class="mode-chart">
                            ${modeChart}
                        </div>
                    </div>
                `)
                .addTo(this.map);
        });

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

        // Cluster click handler
        this.map.on('click', 'clusters', (e) => {
            const features = this.map.queryRenderedFeatures(e.point, {
                layers: ['clusters']
            });
            const clusterId = features[0].properties.cluster_id;
            this.map.getSource('pois').getClusterExpansionZoom(
                clusterId,
                (err, zoom) => {
                    if (err) return;
                    this.map.easeTo({
                        center: features[0].geometry.coordinates,
                        zoom: zoom
                    });
                }
            );
        });

        // Cursor changes
        this.map.on('mouseenter', 'clusters', () => {
            this.map.getCanvas().style.cursor = 'pointer';
        });
        this.map.on('mouseleave', 'clusters', () => {
            this.map.getCanvas().style.cursor = '';
        });

        // Cluster hover effect
        this.map.on('mouseenter', 'clusters', () => {
            this.map.getCanvas().style.cursor = 'pointer';
        });
        this.map.on('mouseenter', 'unclustered-point', () => {
            this.map.getCanvas().style.cursor = 'pointer';
        });
        this.map.on('mouseleave', 'unclustered-point', () => {
            this.map.getCanvas().style.cursor = '';
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
            // Group routes by transport mode
            const modeGroups = {};
            let totalRoutes = 0;
            
            // Use a Set to track unique route IDs to avoid double-counting
            const uniqueRouteIds = new Set();
            
            features.forEach(feature => {
                const mode = feature.properties.transportMode;
                const routeId = feature.properties.id;
                
                // Only count each route once
                if (!uniqueRouteIds.has(routeId)) {
                    uniqueRouteIds.add(routeId);
                    
                    if (!modeGroups[mode]) {
                        modeGroups[mode] = 0;
                    }
                    modeGroups[mode] += 1;
                    totalRoutes += 1;
                }
            });
            
            // Create combined popup content
            let popupContent = `
                <div class="route-popup">
                    <h4><i class="fas fa-route"></i> Route Information</h4>
                    <p><strong>${totalRoutes}</strong> total routes</p>
            `;
            
            Object.entries(modeGroups).forEach(([mode, count]) => {
                const modeColors = {
                    'walking': '#4CAF50',
                    'bicycle': '#FF9800',
                    'ebike': '#9C27B0',
                    'car': '#F44336',
                    'bus': '#2196F3',
                    'train': '#795548',
                    'unknown': '#9E9E9E'
                };
                
                popupContent += `
                    <div class="route-mode-item">
                        <span class="mode-dot" style="background: ${modeColors[mode] || '#9E9E9E'}"></span>
                        <span>${mode}: ${count} routes</span>
                    </div>
                `;
            });
            
            popupContent += '</div>';
            
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
            setTimeout(() => this.updateMap(), 100);
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
        setTimeout(() => this.updateMap(), 100);
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
        // Check if map sources exist before updating
        if (!this.map.getSource('pois') || !this.map.getSource('routes')) {
            console.log('⚠️ Map sources not ready yet, skipping update');
            return;
        }

        // Update POIs
        const poiFeatures = this.poisData
            .filter(poi => this.currentFilters.showPOIs)
            .filter(poi => !this.currentFilters.commentsOnly || poi.hasComment)
            .map(poi => ({
                type: 'Feature',
                geometry: {
                    type: 'Point',
                    coordinates: [poi.lng, poi.lat]
                },
                properties: {
                    id: poi.id,
                    comment: poi.comment,
                    hasComment: poi.hasComment
                }
            }));

        this.map.getSource('pois').setData({
            type: 'FeatureCollection',
            features: poiFeatures
        });

        // Group routes by transport mode for smooth layering
        const modeGroups = {};
        this.routesData
            .filter(route => this.currentFilters.showRoutes)
            .filter(route => this.currentFilters.transportMode === 'all' || route.transportMode === this.currentFilters.transportMode)
            .forEach(route => {
                if (!modeGroups[route.transportMode]) {
                    modeGroups[route.transportMode] = [];
                }
                modeGroups[route.transportMode].push(route);
            });
        
        // Create route features with mode-based intensity
        const routeFeatures = [];
        Object.entries(modeGroups).forEach(([mode, modeRoutes]) => {
            // Calculate mode intensity (same for all routes in this mode)
            const modeIntensity = modeRoutes.length / this.routesData.length;
            
            modeRoutes.forEach(route => {
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
                        transportMode: route.transportMode,
                        distance: route.distance,
                        poiCount: route.poiCount,
                        intensity: modeIntensity,
                        modeCount: modeRoutes.length
                    }
                });
            });
        });

        this.map.getSource('routes').setData({
            type: 'FeatureCollection',
            features: routeFeatures
        });
    }

    updateUI() {

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

    setTransportFilter(mode) {
        this.currentFilters.transportMode = mode;
        
        // Update button states
        document.querySelectorAll('.transport-menu-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        
        if (mode === 'all') {
            document.querySelector('.transport-menu-btn').classList.add('active');
        } else {
            // Update the dropdown button text
            const dropdownBtn = document.querySelector('.transport-dropdown .transport-menu-btn');
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

    toggleCommentsOnly() {
        this.currentFilters.commentsOnly = !this.currentFilters.commentsOnly;
        document.querySelector('[data-filter="comments"]').classList.toggle('active', this.currentFilters.commentsOnly);
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
        window.toggleCommentsOnly = () => this.toggleCommentsOnly();
        window.resetMap = () => this.resetMap();
        window.toggleFullscreen = () => this.toggleFullscreen();
        window.setTransportFilter = (mode) => this.setTransportFilter(mode);
        
        // Add transport dropdown functionality
        window.toggleTransportDropdown = () => {
            const options = document.getElementById('transport-options');
            options.classList.toggle('show');
        };

        // Close dropdown when clicking outside
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.transport-dropdown')) {
                const options = document.getElementById('transport-options');
                if (options) {
                    options.classList.remove('show');
                }
            }
        });
    }

    resetMap() {
        this.map.flyTo({
            center: [34.7983, 31.2627],
            zoom: 12,
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