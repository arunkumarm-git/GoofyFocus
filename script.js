document.addEventListener('DOMContentLoaded', () => {
    /* ==========================================================================
       1. App Mockup View Switcher & Mascot Interactivity
       ========================================================================== */
    const tabButtons = document.querySelectorAll('.app-nav-btn');
    const screenshots = document.querySelectorAll('.app-screenshot');
    const viewLabel = document.getElementById('mockup-current-view');
    const normalToggle = document.getElementById('btn-toggle-normal');
    const breakToggle = document.getElementById('btn-toggle-break');
    const mascotAvatar = document.getElementById('mascot-avatar');
    const mascotBubble = document.getElementById('mascot-speech-bubble');
    const mascotTear = document.getElementById('mascot-tear');
    const muteBtn = document.getElementById('app-mute-btn');

    let activeTab = 'sessions';
    let isBreakOverlayActive = false;

    // Helper to switch mockup screenshots
    function updateMockupView() {
        screenshots.forEach(ss => ss.classList.remove('active'));
        
        if (isBreakOverlayActive) {
            document.getElementById('ss-break').classList.add('active');
            viewLabel.textContent = 'Break Overlay View';
            normalToggle.classList.remove('active');
            breakToggle.classList.add('active');
        } else {
            const targetScreenshot = document.getElementById(`ss-${activeTab}`);
            if (targetScreenshot) {
                targetScreenshot.classList.add('active');
            }
            viewLabel.textContent = `${activeTab} view`;
            normalToggle.classList.add('active');
            breakToggle.classList.remove('active');
        }

        // Mascot state changes: on account page, mascot is logged in/happy. Otherwise, sad.
        if (activeTab === 'account' && !isBreakOverlayActive) {
            mascotAvatar.classList.remove('sad');
            mascotAvatar.style.background = 'linear-gradient(135deg, #FCD34D, #F59E0B)';
        } else if (activeTab === 'analytics' || activeTab === 'settings') {
            mascotAvatar.classList.remove('sad');
            mascotAvatar.style.background = 'linear-gradient(135deg, #FCD34D, #F59E0B)';
        } else {
            // Sad mascot on sessions tab or break overlay to remind user
            mascotAvatar.classList.add('sad');
        }
    }

    // Tab button click
    tabButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            tabButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            activeTab = btn.getAttribute('data-tab');
            isBreakOverlayActive = false;
            updateMockupView();
        });
    });

    // Mockup Mode Toggles
    normalToggle.addEventListener('click', () => {
        isBreakOverlayActive = false;
        updateMockupView();
    });

    breakToggle.addEventListener('click', () => {
        isBreakOverlayActive = true;
        updateMockupView();
    });

    // Mascot Speech Bubble Randomization
    const mascotPhrases = [
        "Please rest your eyes! 👀",
        "I cry when you don't sign in! 😭",
        "Cycles: 25m focus, 5m break! ⏳",
        "Frosted glass looks clean, right? ✨",
        "I live inside your sidebar! 🤖",
        "Need a break? Skip forward! 🚀",
        "Click the Heart to support! 💖"
    ];

    mascotAvatar.addEventListener('mouseenter', () => {
        const randomPhrase = mascotPhrases[Math.floor(Math.random() * mascotPhrases.length)];
        mascotBubble.textContent = randomPhrase;
    });

    // Interactivity: Toggle mascot sad/happy on click
    mascotAvatar.addEventListener('click', () => {
        mascotAvatar.classList.toggle('sad');
        if (mascotAvatar.classList.contains('sad')) {
            mascotBubble.textContent = "Aww... back to work! 😭";
        } else {
            mascotBubble.textContent = "Yay! Let's stay focused! 😄";
        }
    });

    // App Mute button toggle mockup
    muteBtn.addEventListener('click', () => {
        muteBtn.classList.toggle('muted');
        const icon = muteBtn.querySelector('.mute-icon');
        if (muteBtn.classList.contains('muted')) {
            // Muted SVG change
            icon.innerHTML = '<path d="M11 5L6 9H2v6h4l5 4V5z"></path><line x1="23" y1="9" x2="17" y2="15"></line><line x1="17" y1="9" x2="23" y2="15"></line>';
        } else {
            // Unmuted SVG change
            icon.innerHTML = '<path d="M11 5L6 9H2v6h4l5 4V5z"></path><path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"></path>';
        }
    });


    /* ==========================================================================
       2. Screenshot Slideshow Carousel
       ========================================================================== */
    const track = document.getElementById('carousel-track');
    const slides = document.querySelectorAll('.carousel-slide');
    const prevBtn = document.getElementById('carousel-prev');
    const nextBtn = document.getElementById('carousel-next');
    const dotContainer = document.getElementById('carousel-dots');
    const dots = document.querySelectorAll('.carousel-dot');

    let currentSlide = 0;
    const slideCount = slides.length;
    let autoPlayInterval;

    function goToSlide(index) {
        if (index < 0) {
            currentSlide = slideCount - 1;
        } else if (index >= slideCount) {
            currentSlide = 0;
        } else {
            currentSlide = index;
        }

        // Translate track
        track.style.transform = `translateX(-${currentSlide * 100}%)`;

        // Update dots active class
        dots.forEach((dot, idx) => {
            if (idx === currentSlide) {
                dot.classList.add('active');
            } else {
                dot.classList.remove('active');
            }
        });
    }

    // Next slide click
    nextBtn.addEventListener('click', () => {
        goToSlide(currentSlide + 1);
        resetAutoplay();
    });

    // Prev slide click
    prevBtn.addEventListener('click', () => {
        goToSlide(currentSlide - 1);
        resetAutoplay();
    });

    // Dot click
    dots.forEach((dot, idx) => {
        dot.addEventListener('click', () => {
            goToSlide(idx);
            resetAutoplay();
        });
    });

    // Autoplay logic
    function startAutoplay() {
        autoPlayInterval = setInterval(() => {
            goToSlide(currentSlide + 1);
        }, 6000);
    }

    function resetAutoplay() {
        clearInterval(autoPlayInterval);
        startAutoplay();
    }

    startAutoplay();


    /* ==========================================================================
       3. Interactive Live Timer Demonstration
       ========================================================================== */
    const timerProgress = document.getElementById('js-timer-progress');
    const timerLabel = document.getElementById('js-timer-label');
    const timerTime = document.getElementById('js-timer-time');
    const timerPlayBtn = document.getElementById('btn-timer-play');
    const timerResetBtn = document.getElementById('btn-timer-reset');
    const timerSkipBtn = document.getElementById('btn-timer-skip');
    const dfiWork = document.getElementById('dfi-work');
    const dfiBreak = document.getElementById('dfi-break');
    const playPauseIcon = document.getElementById('play-pause-icon');

    // Timer configuration: Work is 25m, Break is 5m
    const PHASES = {
        WORK: {
            name: 'WORK',
            duration: 1500, // 25 minutes
            color: '#FB7185',
            glow: 'rgba(251, 113, 133, 0.5)'
        },
        BREAK: {
            name: 'BREAK',
            duration: 300, // 5 minutes
            color: '#A78BFA',
            glow: 'rgba(167, 139, 250, 0.5)'
        }
    };

    let currentPhase = PHASES.WORK;
    let timerState = 'paused'; // playing or paused
    let secondsRemaining = currentPhase.duration;
    let timerInterval = null;

    const CIRCUMFERENCE = 565.48; // 2 * PI * 90

    function updateTimerDisplay() {
        // Set minutes and seconds
        const mins = Math.floor(secondsRemaining / 60);
        const secs = secondsRemaining % 60;
        timerTime.textContent = `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;

        // Circular progress offset
        const fraction = secondsRemaining / currentPhase.duration;
        const offset = CIRCUMFERENCE * (1 - fraction);
        timerProgress.style.strokeDashoffset = offset;

        // Apply colors and highlights
        timerLabel.textContent = currentPhase.name;
        timerLabel.style.color = currentPhase.color;
        timerProgress.style.stroke = currentPhase.color;
        timerProgress.style.filter = `drop-shadow(0 0 6px ${currentPhase.glow})`;

        if (currentPhase.name === 'WORK') {
            dfiWork.classList.add('active');
            dfiBreak.classList.remove('active');
        } else {
            dfiWork.classList.remove('active');
            dfiBreak.classList.add('active');
        }
    }

    function startTimer() {
        if (timerInterval) clearInterval(timerInterval);
        
        timerState = 'playing';
        // Play state: show Pause icon (two vertical bars)
        playPauseIcon.innerHTML = '<rect x="6" y="4" width="4" height="16"></rect><rect x="14" y="4" width="4" height="16"></rect>';
        playPauseIcon.setAttribute('viewBox', '0 0 24 24');

        timerInterval = setInterval(() => {
            if (secondsRemaining > 0) {
                secondsRemaining--;
                updateTimerDisplay();
            } else {
                // Phase completed! Auto toggle phase
                clearInterval(timerInterval);
                togglePhase();
                startTimer();
            }
        }, 1000);
    }

    function pauseTimer() {
        timerState = 'paused';
        // Pause state: show Play icon (triangle)
        playPauseIcon.innerHTML = '<polygon points="5 3 19 12 5 21 5 3"></polygon>';
        playPauseIcon.setAttribute('viewBox', '0 0 24 24');
        
        if (timerInterval) {
            clearInterval(timerInterval);
            timerInterval = null;
        }
    }

    function togglePhase() {
        currentPhase = currentPhase === PHASES.WORK ? PHASES.BREAK : PHASES.WORK;
        secondsRemaining = currentPhase.duration;
        updateTimerDisplay();
    }

    // Play/Pause Click Handler
    timerPlayBtn.addEventListener('click', () => {
        if (timerState === 'paused') {
            startTimer();
        } else {
            pauseTimer();
        }
    });

    // Reset Click Handler
    timerResetBtn.addEventListener('click', () => {
        pauseTimer();
        secondsRemaining = currentPhase.duration;
        updateTimerDisplay();
    });

    // Skip Click Handler
    timerSkipBtn.addEventListener('click', () => {
        const wasPlaying = timerState === 'playing';
        pauseTimer();
        togglePhase();
        if (wasPlaying) {
            startTimer();
        }
    });

    // Initialize display state
    updateTimerDisplay();
    updateMockupView();
});
