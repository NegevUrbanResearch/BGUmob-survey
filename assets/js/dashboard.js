/**
 * BGU Mobility Dashboard - JavaScript
 * Handles navigation, transitions, and interactive features
 */

(function() {
    'use strict';

    // DOM elements
    const navLinks = document.querySelectorAll('.nav-link');
    const sections = document.querySelectorAll('.section');
    
    // Initialize dashboard when DOM is loaded
    document.addEventListener('DOMContentLoaded', function() {
        initializeNavigation();
        initializeSmoothScrolling();
        initializeAnimations();
        initializeTooltips();
        handleResponsiveFeatures();
        
        // Show section based on URL hash or default to overview
        const currentSection = Utils.getCurrentSectionFromHash();
        showSection(currentSection);
        const targetNavLink = document.querySelector(`[data-section="${currentSection}"]`);
        updateActiveNavLink(targetNavLink);
        
        console.log('✅ NUR Mobility Dashboard initialized successfully');
    });

    /**
     * Initialize navigation functionality
     */
    function initializeNavigation() {
        navLinks.forEach(link => {
            link.addEventListener('click', function(e) {
                e.preventDefault();
                
                const targetSection = this.getAttribute('data-section');
                if (targetSection) {
                    showSection(targetSection);
                    updateActiveNavLink(this);
                }
            });
        });

        // Handle browser back/forward buttons
        window.addEventListener('popstate', function(e) {
            const section = e.state?.section || 'overview';
            showSection(section);
            updateActiveNavLink(document.querySelector(`[data-section="${section}"]`));
        });
    }

    /**
     * Show specific section with smooth transition
     */
    function showSection(sectionId) {
        // Hide all sections
        sections.forEach(section => {
            section.classList.remove('active');
        });

        // Show target section
        const targetSection = document.getElementById(sectionId);
        if (targetSection) {
            // Small delay to ensure smooth transition
            setTimeout(() => {
                targetSection.classList.add('active');
                
                // Update browser history
                const newUrl = sectionId === 'overview' ? '#' : `#${sectionId}`;
                history.pushState({section: sectionId}, '', newUrl);
                
                // Update page title
                updatePageTitle(sectionId);
                
                // Trigger custom event for section change
                document.dispatchEvent(new CustomEvent('sectionChanged', {
                    detail: { sectionId }
                }));
            }, 50);
        }
    }

    /**
     * Update active navigation link
     */
    function updateActiveNavLink(activeLink) {
        navLinks.forEach(link => {
            link.classList.remove('active');
        });
        
        if (activeLink) {
            activeLink.classList.add('active');
        }
    }

    /**
     * Update page title based on active section
     */
    function updatePageTitle(sectionId) {
        const titles = {
            'overview': 'NUR Mobility Dashboard',
            'route-choice': 'Route Choice Analysis - NUR',
            'transportation': 'Transportation Analysis - NUR',
            'poi-map': 'Points of Interest - NUR',
            'credits': 'Credits & Methodology - NUR'
        };
        
        document.title = titles[sectionId] || 'BGU Mobility Dashboard';
    }

    /**
     * Initialize smooth scrolling for internal links
     */
    function initializeSmoothScrolling() {
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', function(e) {
                const href = this.getAttribute('href');
                if (href === '#') return;
                
                e.preventDefault();
                const target = document.querySelector(href);
                if (target) {
                    target.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            });
        });
    }

    /**
     * Initialize intersection observer for animations
     */
    function initializeAnimations() {
        const observerOptions = {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        };

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('animate-in');
                }
            });
        }, observerOptions);

        // Observe metric cards and info cards
        document.querySelectorAll('.metric-card, .info-card, .visualization-container').forEach(el => {
            observer.observe(el);
        });
    }

    /**
     * Initialize Bootstrap tooltips if available
     */
    function initializeTooltips() {
        // Check if Bootstrap tooltips are available
        if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
            const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
            tooltipTriggerList.map(function(tooltipTriggerEl) {
                return new bootstrap.Tooltip(tooltipTriggerEl);
            });
        }
    }

    /**
     * Handle responsive features
     */
    function handleResponsiveFeatures() {
        // Close mobile menu when clicking on nav link
        const navbarCollapse = document.getElementById('navbarNav');
        const navbarToggler = document.querySelector('.navbar-toggler');

        if (navbarCollapse && navbarToggler) {
            navLinks.forEach(link => {
                link.addEventListener('click', () => {
                    if (window.innerWidth < 992) { // Bootstrap lg breakpoint
                        const bsCollapse = new bootstrap.Collapse(navbarCollapse, {
                            toggle: false
                        });
                        bsCollapse.hide();
                    }
                });
            });
        }

        // Handle window resize
        let resizeTimer;
        window.addEventListener('resize', function() {
            clearTimeout(resizeTimer);
            resizeTimer = setTimeout(function() {
                handleViewportChange();
            }, 250);
        });
    }

    /**
     * Handle viewport changes for responsive design
     */
    function handleViewportChange() {
        // Adjust iframe heights on mobile
        const iframes = document.querySelectorAll('.viz-iframe');
        const isMobile = window.innerWidth < 768;
        
        iframes.forEach(iframe => {
            if (isMobile) {
                iframe.style.height = '92vh'; // Nearly full screen on mobile
                iframe.style.minHeight = '700px';
            } else {
                iframe.style.height = '95vh'; // Nearly full screen on desktop
                iframe.style.minHeight = '900px';
            }
        });
    }

    /**
     * Global navigation function for button clicks
     */
    window.navigateToSection = function(sectionId) {
        showSection(sectionId);
        const targetNavLink = document.querySelector(`[data-section="${sectionId}"]`);
        updateActiveNavLink(targetNavLink);
        
        // Smooth scroll to top of section
        const targetSection = document.getElementById(sectionId);
        if (targetSection) {
            targetSection.scrollIntoView({ 
                behavior: 'smooth',
                block: 'start'
            });
        }
    };

    /**
     * Utility functions
     */
    const Utils = {
        // Debounce function for performance
        debounce: function(func, wait, immediate) {
            let timeout;
            return function executedFunction() {
                const context = this;
                const args = arguments;
                const later = function() {
                    timeout = null;
                    if (!immediate) func.apply(context, args);
                };
                const callNow = immediate && !timeout;
                clearTimeout(timeout);
                timeout = setTimeout(later, wait);
                if (callNow) func.apply(context, args);
            };
        },

        // Check if element is in viewport
        isInViewport: function(element) {
            const rect = element.getBoundingClientRect();
            return (
                rect.top >= 0 &&
                rect.left >= 0 &&
                rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
                rect.right <= (window.innerWidth || document.documentElement.clientWidth)
            );
        },

        // Get current section from URL hash
        getCurrentSectionFromHash: function() {
            const hash = window.location.hash.substring(1);
            return hash || 'overview';
        }
    };

    /**
     * Initialize section based on URL hash
     */
    function initializeFromHash() {
        const currentSection = Utils.getCurrentSectionFromHash();
        showSection(currentSection);
        
        const targetNavLink = document.querySelector(`[data-section="${currentSection}"]`);
        updateActiveNavLink(targetNavLink);
    }

    /**
     * Add loading states for iframes
     */
    function addIframeLoadingStates() {
        const iframes = document.querySelectorAll('.viz-iframe');
        
        iframes.forEach(iframe => {
            // Add loading indicator
            const loadingDiv = document.createElement('div');
            loadingDiv.className = 'iframe-loading';
            loadingDiv.innerHTML = `
                <div class="loading-content">
                    <div class="loading"></div>
                    <p>Loading visualization...</p>
                </div>
            `;
            
            iframe.parentNode.insertBefore(loadingDiv, iframe);
            
            // Hide loading when iframe loads
            iframe.addEventListener('load', function() {
                loadingDiv.style.display = 'none';
                iframe.style.opacity = '1';
            });
            
            // Show error state if iframe fails to load
            iframe.addEventListener('error', function() {
                loadingDiv.innerHTML = `
                    <div class="error-content">
                        <i class="fas fa-exclamation-triangle"></i>
                        <p>Failed to load visualization</p>
                    </div>
                `;
            });
        });
    }

    /**
     * Performance monitoring
     */
    function initializePerformanceMonitoring() {
        // Monitor section change performance
        document.addEventListener('sectionChanged', function(e) {
            console.log(`📊 Section changed to: ${e.detail.sectionId}`);
        });

        // Monitor page load performance
        window.addEventListener('load', function() {
            if (performance && performance.timing) {
                const loadTime = performance.timing.loadEventEnd - performance.timing.navigationStart;
                console.log(`⚡ Page loaded in ${loadTime}ms`);
            }
        });
    }

    /**
     * Accessibility enhancements
     */
    function initializeAccessibility() {
        // Add keyboard navigation support
        document.addEventListener('keydown', function(e) {
            // Press 'h' to go to home/overview
            if (e.key === 'h' && !e.ctrlKey && !e.metaKey) {
                const focusedElement = document.activeElement;
                if (focusedElement.tagName !== 'INPUT' && focusedElement.tagName !== 'TEXTAREA') {
                    navigateToSection('overview');
                }
            }
        });

        // Add ARIA labels and roles where needed
        sections.forEach(section => {
            section.setAttribute('role', 'main');
            section.setAttribute('aria-label', `${section.id} section`);
        });

        // Add skip navigation link
        const skipLink = document.createElement('a');
        skipLink.href = '#main-content';
        skipLink.className = 'sr-only sr-only-focusable';
        skipLink.textContent = 'Skip to main content';
        document.body.insertBefore(skipLink, document.body.firstChild);
    }

    // Initialize additional features when DOM is ready
    document.addEventListener('DOMContentLoaded', function() {
        initializeFromHash();
        addIframeLoadingStates();
        initializePerformanceMonitoring();
        initializeAccessibility();
    });

    // Export utilities for global use if needed
    window.DashboardUtils = Utils;
})(); 