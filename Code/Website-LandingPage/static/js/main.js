/**
 * SignFlow Main JavaScript
 * Initialization and utility functions
 */

const safeStorage = {
    get(key) {
        try {
            return localStorage.getItem(key);
        } catch (error) {
            return null;
        }
    },
    set(key, value) {
        try {
            localStorage.setItem(key, value);
        } catch (error) {
            // Ignore storage errors (private mode, disabled storage, etc.)
        }
    },
    remove(key) {
        try {
            localStorage.removeItem(key);
        } catch (error) {
            // Ignore storage errors
        }
    }
};

const DOODLE_CONFIG = {
    minCount: 6,
    maxCount: 16,
    areaPerDoodle: 160000,
    minSize: 58,
    maxSize: 150,
    minOpacityLight: 0.12,
    maxOpacityLight: 0.18,
    minOpacityDark: 0.18,
    maxOpacityDark: 0.28,
    insetPadding: 6,
    edgePaddingPercent: 10,
    maxPlacementAttempts: 40,
    minSeparationFactor: 1.08
};

const DOODLE_ANIMATION_ENABLED = true;
const DOODLE_REBUILD_ON_RESIZE = false;
const DOODLE_REBUILD_ON_THEME_CHANGE = false;

const DOODLE_SVGS = (() => {
    const toDataUri = (svg) => `data:image/svg+xml,${encodeURIComponent(svg)}`;
    const buildSetGradient = (stops) => ([
        `<svg xmlns="http://www.w3.org/2000/svg" width="140" height="140" viewBox="0 0 140 140" fill="none"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">${stops}</linearGradient></defs><path d="M16 42 C 36 12, 60 72, 86 42 S 124 72, 124 96" stroke="url(#g)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
        `<svg xmlns="http://www.w3.org/2000/svg" width="120" height="120" viewBox="0 0 120 120" fill="none"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">${stops}</linearGradient></defs><circle cx="60" cy="60" r="18" stroke="url(#g)" stroke-width="2"/></svg>`,
        `<svg xmlns="http://www.w3.org/2000/svg" width="140" height="140" viewBox="0 0 140 140" fill="none"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">${stops}</linearGradient></defs><path d="M20 100 L70 30 L120 100 Z" stroke="url(#g)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
        `<svg xmlns="http://www.w3.org/2000/svg" width="120" height="120" viewBox="0 0 120 120" fill="none"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">${stops}</linearGradient></defs><path d="M60 12 L66 46 L100 52 L66 58 L60 96 L54 58 L20 52 L54 46 Z" stroke="url(#g)" stroke-width="2" stroke-linejoin="round"/></svg>`,
        `<svg xmlns="http://www.w3.org/2000/svg" width="140" height="140" viewBox="0 0 140 140" fill="none"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">${stops}</linearGradient></defs><path d="M20 70 C 20 40, 120 40, 120 70 C 120 100, 20 100, 20 70 Z" stroke="url(#g)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
        `<svg xmlns="http://www.w3.org/2000/svg" width="140" height="140" viewBox="0 0 140 140" fill="none"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">${stops}</linearGradient></defs><path d="M28 44 L52 20 L88 20 L112 44 L112 96 L88 120 L52 120 L28 96 Z" stroke="url(#g)" stroke-width="2" stroke-linejoin="round"/></svg>`,
        `<svg xmlns="http://www.w3.org/2000/svg" width="140" height="140" viewBox="0 0 140 140" fill="none"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">${stops}</linearGradient></defs><path d="M30 40 C 60 20, 90 20, 110 40 C 90 60, 60 60, 30 40 Z" stroke="url(#g)" stroke-width="2" stroke-linecap="round"/></svg>`,
        `<svg xmlns="http://www.w3.org/2000/svg" width="140" height="140" viewBox="0 0 140 140" fill="none"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">${stops}</linearGradient></defs><path d="M20 30 L120 30 L120 40 L20 40 Z M20 65 L120 65 L120 75 L20 75 Z M20 100 L120 100 L120 110 L20 110 Z" stroke="url(#g)" stroke-width="2"/></svg>`,
        `<svg xmlns="http://www.w3.org/2000/svg" width="140" height="140" viewBox="0 0 140 140" fill="none"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">${stops}</linearGradient></defs><path d="M70 16 L90 46 L124 52 L98 76 L106 112 L70 94 L34 112 L42 76 L16 52 L50 46 Z" stroke="url(#g)" stroke-width="2" stroke-linejoin="round"/></svg>`,
        `<svg xmlns="http://www.w3.org/2000/svg" width="140" height="140" viewBox="0 0 140 140" fill="none"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">${stops}</linearGradient></defs><path d="M20 90 C 40 60, 60 120, 80 90 C 100 60, 120 120, 120 90" stroke="url(#g)" stroke-width="2" stroke-linecap="round"/></svg>`,
        `<svg xmlns="http://www.w3.org/2000/svg" width="140" height="140" viewBox="0 0 140 140" fill="none"><defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">${stops}</linearGradient></defs><rect x="28" y="28" width="84" height="84" rx="18" stroke="url(#g)" stroke-width="2"/></svg>`
    ]);
    const buildSetSolid = (stroke) => ([
        `<svg xmlns="http://www.w3.org/2000/svg" width="140" height="140" viewBox="0 0 140 140" fill="none"><path d="M16 42 C 36 12, 60 72, 86 42 S 124 72, 124 96" stroke="${stroke}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
        `<svg xmlns="http://www.w3.org/2000/svg" width="120" height="120" viewBox="0 0 120 120" fill="none"><circle cx="60" cy="60" r="18" stroke="${stroke}" stroke-width="2"/></svg>`,
        `<svg xmlns="http://www.w3.org/2000/svg" width="140" height="140" viewBox="0 0 140 140" fill="none"><path d="M20 100 L70 30 L120 100 Z" stroke="${stroke}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
        `<svg xmlns="http://www.w3.org/2000/svg" width="120" height="120" viewBox="0 0 120 120" fill="none"><path d="M60 12 L66 46 L100 52 L66 58 L60 96 L54 58 L20 52 L54 46 Z" stroke="${stroke}" stroke-width="2" stroke-linejoin="round"/></svg>`,
        `<svg xmlns="http://www.w3.org/2000/svg" width="140" height="140" viewBox="0 0 140 140" fill="none"><path d="M20 70 C 20 40, 120 40, 120 70 C 120 100, 20 100, 20 70 Z" stroke="${stroke}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>`,
        `<svg xmlns="http://www.w3.org/2000/svg" width="140" height="140" viewBox="0 0 140 140" fill="none"><path d="M28 44 L52 20 L88 20 L112 44 L112 96 L88 120 L52 120 L28 96 Z" stroke="${stroke}" stroke-width="2" stroke-linejoin="round"/></svg>`,
        `<svg xmlns="http://www.w3.org/2000/svg" width="140" height="140" viewBox="0 0 140 140" fill="none"><path d="M30 40 C 60 20, 90 20, 110 40 C 90 60, 60 60, 30 40 Z" stroke="${stroke}" stroke-width="2" stroke-linecap="round"/></svg>`,
        `<svg xmlns="http://www.w3.org/2000/svg" width="140" height="140" viewBox="0 0 140 140" fill="none"><path d="M20 30 L120 30 L120 40 L20 40 Z M20 65 L120 65 L120 75 L20 75 Z M20 100 L120 100 L120 110 L20 110 Z" stroke="${stroke}" stroke-width="2"/></svg>`,
        `<svg xmlns="http://www.w3.org/2000/svg" width="140" height="140" viewBox="0 0 140 140" fill="none"><path d="M70 16 L90 46 L124 52 L98 76 L106 112 L70 94 L34 112 L42 76 L16 52 L50 46 Z" stroke="${stroke}" stroke-width="2" stroke-linejoin="round"/></svg>`,
        `<svg xmlns="http://www.w3.org/2000/svg" width="140" height="140" viewBox="0 0 140 140" fill="none"><path d="M20 90 C 40 60, 60 120, 80 90 C 100 60, 120 120, 120 90" stroke="${stroke}" stroke-width="2" stroke-linecap="round"/></svg>`,
        `<svg xmlns="http://www.w3.org/2000/svg" width="140" height="140" viewBox="0 0 140 140" fill="none"><rect x="28" y="28" width="84" height="84" rx="18" stroke="${stroke}" stroke-width="2"/></svg>`
    ]);

    return {
        light: buildSetSolid('#6b7280').map(toDataUri),
        dark: buildSetGradient('<stop offset="0%" stop-color="#22d3ee"/><stop offset="50%" stop-color="#60a5fa"/><stop offset="100%" stop-color="#a855f7"/>').map(toDataUri)
    };
})();

let doodleResizeTimer;
let iconGradientCounter = 0;

function prefersReducedMotion() {
    return window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

function isDarkTheme() {
    return (document.documentElement.getAttribute('data-theme') || 'light') === 'dark';
}

function getIconGradientStops() {
    const rootStyles = getComputedStyle(document.documentElement);
    return [
        { offset: '0%', color: rootStyles.getPropertyValue('--icon-gradient-start').trim() || '#a855f7' },
        { offset: '55%', color: rootStyles.getPropertyValue('--icon-gradient-mid').trim() || '#60a5fa' },
        { offset: '100%', color: rootStyles.getPropertyValue('--icon-gradient-end').trim() || '#22d3ee' }
    ];
}

function ensureSvgGradient(svg) {
    if (!svg) return null;

    let defs = svg.querySelector('defs');
    if (!defs) {
        defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
        svg.insertBefore(defs, svg.firstChild);
    }

    let gradientId = svg.dataset.signflowGradientId;
    if (!gradientId) {
        iconGradientCounter += 1;
        gradientId = `signflow-icon-gradient-${iconGradientCounter}`;
        svg.dataset.signflowGradientId = gradientId;
    }

    let gradient = defs.querySelector(`#${gradientId}`);
    if (!gradient) {
        gradient = document.createElementNS('http://www.w3.org/2000/svg', 'linearGradient');
        gradient.setAttribute('id', gradientId);
        gradient.setAttribute('data-signflow-icon-gradient', 'true');
        defs.insertBefore(gradient, defs.firstChild);
    }

    gradient.setAttribute('x1', '0');
    gradient.setAttribute('y1', '1');
    gradient.setAttribute('x2', '1');
    gradient.setAttribute('y2', '0');
    gradient.replaceChildren();

    getIconGradientStops().forEach(({ offset, color }) => {
        const stop = document.createElementNS('http://www.w3.org/2000/svg', 'stop');
        stop.setAttribute('offset', offset);
        stop.setAttribute('stop-color', color);
        gradient.appendChild(stop);
    });

    return `url(#${gradientId})`;
}

function clearGradientFromSvg(svg, options = {}) {
    const {
        rootStroke = false,
        rootFill = false,
        strokeSelectors = [],
        fillSelectors = []
    } = options;

    if (!svg) return;

    if (rootStroke) {
        svg.style.removeProperty('stroke');
    }

    if (rootFill) {
        svg.style.removeProperty('fill');
    }

    strokeSelectors.forEach((selector) => {
        svg.querySelectorAll(selector).forEach((element) => {
            element.style.removeProperty('stroke');
        });
    });

    fillSelectors.forEach((selector) => {
        svg.querySelectorAll(selector).forEach((element) => {
            element.style.removeProperty('fill');
        });
    });

    const gradientId = svg.dataset.signflowGradientId;
    if (!gradientId) return;

    const defs = svg.querySelector('defs');
    const gradient = defs?.querySelector(`#${gradientId}`);
    if (gradient) {
        gradient.remove();
    }

    if (defs && !defs.children.length) {
        defs.remove();
    }

    delete svg.dataset.signflowGradientId;
}

function applyGradientToSvg(svg, options = {}) {
    const {
        rootStroke = false,
        rootFill = false,
        strokeSelectors = [],
        fillSelectors = []
    } = options;

    const gradientRef = ensureSvgGradient(svg);
    if (!gradientRef) return;

    if (rootStroke) {
        svg.style.stroke = gradientRef;
    }

    if (rootFill) {
        svg.style.fill = gradientRef;
    }

    strokeSelectors.forEach((selector) => {
        svg.querySelectorAll(selector).forEach((element) => {
            element.style.stroke = gradientRef;
        });
    });

    fillSelectors.forEach((selector) => {
        svg.querySelectorAll(selector).forEach((element) => {
            element.style.fill = gradientRef;
        });
    });
}

function applyGradientToDocument(root = document) {
    if (!isDarkTheme()) {
        root.querySelectorAll('svg.lucide, svg.hand-svg').forEach((svg) => {
            clearGradientFromSvg(svg, { rootStroke: true });
        });

        root.querySelectorAll('.theme-toggle svg').forEach((svg) => {
            clearGradientFromSvg(svg, { rootStroke: true });
        });

        root.querySelectorAll('.pipeline-connector svg').forEach((svg) => {
            clearGradientFromSvg(svg, {
                strokeSelectors: ['line', 'path', 'polyline', 'rect', 'circle', 'ellipse'],
                fillSelectors: ['polygon']
            });
        });

        root.querySelectorAll('.cursor-icon').forEach((svg) => {
            clearGradientFromSvg(svg, {
                strokeSelectors: ['path'],
                fillSelectors: ['path']
            });
        });

        return;
    }

    root.querySelectorAll('svg.lucide, svg.hand-svg').forEach((svg) => {
        applyGradientToSvg(svg, { rootStroke: true });
    });

    root.querySelectorAll('.theme-toggle svg').forEach((svg) => {
        applyGradientToSvg(svg, { rootStroke: true });
    });

    root.querySelectorAll('.pipeline-connector svg').forEach((svg) => {
        applyGradientToSvg(svg, {
            strokeSelectors: ['line', 'path', 'polyline', 'rect', 'circle', 'ellipse'],
            fillSelectors: ['polygon']
        });
    });

    root.querySelectorAll('.cursor-icon').forEach((svg) => {
        applyGradientToSvg(svg, {
            strokeSelectors: ['path'],
            fillSelectors: ['path']
        });
    });
}

window.SignFlowIconGradient = {
    applyToSvg: applyGradientToSvg,
    applyToDocument: applyGradientToDocument,
    ensureSvgGradient,
    isDarkTheme
};

function initLucideIcons() {
    document.querySelectorAll('.icon-stage[data-lucide="align-left"]').forEach((icon) => {
        const stageTitle = icon.closest('.pipeline-content')?.querySelector('h3')?.textContent?.trim();
        if (stageTitle === 'LLM Smoothing') {
            icon.setAttribute('data-lucide', 'sparkles');
        }
    });

    if (window.lucide && typeof window.lucide.createIcons === 'function') {
        window.lucide.createIcons({
            attrs: {
                'stroke-width': 1.75
            }
        });
    }

    applyGradientToDocument(document);
}

function isHomePage() {
    return Boolean(document.querySelector('.hero'));
}

function getDoodleSet() {
    const theme = document.documentElement.getAttribute('data-theme') || 'light';
    return theme === 'dark' ? DOODLE_SVGS.dark : DOODLE_SVGS.light;
}

function getDoodleOpacityRange() {
    const theme = document.documentElement.getAttribute('data-theme') || 'light';
    if (theme === 'dark') {
        return { min: DOODLE_CONFIG.minOpacityDark, max: DOODLE_CONFIG.maxOpacityDark };
    }
    return { min: DOODLE_CONFIG.minOpacityLight, max: DOODLE_CONFIG.maxOpacityLight };
}

function buildDoodlesForSection(section, doodles) {
    if (!section) return;

    let layer = section.querySelector('.doodle-layer');
    if (!layer) {
        layer = document.createElement('div');
        layer.className = 'doodle-layer';
        layer.setAttribute('aria-hidden', 'true');
        section.insertBefore(layer, section.firstChild);
    }

    layer.innerHTML = '';

    const sectionWidth = section.offsetWidth;
    const sectionHeight = section.offsetHeight;
    const area = sectionWidth * sectionHeight;
    const estimated = Math.round(area / DOODLE_CONFIG.areaPerDoodle);
    const count = Math.min(
        DOODLE_CONFIG.maxCount,
        Math.max(DOODLE_CONFIG.minCount, estimated)
    );

    const opacityRange = getDoodleOpacityRange();
    const placed = [];
    const horizontalPadding = Math.max(sectionWidth * (DOODLE_CONFIG.insetPadding / 100), 12);
    const verticalPadding = Math.max(sectionHeight * (DOODLE_CONFIG.edgePaddingPercent / 100), 18);

    for (let i = 0; i < count; i += 1) {
        let attempts = 0;
        let placedDoodle = null;

        while (attempts < DOODLE_CONFIG.maxPlacementAttempts && !placedDoodle) {
            const size = DOODLE_CONFIG.minSize + Math.random() * (DOODLE_CONFIG.maxSize - DOODLE_CONFIG.minSize);
            const maxLeft = Math.max(horizontalPadding, sectionWidth - horizontalPadding - size);
            const maxTop = Math.max(verticalPadding, sectionHeight - verticalPadding - size);
            const leftPx = horizontalPadding + Math.random() * Math.max(1, maxLeft - horizontalPadding);
            const topPx = verticalPadding + Math.random() * Math.max(1, maxTop - verticalPadding);
            const centerX = leftPx + size / 2;
            const centerY = topPx + size / 2;

            const hasOverlap = placed.some(item => {
                const dx = centerX - item.centerX;
                const dy = centerY - item.centerY;
                const distance = Math.hypot(dx, dy);
                const minDistance = (size + item.size) * 0.5 * DOODLE_CONFIG.minSeparationFactor;
                return distance < minDistance;
            });

            if (!hasOverlap) {
                placedDoodle = { size, leftPx, topPx, centerX, centerY };
            }

            attempts += 1;
        }

        if (!placedDoodle) {
            continue;
        }

        const doodle = document.createElement('span');
        doodle.className = 'doodle doodle--flow';
        const direction = Math.random() < 0.5 ? 1 : -1;
        const driftDistance = 10 + Math.random() * 14;
        const tiltFactor = 0.12 + Math.random() * 0.2;
        const verticalSign = Math.random() < 0.5 ? -1 : 1;
        const driftX = direction * driftDistance;
        const driftY = verticalSign * driftDistance * tiltFactor;
        doodle.style.width = `${placedDoodle.size.toFixed(0)}px`;
        doodle.style.height = `${placedDoodle.size.toFixed(0)}px`;
        doodle.style.left = `${placedDoodle.leftPx.toFixed(1)}px`;
        doodle.style.top = `${placedDoodle.topPx.toFixed(1)}px`;
        doodle.style.setProperty('--doodle-opacity', (opacityRange.min + Math.random() * (opacityRange.max - opacityRange.min)).toFixed(2));
        doodle.style.backgroundImage = `url("${doodles[Math.floor(Math.random() * doodles.length)]}")`;
        doodle.style.setProperty('--doodle-rotate', `${Math.round(Math.random() * 360)}deg`);
        doodle.style.setProperty('--doodle-duration', `${16 + Math.random() * 12}s`);
        doodle.style.setProperty('--doodle-delay', `${(Math.random() * 6).toFixed(2)}s`);
        doodle.style.setProperty('--doodle-dx', `${driftX.toFixed(1)}px`);
        doodle.style.setProperty('--doodle-dy', `${driftY.toFixed(1)}px`);
        if (!DOODLE_ANIMATION_ENABLED || prefersReducedMotion()) {
            doodle.classList.add('doodle--static');
        }

        placed.push(placedDoodle);
        layer.appendChild(doodle);
    }
}

function initDoodleLayers() {
    const sections = document.querySelectorAll('section, .footer');
    const doodles = getDoodleSet();
    sections.forEach(section => buildDoodlesForSection(section, doodles));
}

// Detect user's system theme preference
function getSystemTheme() {
    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
        return 'dark';
    }
    return 'light';
}

// Navigation state
let lastScrollTime = 0;
let scrollTimeout;
const SCROLL_DEBOUNCE = 100;
let suppressScrollSpyUntil = 0;

// Initialize application
function initApp() {
    // Check for saved theme preference
    const savedTheme = safeStorage.get('signflow-theme');
    const theme = savedTheme || getSystemTheme();

    // Apply theme
    document.documentElement.setAttribute('data-theme', theme);

    // Initialize random background doodles
    initDoodleLayers();

    // Initialize SVG icons
    initLucideIcons();

    // Initialize intersection observer for animations
    initIntersectionObserver();

    // Add event listeners
    setupEventListeners();

    // Initialize mobile navigation
    initMobileNav();

    if (isHomePage()) {
        // Initialize hash-based navigation
        initHashNavigation();

        // Handle initial hash after DOM ready
        setTimeout(() => {
            handleHashNavigation();
            updateNavState();
        }, 150);
    }

    if (DOODLE_REBUILD_ON_THEME_CHANGE) {
        window.addEventListener('themechange', () => {
            initDoodleLayers();
        });
    }

    window.addEventListener('themechange', () => {
        applyGradientToDocument(document);
    });

    if (DOODLE_REBUILD_ON_RESIZE) {
        window.addEventListener('resize', () => {
            clearTimeout(doodleResizeTimer);
            doodleResizeTimer = setTimeout(initDoodleLayers, 200);
        }, { passive: true });
    }
}

// Hash-based navigation system
function initHashNavigation() {
    if (!isHomePage()) return;

    const navLinks = document.querySelectorAll('.navbar-menu a[data-scroll]');

    navLinks.forEach(link => {
        link.addEventListener('click', (e) => {
            if (!isHomePage()) return;

            const targetHash = link.hash;
            if (!targetHash) return;

            const targetSection = targetHash === '#home'
                ? document.querySelector('.hero')
                : document.querySelector(targetHash);

            if (!targetSection) return;

            e.preventDefault();
            suppressScrollSpyUntil = Date.now() + 1200;

            if (window.location.hash !== targetHash) {
                window.location.hash = targetHash;
            } else {
                handleHashNavigation();
                updateNavState();
            }
        }, { passive: false });
    });

    // Listen for hash changes
    window.addEventListener('hashchange', () => {
        updateNavState();
        handleHashNavigation();
    }, { passive: true });
}

function scrollToSection(targetSection) {
    const behavior = prefersReducedMotion() ? 'auto' : 'smooth';
    targetSection.scrollIntoView({ behavior });
}

// Handle navigation to hash section
function handleHashNavigation() {
    if (!isHomePage()) return;

    const hash = window.location.hash || '#home';
    const targetSection = hash === '#home'
        ? document.querySelector('.hero')
        : document.querySelector(hash);

    if (targetSection) {
        suppressScrollSpyUntil = Math.max(suppressScrollSpyUntil, Date.now() + 1200);
        scrollToSection(targetSection);
        updateNavState();
    }
}

// Update navigation state (underline position)
function updateNavState() {
    if (!isHomePage()) return;

    const hash = window.location.hash || '#home';
    const navLinks = document.querySelectorAll('.navbar-menu a[data-scroll]');
    const underline = document.querySelector('.nav-underline');

    if (!underline || !navLinks.length) return;

    let activeLink = null;

    navLinks.forEach(link => {
        if (link.hash === hash) {
            activeLink = link;
        }
    });

    if (activeLink) {
        positionUnderline(activeLink, underline);
    }
}

// Position underline under active link
function positionUnderline(link, underline) {
    const menu = document.querySelector('.navbar-menu');
    if (!menu) return;

    const menuRect = menu.getBoundingClientRect();
    if (menuRect.width === 0 || menuRect.height === 0) return;

    const rect = link.getBoundingClientRect();
    const left = rect.left - menuRect.left;
    const width = rect.width;

    underline.style.left = left + 'px';
    underline.style.width = width + 'px';
}

// Setup intersection observer for scroll animations
function initIntersectionObserver() {
    const animatedItems = document.querySelectorAll('[data-animation]');

    if (!animatedItems.length) return;

    if (!('IntersectionObserver' in window) || prefersReducedMotion()) {
        animatedItems.forEach(el => el.classList.add('animated'));
        return;
    }

    const options = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const animationType = entry.target.getAttribute('data-animation');
                if (animationType) {
                    entry.target.classList.add('animated');
                }
                observer.unobserve(entry.target);
            }
        });
    }, options);

    // Observe all elements with animation attributes
    animatedItems.forEach(el => {
        observer.observe(el);
    });
}

// Setup general event listeners
function setupEventListeners() {
    if (isHomePage()) {
        // Debounced scroll handler for nav updates
        window.addEventListener('scroll', () => {
            const now = Date.now();
            if (now - lastScrollTime < SCROLL_DEBOUNCE) return;
            lastScrollTime = now;

            clearTimeout(scrollTimeout);
            scrollTimeout = setTimeout(updateNavFromScroll, SCROLL_DEBOUNCE);
        }, { passive: true });

        // Update underline on resize
        window.addEventListener('resize', updateNavState, { passive: true });
    }
}

// Mobile navigation toggle
function initMobileNav() {
    const toggle = document.getElementById('nav-toggle');
    const menu = document.getElementById('nav-menu');

    if (!toggle || !menu) return;

    const setExpanded = (isOpen) => {
        toggle.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
        toggle.classList.toggle('is-open', isOpen);
        menu.classList.toggle('is-open', isOpen);
    };

    const closeMenu = () => setExpanded(false);

    toggle.addEventListener('click', (event) => {
        event.stopPropagation();
        const isOpen = menu.classList.contains('is-open');
        setExpanded(!isOpen);
    });

    document.addEventListener('click', (event) => {
        if (!menu.classList.contains('is-open')) return;
        if (menu.contains(event.target) || toggle.contains(event.target)) return;
        closeMenu();
    });

    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') {
            closeMenu();
        }
    });

    menu.querySelectorAll('a').forEach(link => {
        link.addEventListener('click', () => closeMenu());
    });

    window.addEventListener('resize', () => {
        if (window.innerWidth > 768) {
            closeMenu();
        }
    }, { passive: true });
}

// Update nav based on scroll position
function updateNavFromScroll() {
    if (!isHomePage()) return;
    if (Date.now() < suppressScrollSpyUntil) return;

    const scrollPos = window.scrollY + 150;
    const sections = [
        { hash: '#home', element: document.querySelector('.hero'), top: 0 },
        { hash: '#demo', element: document.querySelector('#demo'), top: 0 },
        { hash: '#why-matters', element: document.querySelector('#why-matters'), top: 0 },
        { hash: '#how-works', element: document.querySelector('#how-works'), top: 0 },
        { hash: '#download', element: document.querySelector('#download'), top: 0 },
        { hash: '#donate', element: document.querySelector('#donate'), top: 0 },
        { hash: '#login', element: document.querySelector('#login'), top: 0 }
    ];

    let activeHash = '#home';

    for (let section of sections) {
        if (section.element) {
            section.top = section.element.offsetTop;
        }
    }

    for (let i = 0; i < sections.length; i++) {
        const current = sections[i];
        const next = sections[i + 1];

        if (scrollPos >= current.top && (!next || scrollPos < next.top)) {
            activeHash = current.hash;
            break;
        }
    }

    if (window.location.hash !== activeHash) {
        history.replaceState(null, null, activeHash);
        updateNavState();
    }
}

// Utility function to add CSS class with animation
function addAnimationClass(element, animationClass, onComplete) {
    element.classList.add(animationClass);

    if (onComplete) {
        element.addEventListener('animationend', () => {
            onComplete();
        }, { once: true });
    }
}

// Initialize app when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initApp);
} else {
    initApp();
}

// Export functions for use in other scripts
window.SignFlow = {
    getSystemTheme,
    initIntersectionObserver,
    addAnimationClass
};
