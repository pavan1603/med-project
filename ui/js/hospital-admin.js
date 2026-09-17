setupShell('Overview');
renderReportForm();
renderStandalonePredictionForm();

async function loadOverview() {
    const summary = await hospitalApi('/api/analytics/dashboard');
    document.getElementById('metrics').innerHTML = `
        <div class="metric"><span>Hospital</span><strong>${roleUser.hospital_name || 'Hospital'}</strong></div>
        <div class="metric" onclick="openRegisteredPatients()"><span>Registered Patients</span><strong>${summary.total_patients}</strong><span>Click to view list</span></div>
    `;
}

async function openRegisteredPatients() {
    showView('patients');
    document.getElementById('view-patients')?.classList.add('details-only');
    await loadRegisteredPatients();
    document.getElementById('registered-patients-panel')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function openPatientWorkflow() {
    showView('patients');
    document.getElementById('view-patients')?.classList.remove('details-only');
}

function showPatientWorkspace() {
    openPatientWorkflow();
}

document.getElementById('patient-form').addEventListener('submit', registerPatient);
document.getElementById('patient-search-btn').addEventListener('click', searchPatients);
document.getElementById('load-insights-btn').addEventListener('click', loadInsights);
document.getElementById('load-portal-btn')?.addEventListener('click', loadPortalAccess);
document.getElementById('patients-workflow-btn')?.addEventListener('click', openPatientWorkflow);
loadOverview();
