const form = document.getElementById('login-form');
const usernameInput = document.getElementById('username');
const passwordInput = document.getElementById('password');
const messageEl = document.getElementById('login-message');
const themeToggle = document.getElementById('theme-toggle');

function setMessage(text, ok = false) {
    messageEl.textContent = text || '';
    messageEl.classList.toggle('success', ok);
}

function dashboardForRole(user) {
    if (user.role === 'super_admin') return 'super-admin.html';
    if (user.role === 'hospital_admin') return 'hospital-admin.html';
    if (user.role === 'receptionist') return 'receptionist.html';
    if (user.role === 'doctor') return 'doctor.html';
    if (user.role === 'patient') return 'patient.html';
    return 'hospital-dashboard.html';
}

themeToggle.addEventListener('click', toggleHospitalTheme);

document.querySelectorAll('.demo-users button').forEach((button) => {
    button.addEventListener('click', () => {
        usernameInput.value = button.dataset.user;
        passwordInput.value = button.dataset.pass;
        setMessage('');
    });
});

form.addEventListener('submit', async (event) => {
    event.preventDefault();
    setMessage('Checking credentials...', true);

    try {
        const response = await fetch(`${HOSPITAL_API_BASE}/api/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                username: usernameInput.value.trim(),
                password: passwordInput.value,
            }),
        });

        const payload = await response.json();

        if (!response.ok || payload.success === false) {
            throw new Error(payload.error || 'Login failed');
        }

        saveHospitalSession(payload.data);
        setMessage('Login successful. Opening workspace...', true);
        window.location.href = dashboardForRole(payload.data.user);
    } catch (error) {
        setMessage(error.message || 'Login failed');
    }
});
