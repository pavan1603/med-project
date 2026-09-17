setupShell('Overview');

async function loadOverview() {
    const summary = await hospitalApi('/api/analytics/dashboard');
    document.getElementById('metrics').innerHTML = `
        <div class="metric"><span>Total Hospitals</span><strong>${summary.total_hospitals}</strong></div>
        <div class="metric"><span>Total Patients</span><strong>${summary.total_patients}</strong></div>
        <div class="metric"><span>Total Reports</span><strong>${summary.diabetes_reports + summary.heart_reports}</strong></div>
    `;
}

async function loadHospitals() {
    const hospitals = await hospitalApi('/api/analytics/hospitals');
    document.getElementById('hospital-list').innerHTML = hospitals.map((h) =>
        item(h.hospital_name, `${h.city || ''} | Patients ${h.total_patients} | Reports ${h.diabetes_reports + h.heart_reports}`)
    ).join('');
}

async function loadActivity() {
    const rows = await hospitalApi('/api/analytics/recent-activity');
    document.getElementById('activity-list').innerHTML = rows.map((x) =>
        item(x.action, `${x.entity_type} #${x.entity_id || ''} | ${x.created_at}`)
    ).join('');
}

document.querySelector('[data-view="hospitals"]').addEventListener('click', loadHospitals);
document.querySelector('[data-view="activity"]').addEventListener('click', loadActivity);
document.getElementById('load-insights-btn')?.addEventListener('click', loadInsights);
document.getElementById('load-portal-btn')?.addEventListener('click', loadPortalAccess);
loadOverview();
