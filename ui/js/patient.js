setupShell('My Summary');

async function loadPatientSummary() {
    const patientId = roleUser.patient_id;
    const [insights, doctorSummaries] = await Promise.all([
        hospitalApi(`/api/patients/${patientId}/insights`),
        hospitalApi(`/api/patients/${patientId}/doctor-summaries`),
    ]);
    const doctorSummaryHtml = doctorSummaries.length
        ? doctorSummaries.map((summary) => `
            <div class="item">
                <strong>Doctor Summary - ${summary.doctor_name || 'Doctor'}</strong>
                <span>${summary.created_at || ''}</span>
                <ul>
                    <li>${summary.summary_text}</li>
                    ${summary.medication_suggestions ? `<li><strong>Medication:</strong> ${summary.medication_suggestions}</li>` : ''}
                    ${summary.lifestyle_suggestions ? `<li><strong>Lifestyle:</strong> ${summary.lifestyle_suggestions}</li>` : ''}
                    ${summary.follow_up_advice ? `<li><strong>Follow-up:</strong> ${summary.follow_up_advice}</li>` : ''}
                </ul>
            </div>
        `).join('')
        : item('Doctor Summary', 'No doctor summary has been shared yet.');

    document.getElementById('patient-summary').innerHTML = `
        <div class="item"><strong>${roleUser.full_name}</strong><span>${roleUser.patient_uid}</span></div>
        ${doctorSummaryHtml}
        <div class="item"><strong>Summary</strong><ul>${insights.patient_summary.map((x) => `<li>${x}</li>`).join('')}</ul></div>
        <div class="item"><strong>Guidance</strong><ul>${insights.recommendations.map((x) => `<li>${x}</li>`).join('')}</ul></div>
    `;
}

document.getElementById('open-chat-btn').addEventListener('click', () => {
    window.location.href = `chatbot.html?patient_id=${encodeURIComponent(roleUser.patient_id)}`;
});

loadPatientSummary();
