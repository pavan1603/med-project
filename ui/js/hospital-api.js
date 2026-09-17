const HOSPITAL_API_BASE = 'http://127.0.0.1:5000';
const HOSPITAL_SESSION_KEY = 'medirisk_hospital_session';

function saveHospitalSession(payload) {
    localStorage.setItem(HOSPITAL_SESSION_KEY, JSON.stringify(payload));
}

function getHospitalSession() {
    try {
        return JSON.parse(localStorage.getItem(HOSPITAL_SESSION_KEY));
    } catch (error) {
        return null;
    }
}

function clearHospitalSession() {
    localStorage.removeItem(HOSPITAL_SESSION_KEY);
}

function getCurrentHospitalUser() {
    const session = getHospitalSession();
    return session ? session.user : null;
}

async function hospitalApi(path, options = {}) {
    const session = getHospitalSession();
    const headers = {
        'Content-Type': 'application/json',
        ...(options.headers || {}),
    };

    if (session && session.account_type === 'patient' && session.user && session.user.id) {
        headers['X-Patient-Account-Id'] = String(session.user.id);
    } else if (session && session.user && session.user.id) {
        headers['X-User-Id'] = String(session.user.id);
    }

    const response = await fetch(`${HOSPITAL_API_BASE}${path}`, {
        ...options,
        headers,
    });

    const payload = await response.json().catch(() => ({}));

    if (!response.ok || payload.success === false) {
        throw new Error(payload.error || `Request failed with status ${response.status}`);
    }

    return payload.data;
}

function requireHospitalLogin() {
    const session = getHospitalSession();
    if (!session || !session.user) {
        window.location.href = 'hospital-login.html';
        return null;
    }
    return session.user;
}

function applyHospitalTheme() {
    const savedTheme = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-theme', savedTheme);
    const icon = document.getElementById('theme-icon');
    if (icon) {
        icon.className = savedTheme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
    }
}

function toggleHospitalTheme() {
    const html = document.documentElement;
    const icon = document.getElementById('theme-icon');
    const isDark = html.getAttribute('data-theme') === 'dark';
    const nextTheme = isDark ? 'light' : 'dark';
    html.setAttribute('data-theme', nextTheme);
    localStorage.setItem('theme', nextTheme);
    if (icon) {
        icon.className = nextTheme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
    }
}

applyHospitalTheme();
