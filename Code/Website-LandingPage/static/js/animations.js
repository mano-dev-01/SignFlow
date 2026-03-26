/**
 * SignFlow Animations
 * Handles various page animations and effects
 */

function prefersReducedMotion() {
    return window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

const MOTION = {
    fade: 1100,
    logoHover: 400,
    logoLoad: 800,
    pulse: 700,
    slide: 850,
    scale: 600,
    stagger: 120
};

const MOTION_EASE = 'cubic-bezier(0.22, 0.61, 0.36, 1)';

class SignFlowAnimations {
    constructor() {
        this.init();
    }

    init() {
        this.setupFadeInAnimations();
        this.setupLogoAnimation();
        this.setupHeroAnimations();
        this.setupScrollAnimations();
    }

    setupFadeInAnimations() {
        // Elements with data-animation attribute
        const animatedElements = document.querySelectorAll('[data-animation]');

        if (!animatedElements.length) return;

        if (prefersReducedMotion()) {
            animatedElements.forEach(element => {
                element.style.opacity = '1';
                element.style.animation = 'none';
            });
            return;
        }

        animatedElements.forEach((element, index) => {
            const animationType = element.getAttribute('data-animation');
            
            // Add initial styles
            element.style.opacity = '0';
            element.style.animation = 'none';
            
            // Create CSS animation based on type
            const delay = index * MOTION.stagger; // Stagger animation
            const styleName = `animation-${animationType}-${index}`;
            
            if (animationType === 'fade-in-down') {
                this.applyFadeInDown(element, delay);
            } else if (animationType === 'fade-in-up') {
                this.applyFadeInUp(element, delay);
            }
        });
    }

    applyFadeInDown(element, delay) {
        element.style.animation = `fade-in-down ${MOTION.fade}ms ${MOTION_EASE} ${delay}ms forwards`;
    }

    applyFadeInUp(element, delay) {
        element.style.animation = `fade-in-up ${MOTION.fade}ms ${MOTION_EASE} ${delay}ms forwards`;
    }

    setupLogoAnimation() {
        const logo = document.querySelector('.logo-svg');
        if (logo) {
            logo.addEventListener('mouseenter', () => {
                logo.style.animation = `logo-hover ${MOTION.logoHover}ms ${MOTION_EASE}`;
            });

            // Auto-animate on load
            window.addEventListener('load', () => {
                logo.style.animation = `logo-hover ${MOTION.logoLoad}ms ${MOTION_EASE}`;
            });
        }
    }

    setupHeroAnimations() {
        const hero = document.querySelector('.hero');
        if (!hero || prefersReducedMotion()) return;

        // Parallax effect on scroll (smoothed)
        const doodles = document.querySelectorAll('.animated-hand-doodle');
        let latestScroll = 0;
        let ticking = false;

        const updateDoodles = () => {
            doodles.forEach((doodle, index) => {
                const speed = 0.22 + (index * 0.05);
                doodle.style.transform = `translate3d(0, ${latestScroll * speed}px, 0)`;
            });
            ticking = false;
        };

        window.addEventListener('scroll', () => {
            latestScroll = window.pageYOffset;
            if (!ticking) {
                window.requestAnimationFrame(updateDoodles);
                ticking = true;
            }
        }, { passive: true });

        // Subtle glow effect on hero title
        const heroTitle = document.querySelector('.hero-title');
        if (heroTitle) {
            heroTitle.addEventListener('mouseenter', () => {
                heroTitle.style.textShadow = '0 0 20px rgba(37, 99, 235, 0.2)';
            });

            heroTitle.addEventListener('mouseleave', () => {
                heroTitle.style.textShadow = 'none';
            });
        }
    }

    setupScrollAnimations() {
        // Create intersection observer for scroll-triggered animations
        if (prefersReducedMotion()) {
            document.querySelectorAll(
                '.stat-card, .step, .platform-card, .download-card, .tech-item, .donation-card'
            ).forEach(element => {
                element.classList.add('animated');
            });
            return;
        }

        if (!('IntersectionObserver' in window)) {
            document.querySelectorAll(
                '.stat-card, .step, .platform-card, .download-card, .tech-item, .donation-card'
            ).forEach(element => {
                element.classList.add('animated');
            });
            return;
        }

        const observerOptions = {
            threshold: 0.1,
            rootMargin: '0px 0px -100px 0px'
        };

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    // Add animation class to trigger CSS animation
                    entry.target.classList.add('animated');
                    
                    // Specific animations for different element types
                    if (entry.target.classList.contains('stat-card')) {
                        this.animateStatCard(entry.target);
                    } else if (entry.target.classList.contains('step')) {
                        this.animateStep(entry.target);
                    } else if (entry.target.classList.contains('platform-card')) {
                        this.animatePlatformCard(entry.target);
                    }
                }
            });
        }, observerOptions);

        // Observe elements
        document.querySelectorAll(
            '.stat-card, .step, .platform-card, .download-card, .tech-item, .donation-card'
        ).forEach(element => {
            observer.observe(element);
        });
    }

    animateStatCard(element) {
        element.style.animation = `pulse-in ${MOTION.pulse}ms ${MOTION_EASE}`;
    }

    animateStep(element) {
        element.style.animation = `slide-in-up ${MOTION.slide}ms ${MOTION_EASE}`;
    }

    animatePlatformCard(element) {
        element.style.animation = `scale-in ${MOTION.scale}ms ${MOTION_EASE}`;
    }
}

// Add CSS animations to the document
function injectAnimationStyles() {
    const style = document.createElement('style');
    style.textContent = `
        @keyframes pulse-in {
            0% {
                opacity: 0;
                transform: scale(0.95);
            }
            100% {
                opacity: 1;
                transform: scale(1);
            }
        }

        @keyframes slide-in-up {
            0% {
                opacity: 0;
                transform: translateY(30px);
            }
            100% {
                opacity: 1;
                transform: translateY(0);
            }
        }

        @keyframes scale-in {
            0% {
                opacity: 0;
                transform: scale(0.9);
            }
            100% {
                opacity: 1;
                transform: scale(1);
            }
        }

        @keyframes float-in {
            0% {
                opacity: 0;
                transform: translateY(20px);
            }
            100% {
                opacity: 1;
                transform: translateY(0);
            }
        }
    `;
    document.head.appendChild(style);
}

// Initialize animations
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        injectAnimationStyles();
        new SignFlowAnimations();
    });
} else {
    injectAnimationStyles();
    new SignFlowAnimations();
}

// Export for use in other scripts
window.SignFlowAnimations = SignFlowAnimations;
