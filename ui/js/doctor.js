setupShell('Overview');
renderReportForm();
renderStandalonePredictionForm();

async function loadOverview() {
    const summary = await hospitalApi('/api/analytics/dashboard');
    document.getElementById('metrics').innerHTML = `
        <div class="metric"><span>Hospital</span><strong>${roleUser.hospital_name || 'Hospital'}</strong></div>
        <div class="metric" onclick="openRegisteredPatients()"><span>Registered Patients</span><strong>${summary.total_patients}</strong><span>Click to view list</span></div>
        <div class="metric" onclick="openSummaryFromPatients()"><span>Give Summary</span><strong>Write</strong><span>Select a patient and add advice</span></div>
    `;
}

async function openRegisteredPatients() {
    showView('patients');
    await loadRegisteredPatients();
}

async function openSummaryFromPatients() {
    showView('patients');
    await loadRegisteredPatients();
    document.getElementById('patient-results')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

async function saveDoctorSummary(event) {
    event.preventDefault();
    const patientId = document.getElementById('summary-patient-id').value;
    const msg = document.getElementById('summary-message');
    msg.textContent = 'Saving patient summary...';

    try {
        const saved = await hospitalApi(`/api/patients/${patientId}/doctor-summaries`, {
            method: 'POST',
            body: JSON.stringify({
                summary_text: document.getElementById('summary-text').value,
                medication_suggestions: document.getElementById('summary-medication').value,
                lifestyle_suggestions: document.getElementById('summary-lifestyle').value,
                follow_up_advice: document.getElementById('summary-followup').value,
                is_visible_to_patient: true,
            }),
        });

        msg.textContent = 'Summary saved and visible to the patient.';
        document.getElementById('summary-output').innerHTML = item(
            `Saved for patient ${saved.patient_id}`,
            `${saved.doctor_name || roleUser.full_name} | ${saved.created_at}`
        );
        document.getElementById('doctor-summary-form').reset();
    } catch (error) {
        msg.textContent = error.message;
    }
}

document.getElementById('patient-search-btn').addEventListener('click', searchPatients);
document.getElementById('load-insights-btn').addEventListener('click', loadInsights);
document.getElementById('doctor-summary-form').addEventListener('submit', saveDoctorSummary);

loadOverview();
