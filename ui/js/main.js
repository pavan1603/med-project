// ===== THEME =====
function toggleTheme() {
    const html = document.documentElement;
    const icon = document.getElementById('theme-icon');
    const isDark = html.getAttribute('data-theme') === 'dark';
    html.setAttribute('data-theme', isDark ? 'light' : 'dark');
    icon.className = isDark ? 'fas fa-moon' : 'fas fa-sun';
    localStorage.setItem('theme', isDark ? 'light' : 'dark');
}

const savedTheme = localStorage.getItem('theme') || 'light';
document.documentElement.setAttribute('data-theme', savedTheme);
if (document.getElementById('theme-icon')) {
    document.getElementById('theme-icon').className =
        savedTheme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
}

// ===== HEARTBEAT =====
const hbCanvas = document.getElementById('heartbeat');
if (hbCanvas) {
    const hbCtx = hbCanvas.getContext('2d');
    hbCanvas.width = hbCanvas.offsetWidth;
    hbCanvas.height = hbCanvas.offsetHeight;
    let offset = 0;

    function drawHeartbeat() {
        hbCtx.clearRect(0, 0, hbCanvas.width, hbCanvas.height);
        const w = hbCanvas.width;
        const h = hbCanvas.height;
        const mid = h / 2;

        hbCtx.shadowBlur = 10;
        hbCtx.shadowColor = '#4f8ef7';
        hbCtx.strokeStyle = '#4f8ef7';
        hbCtx.lineWidth = 2;
        hbCtx.beginPath();

        let x = 0;
        let drawing = false;

        while (x < w) {
            const pos = (x + offset) % w;
            let y = mid;
            const cycle = pos % 150;

            if (cycle < 40) { y = mid; }
            else if (cycle < 50) { y = mid - 15 * Math.sin((cycle-40)/10*Math.PI); }
            else if (cycle < 60) { y = mid - 50 * Math.sin((cycle-50)/10*Math.PI); }
            else if (cycle < 70) { y = mid + 20 * Math.sin((cycle-60)/10*Math.PI); }
            else if (cycle < 85) { y = mid - 10 * Math.sin((cycle-70)/15*Math.PI); }
            else { y = mid; }

            if (!drawing) { hbCtx.moveTo(x, y); drawing = true; }
            else { hbCtx.lineTo(x, y); }
            x += 2;
        }

        hbCtx.stroke();
        offset += 2;
        requestAnimationFrame(drawHeartbeat);
    }
    drawHeartbeat();
}

// ===== COUNTER =====
function animateCounter(el) {
    const target = parseInt(el.getAttribute('data-target'));
    const step = target / (2000 / 16);
    let current = 0;
    const timer = setInterval(() => {
        current += step;
        if (current >= target) { current = target; clearInterval(timer); }
        el.textContent = Math.floor(current).toLocaleString();
    }, 16);
}

const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            document.querySelectorAll('.counter').forEach(animateCounter);
            observer.disconnect();
        }
    });
}, { threshold: 0.5 });

const statsSection = document.querySelector('.stats');
if (statsSection) observer.observe(statsSection);

// ===== NAVBAR SCROLL =====
window.addEventListener('scroll', () => {
    const navbar = document.querySelector('.navbar');
    navbar.style.boxShadow = window.scrollY > 50 ?
        '0 4px 30px rgba(0,0,0,0.08)' : 'none';
});

window.addEventListener('resize', () => {
    if (hbCanvas) {
        hbCanvas.width = hbCanvas.offsetWidth;
        hbCanvas.height = hbCanvas.offsetHeight;
    }
});