// Y2K Hip-Hop JavaScript for Summit Application
let effectsEnabled = true;
let matrixContainer = null;

document.addEventListener('DOMContentLoaded', function() {
    console.log('🔥 NEXUS AI LOADED - READY TO BALL! 🔥');
    
    // Initialize effects toggle
    initializeEffectsToggle();
    
    // Add some Y2K matrix-style effects
    if (effectsEnabled) {
        createMatrixRain();
    }
    
    // Add smooth scrolling for anchor links with some swagger
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
    
    // Add click handler for CTA button with 2000s energy
    const ctaButton = document.querySelector('.cta-button');
    if (ctaButton) {
        ctaButton.addEventListener('click', function() {
            // Create some bling effects
            if (effectsEnabled) {
                createBlingEffect(this);
            }
            alert('YO! Welcome to NEXUS AI! Time to level up! 💎✨');
        });
    }
    
    // Add intersection observer for feature cards with hip-hop flair
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };
    
    const observer = new IntersectionObserver(function(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                if (effectsEnabled) {
                    entry.target.style.transform = 'translateY(0) rotateX(0deg)';
                    // Add some bling when cards appear
                    setTimeout(() => createBlingEffect(entry.target), 500);
                } else {
                    entry.target.style.transform = 'translateY(0)';
                }
            }
        });
    }, observerOptions);
    
    document.querySelectorAll('.feature-card').forEach(card => {
        card.style.opacity = '0';
        if (effectsEnabled) {
            card.style.transform = 'translateY(50px) rotateX(20deg)';
        } else {
            card.style.transform = 'translateY(50px)';
        }
        card.style.transition = 'opacity 0.8s ease, transform 0.8s ease';
        observer.observe(card);
    });
});

function initializeEffectsToggle() {
    const effectsSwitch = document.getElementById('effects-switch');
    if (effectsSwitch) {
        // Load saved preference
        const savedPreference = localStorage.getItem('effectsEnabled');
        if (savedPreference !== null) {
            effectsEnabled = savedPreference === 'true';
            effectsSwitch.checked = effectsEnabled;
        }
        
        // Apply initial state
        toggleEffects(effectsEnabled);
        
        // Add event listener
        effectsSwitch.addEventListener('change', function() {
            effectsEnabled = this.checked;
            localStorage.setItem('effectsEnabled', effectsEnabled.toString());
            toggleEffects(effectsEnabled);
        });
    }
}

function toggleEffects(enabled) {
    if (enabled) {
        document.body.classList.remove('effects-disabled');
        if (!matrixContainer) {
            createMatrixRain();
        }
    } else {
        document.body.classList.add('effects-disabled');
        if (matrixContainer) {
            matrixContainer.remove();
            matrixContainer = null;
        }
    }
}

// Matrix rain effect for that Y2K vibe
function createMatrixRain() {
    const chars = '01アイウエオカキクケコサシスセソタチツテト';
    matrixContainer = document.createElement('div');
    matrixContainer.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        pointer-events: none;
        z-index: 1;
        overflow: hidden;
    `;
    
    for (let i = 0; i < 50; i++) {
        const span = document.createElement('span');
        span.textContent = chars[Math.floor(Math.random() * chars.length)];
        span.style.cssText = `
            position: absolute;
            color: #00FF00;
            font-family: monospace;
            font-size: 14px;
            left: ${Math.random() * 100}%;
            animation: fall ${3 + Math.random() * 3}s linear infinite;
            animation-delay: ${Math.random() * 3}s;
            opacity: 0.3;
        `;
        matrixContainer.appendChild(span);
    }
    
    document.body.appendChild(matrixContainer);
    
    // Add CSS animation
    const style = document.createElement('style');
    style.textContent = `
        @keyframes fall {
            0% { transform: translateY(-100vh); }
            100% { transform: translateY(100vh); }
        }
    `;
    document.head.appendChild(style);
}

// Bling effect for interactive elements
function createBlingEffect(element) {
    const bling = document.createElement('div');
    bling.style.cssText = `
        position: absolute;
        width: 20px;
        height: 20px;
        background: #FFD700;
        border-radius: 50%;
        pointer-events: none;
        z-index: 9999;
        box-shadow: 0 0 20px #FFD700;
        animation: bling-sparkle 1s ease-out forwards;
    `;
    
    const rect = element.getBoundingClientRect();
    bling.style.left = (rect.left + Math.random() * rect.width) + 'px';
    bling.style.top = (rect.top + Math.random() * rect.height) + 'px';
    
    document.body.appendChild(bling);
    
    // Add sparkle animation
    const style = document.createElement('style');
    style.textContent = `
        @keyframes bling-sparkle {
            0% { 
                transform: scale(0) rotate(0deg);
                opacity: 1;
            }
            50% {
                transform: scale(1.5) rotate(180deg);
                opacity: 0.8;
            }
            100% { 
                transform: scale(0) rotate(360deg);
                opacity: 0;
            }
        }
    `;
    document.head.appendChild(style);
    
    setTimeout(() => bling.remove(), 1000);
}
