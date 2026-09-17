const user = requireHospitalLogin();
const themeToggle = document.getElementById('theme-toggle');
const logoutBtn = document.getElementById('logout-btn');
const warmupBtn = document.getElementById('warmup-btn');

function formatRole(role) {
    return String(role || '').replaceAll('_', ' ');
}

function setText(id, value) {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
}

function renderMetrics(summary) {
    const metrics = [
        ['Hospitals', summary.total_hospitals],
        ['Patients', summary.total_patients],
        ['Diabetes Reports', summary.diabetes_reports],
        ['Heart Reports', summary.heart_reports],
    ];

    document.getElementById('metric-grid').innerHTML = metrics.map(([label, value]) => `
        <div class="metric-card">
            <span>${label}</span>
            <strong>${value ?? 0}</strong>
        </div>
    `).join('');
}

function canViewAnalytics() {
    return user && ['super_admin', 'hospital_admin'].includes(user.role);
}

function renderLimitedOverview() {
    document.getElementById('metric-grid').innerHTML = `
        <div class="metric-card">
            <span>Role</span>
            <strong>${formatRole(user.role)}</strong>
        </div>
        <div class="metric-card">
            <span>Hospital</span>
            <strong>${user.hospital_id || 'Global'}</strong>
        </div>
    `;

    renderList('risk-distribution', [], 'Analytics are available for hospital admins and super admins.', () => '');
    renderList('high-risk-list', [], 'Use Patients and Patient Insights from the sidebar.', () => '');
}

function renderList(containerId, items, emptyText, renderer) {
    const container = document.getElementById(containerId);
    if (!items || !items.length) {
        container.innerHTML = `<div class="list-item"><div><strong>${emptyText}</strong></div></div>`;
        return;
    }
    container.innerHTML = items.map(renderer).join('');
}

async function loadOverview() {
    if (!canViewAnalytics()) {
        renderLimitedOverview();
        return;
    }

    const summary = await hospitalApi('/api/analytics/dashboard');
    renderMetrics(summary);

    const diabetesRisk = await hospitalApi('/api/analytics/risk/diabetes');
    const heartRisk = await hospitalApi('/api/analytics/risk/heart');
    const risks = [
        ...diabetesRisk.map((item) => ({ ...item, disease: 'Diabetes' })),
        ...heartRisk.map((item) => ({ ...item, disease: 'Heart' })),
    ];

    renderList('risk-distribution', risks, 'No risk data yet', (item) => `
        <div class="list-item">
            <div>
                <strong>${item.disease}: ${item.risk_level}</strong>
                <span>${item.count} report(s)</span>
            </div>
            <span class="badge">${item.count}</span>
        </div>
    `);

    const highRisk = await hospitalApi('/api/analytics/high-risk-patients');
    renderList('high-risk-list', highRisk, 'No high-risk patients found', (item) => `
        <div class="list-item">
            <div>
                <strong>${item.full_name}</strong>
                <span>${item.patient_uid} | ${item.hospital_name}</span>
            </div>
            <span class="badge">${item.diabetes_risk || item.heart_risk}</span>
        </div>
    `);
}

function showView(view) {
    document.querySelectorAll('.dash-nav button').forEach((button) => {
        button.classList.toggle('active', button.dataset.view === view);
    });
    document.querySelectorAll('.view-section').forEach((section) => {
        section.classList.toggle('active', section.id === `view-${view}`);
    });
    setText('page-title', view.replace('-', ' ').replace(/\b\w/g, (c) => c.toUpperCase()));
}

async function registerPatient(event) {
    event.preventDefault();
    const msg = document.getElementById('patient-message');
    msg.textContent = 'Registering patient...';
    msg.classList.add('success');

    try {
        const result = await hospitalApi('/api/patients/register', {
            method: 'POST',
            body: JSON.stringify({
                full_name: document.getElementById('patient-name').value,
                date_of_birth: document.getElementById('patient-dob').value || null,
                gender: document.getElementById('patient-gender').value,
                phone: document.getElementById('patient-phone').value,
                preferred_language: document.getElementById('patient-language').value,
                address: document.getElementById('patient-address').value,
            }),
        });

        if (result.reason === 'possible_duplicate') {
            msg.classList.remove('success');
            msg.textContent = 'Possible duplicate found. Search patient before creating a new record.';
            renderList('patient-results', result.possible_duplicates, 'No duplicate details', renderPatientItem);
            return;
        }

        msg.textContent = `Patient registered: ${result.patient_uid}`;
        document.getElementById('patient-form').reset();

        if (canViewAnalytics()) {
            await loadOverview();
        }
    } catch (error) {
        msg.classList.remove('success');
        msg.textContent = error.message;
    }
}

function renderPatientItem(item) {
    return `
        <div class="list-item">
            <div>
                <strong>${item.full_name}</strong>
                <span>ID ${item.id} | ${item.patient_uid} | Age ${item.age ?? 'NA'} | ${item.phone || 'No phone'}</span>
            </div>
            <div style="display:flex; gap:8px; flex-wrap:wrap;">
                <button class="secondary-btn" onclick="startReportFor(${item.id})">New Report</button>
                <button class="secondary-btn" onclick="loadInsightsFor(${item.id})">Insights</button>
            </div>
        </div>
    `;
}

async function searchPatients() {
    const query = document.getElementById('patient-search').value.trim();
    if (!query) return;
    const results = await hospitalApi(`/api/patients/search?q=${encodeURIComponent(query)}`);
    renderList('patient-results', results, 'No patients found', renderPatientItem);
}

async function loadInsightsFor(patientId) {
    document.getElementById('insight-patient-id').value = patientId;
    showView('insights');
    await loadInsights();
}

function startReportFor(patientId) {
    document.getElementById('report-patient-id').value = patientId;
    showView('reports');
}

function syncPregnancyField() {
    const gender = document.getElementById('diabetes-gender').value;
    const field = document.getElementById('diabetes-pregnancies-field');
    const input = document.getElementById('diabetes-pregnancies');
    const show = gender === 'female';
    field.style.display = show ? 'grid' : 'none';
    if (!show) input.value = '0';
}

function numberValue(id) {
    const value = document.getElementById(id).value;
    if (value === '') return null;
    return Number(value);
}

function intValue(id) {
    return Number(document.getElementById(id).value || 0);
}

function renderReportResult(payload) {
    const prediction = payload.prediction || {};
    const report = payload.report || {};
    const explanation = prediction.explanation || {};
    const topFactors = explanation.top_factors || prediction.top_factors || [];

    document.getElementById('report-output').innerHTML = `
        <div class="print-actions">
            <button class="secondary-btn" onclick="printSection('report-output')"><i class="fas fa-print"></i> Print Report</button>
        </div>
        <div class="list-item">
            <div>
                <strong>${prediction.result || report.risk_level || 'Prediction saved'}</strong>
                <span>Risk: ${prediction.risk || report.risk_level || 'NA'} | Confidence: ${prediction.confidence ?? report.confidence ?? 'NA'}%</span>
            </div>
            <span class="badge">${report.risk_level || prediction.risk || 'Saved'}</span>
        </div>
        ${explanation.plain_explanation ? `<p class="muted-text">${explanation.plain_explanation}</p>` : ''}
        ${topFactors.length ? `
            <div>
                <h2>Top Factors</h2>
                <ul>${topFactors.slice(0, 5).map((item) => `<li>${item.name || item}: ${item.explanation || item.status || ''}</li>`).join('')}</ul>
            </div>
        ` : ''}
    `;
}

async function submitReport(event) {
    event.preventDefault();

    const msg = document.getElementById('report-message');
    const patientId = Number(document.getElementById('report-patient-id').value);
    const reportType = document.getElementById('report-type').value;

    msg.classList.add('success');
    msg.textContent = 'Creating visit and running prediction...';

    try {
        const visit = await hospitalApi('/api/visits/create', {
            method: 'POST',
            body: JSON.stringify({
                patient_id: patientId,
                visit_reason: document.getElementById('report-reason').value || 'AI screening',
                visit_status: 'completed',
            }),
        });

        let endpoint;
        let body;

        if (reportType === 'diabetes') {
            endpoint = '/api/reports/diabetes';
            body = {
                visit_id: visit.id,
                input_values: {
                    Pregnancies: numberValue('diabetes-pregnancies') || 0,
                    Glucose: numberValue('diabetes-glucose'),
                    BloodPressure: numberValue('diabetes-bp'),
                    SkinThickness: numberValue('diabetes-skin'),
                    Insulin: numberValue('diabetes-insulin'),
                    BMI: numberValue('diabetes-bmi'),
                    DiabetesPedigreeFunction: numberValue('diabetes-dpf') || 0,
                },
            };
        } else {
            endpoint = '/api/reports/heart';
            body = {
                visit_id: visit.id,
                mode: 'simple_screening',
                input_values: {
                    age: numberValue('heart-age'),
                    gender: document.getElementById('heart-gender').value,
                    chest_pain: intValue('heart-chest-pain'),
                    breathless_walking: intValue('heart-breathless'),
                    high_bp: intValue('heart-high-bp'),
                    diabetes: intValue('heart-diabetes'),
                    smoking: intValue('heart-smoking'),
                    high_cholesterol: intValue('heart-cholesterol'),
                    tired_easily: intValue('heart-tired'),
                    family_history: intValue('heart-family'),
                    poor_exercise_recovery: intValue('heart-recovery'),
                    exercise_chest_pain: intValue('heart-exercise-pain'),
                },
            };
        }

        const result = await hospitalApi(endpoint, {
            method: 'POST',
            body: JSON.stringify(body),
        });

        renderReportResult(result);
        msg.textContent = `Report saved for visit ${visit.id}.`;

        if (canViewAnalytics()) {
            await loadOverview();
        }
    } catch (error) {
        msg.classList.remove('success');
        msg.textContent = error.message;
    }
}

async function loadInsights() {
    const patientId = document.getElementById('insight-patient-id').value;
    if (!patientId) return;
    const [patient, insights] = await Promise.all([
        hospitalApi(`/api/patients/${patientId}`),
        hospitalApi(`/api/patients/${patientId}/insights`),
    ]);
    const output = document.getElementById('insight-output');
    output.innerHTML = `
        <div class="print-actions">
            <button class="secondary-btn" onclick="printSection('insight-output')"><i class="fas fa-print"></i> Print Patient Report</button>
        </div>
        <div class="list-item">
            <div>
                <strong>${patient.full_name}</strong>
                <span>${patient.patient_uid} | Age ${patient.age ?? 'NA'} | ${patient.gender} | ${patient.phone || 'No phone'}</span>
            </div>
            <span class="badge">${patient.preferred_language}</span>
        </div>
        <div class="list-item">
            <div>
                <strong>Follow-up priority: ${insights.severity}</strong>
                <span>Patient ID ${insights.patient_id}</span>
            </div>
        </div>
        <div>
            <h2>Doctor Summary</h2>
            <ul>${insights.doctor_summary.map((item) => `<li>${item}</li>`).join('')}</ul>
        </div>
        <div>
            <h2>Recommendations</h2>
            <ul>${insights.recommendations.map((item) => `<li>${item}</li>`).join('')}</ul>
        </div>
    `;
}

async function loadPatientView() {
    const patientId = document.getElementById('patient-view-id').value;
    if (!patientId) return;

    const [patient, insights] = await Promise.all([
        hospitalApi(`/api/patients/${patientId}`),
        hospitalApi(`/api/patients/${patientId}/insights`),
    ]);

    document.getElementById('patient-view-output').innerHTML = `
        <div class="print-actions">
            <button class="secondary-btn" onclick="printSection('patient-view-output')"><i class="fas fa-print"></i> Print Patient Copy</button>
        </div>
        <div class="list-item">
            <div>
                <strong>${patient.full_name}</strong>
                <span>${patient.patient_uid} | Age ${patient.age ?? 'NA'} | ${patient.preferred_language}</span>
            </div>
        </div>
        <div>
            <h2>Patient Summary</h2>
            <ul>${insights.patient_summary.map((item) => `<li>${item}</li>`).join('')}</ul>
        </div>
        <div>
            <h2>Guidance</h2>
            <ul>${insights.recommendations.map((item) => `<li>${item}</li>`).join('')}</ul>
        </div>
        <p class="muted-text">This patient copy is educational guidance. Diagnosis and treatment decisions must be confirmed by a qualified doctor.</p>
    `;
}

async function loadSuperAdminSection() {
    const output = document.getElementById('super-admin-output');

    if (user.role !== 'super_admin') {
        output.innerHTML = '<div class="list-item"><div><strong>Only super admin can view this section.</strong></div></div>';
        return;
    }

    const hospitals = await hospitalApi('/api/analytics/hospitals');
    renderList('super-admin-output', hospitals, 'No hospitals found', (item) => `
        <div class="list-item">
            <div>
                <strong>${item.hospital_name}</strong>
                <span>${item.city || ''} ${item.state || ''} | Patients ${item.total_patients} | Reports ${item.diabetes_reports + item.heart_reports}</span>
            </div>
            <span class="badge">${item.hospital_code}</span>
        </div>
    `);
}

function printSection(sectionId) {
    const source = document.getElementById(sectionId);
    if (!source) return;

    const printWindow = window.open('', '_blank');
    printWindow.document.write(`
        <html>
        <head>
            <title>MediRisk Patient Report</title>
            <style>
                body { font-family: Arial, sans-serif; padding: 24px; color: #111827; }
                .list-item { border: 1px solid #d1d5db; padding: 12px; margin-bottom: 12px; }
                .badge, button { display: none; }
                h2 { margin-top: 20px; }
                li { margin-bottom: 8px; }
            </style>
        </head>
        <body>
            <h1>MediRisk Report</h1>
            ${source.innerHTML}
        </body>
        </html>
    `);
    printWindow.document.close();
    printWindow.focus();
    printWindow.print();
}

function openPatientChat() {
    const patientId = document.getElementById('chat-patient-id').value;
    const url = patientId ? `chatbot.html?patient_id=${encodeURIComponent(patientId)}` : 'chatbot.html';
    window.location.href = url;
}

async function warmupAi() {
    warmupBtn.disabled = true;
    warmupBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Warming...';
    try {
        await hospitalApi('/api/system/warmup-ai', { method: 'POST', body: JSON.stringify({}) });
        warmupBtn.innerHTML = '<i class="fas fa-check"></i> AI Ready';
    } catch (error) {
        warmupBtn.innerHTML = '<i class="fas fa-bolt"></i> Warm up AI';
        alert(error.message);
    } finally {
        warmupBtn.disabled = false;
    }
}

if (user) {
    setText('user-name', user.full_name);
    setText('user-role', formatRole(user.role));
    if (user.role === 'patient') {
        setText('hospital-name', `${user.patient_uid || 'Patient'} Section`);
    } else {
        setText('hospital-name', user.hospital_id ? `Hospital ID ${user.hospital_id}` : 'Global Admin');
    }
}

themeToggle.addEventListener('click', toggleHospitalTheme);
logoutBtn.addEventListener('click', () => {
    clearHospitalSession();
    window.location.href = 'hospital-login.html';
});
warmupBtn.addEventListener('click', warmupAi);

document.querySelectorAll('.dash-nav button').forEach((button) => {
    button.addEventListener('click', () => showView(button.dataset.view));
});

document.getElementById('patient-form').addEventListener('submit', registerPatient);
document.getElementById('patient-search-btn').addEventListener('click', searchPatients);
document.getElementById('load-insights-btn').addEventListener('click', loadInsights);
document.getElementById('open-chat-btn').addEventListener('click', openPatientChat);
document.getElementById('report-form').addEventListener('submit', submitReport);
document.getElementById('diabetes-gender').addEventListener('change', syncPregnancyField);
document.getElementById('load-patient-view-btn').addEventListener('click', loadPatientView);

if (user && user.role === 'patient') {
    document.querySelectorAll('.dash-nav button').forEach((button) => {
        button.style.display = button.dataset.view === 'patient-section' || button.dataset.view === 'chat'
            ? 'inline-flex'
            : 'none';
    });
    document.getElementById('patient-view-id').value = user.patient_id;
    document.getElementById('chat-patient-id').value = user.patient_id;
    showView('patient-section');
    loadPatientView().catch((error) => alert(error.message));
} else if (user && user.role === 'receptionist') {
    showView('patients');
} else if (user && user.role === 'doctor') {
    showView('insights');
}

if (user && user.role !== 'super_admin') {
    document.getElementById('super-admin-nav').style.display = 'none';
}

if (user && user.role === 'patient') {
    document.getElementById('patient-section-nav').style.display = 'inline-flex';
} else {
    document.getElementById('patient-section-nav').style.display = 'inline-flex';
}

syncPregnancyField();
loadSuperAdminSection().catch(() => {});

loadOverview().catch((error) => {
    if (canViewAnalytics()) {
        alert(error.message);
    } else {
        renderLimitedOverview();
    }
});
