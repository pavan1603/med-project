const roleUser = requireHospitalLogin();

function logout() {
    clearHospitalSession();
    window.location.href = 'hospital-login.html';
}

function setupShell(defaultTitle) {
    const name = document.getElementById('user-name');
    if (name) name.textContent = roleUser.full_name;

    const hospital = roleUser.hospital_name || (roleUser.hospital_id ? `Hospital ID ${roleUser.hospital_id}` : 'Global');
    ['hospital-name', 'header-hospital'].forEach((id) => {
        const el = document.getElementById(id);
        if (el) el.textContent = hospital;
    });

    const patientUid = document.getElementById('patient-uid');
    if (patientUid) patientUid.textContent = roleUser.patient_uid || 'Patient';

    document.getElementById('logout-btn')?.addEventListener('click', logout);

    document.querySelectorAll('aside button[data-view]').forEach((button) => {
        button.addEventListener('click', () => showView(button.dataset.view));
    });

    setTitle(defaultTitle);
}

function setTitle(title) {
    const el = document.getElementById('page-title');
    if (el) el.textContent = title;
}

function showView(view) {
    document.querySelectorAll('aside button[data-view]').forEach((button) => {
        button.classList.toggle('active', button.dataset.view === view);
    });
    document.querySelectorAll('.view').forEach((section) => {
        section.classList.toggle('active', section.id === `view-${view}`);
    });
    setTitle(view.replaceAll('-', ' ').replace(/\b\w/g, (c) => c.toUpperCase()));
}

function item(title, subtitle = '') {
    return `<div class="item"><strong>${title}</strong>${subtitle ? `<span>${subtitle}</span>` : ''}</div>`;
}

function renderPatientList(containerId, patients) {
    const container = document.getElementById(containerId);
    if (!patients.length) {
        container.innerHTML = item('No patients found');
        return;
    }
    container.innerHTML = patients.map((patient) => `
        <div class="item">
            <strong>${patient.full_name}</strong>
            <span>ID ${patient.id} | ${patient.patient_uid} | Age ${patient.age ?? 'NA'} | ${patient.phone || 'No phone'}</span>
            <div class="row" style="margin-top:10px;">
                <button onclick="fillReportPatient(${patient.id})">New Report</button>
                <button onclick="fillInsightPatient(${patient.id})">Insights</button>
                ${document.getElementById('portal-patient-id') ? `<button onclick="fillPortalAccessPatient(${patient.id})">Portal Access</button>` : ''}
                ${document.getElementById('summary-patient-id') ? `<button onclick="fillSummaryPatient(${patient.id})">Give Summary</button>` : ''}
            </div>
        </div>
    `).join('');
}

function fillReportPatient(patientId) {
    const input = document.getElementById('report-patient-id');
    if (input) input.value = patientId;
    showView('reports');
}

function fillInsightPatient(patientId) {
    const input = document.getElementById('insight-patient-id');
    if (input) input.value = patientId;
    showView('insights');
    loadInsights?.();
}

function fillSummaryPatient(patientId) {
    const input = document.getElementById('summary-patient-id');
    if (input) input.value = patientId;
    showView('summary');
    document.getElementById('summary-text')?.focus();
}

function fillPortalAccessPatient(patientId) {
    const input = document.getElementById('portal-patient-id');
    if (input) input.value = patientId;
    showView('portal-access');
    loadPortalAccess?.();
}

async function registerPatient(event) {
    event.preventDefault();
    const msg = document.getElementById('patient-message');
    msg.textContent = 'Registering patient...';

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
            msg.textContent = 'Possible duplicate found. Select existing patient or use a different record.';
            renderPatientList('patient-results', result.possible_duplicates);
            return;
        }

        const account = result.patient_account;
        if (account) {
            msg.innerHTML = `
                Patient registered: <strong>${result.patient_uid}</strong><br>
                Patient login username: <strong>${account.username}</strong><br>
                Temporary password: <strong>${account.temporary_password}</strong><br>
                Share these credentials with the patient. The password is shown only now.
            `;
        } else {
            msg.textContent = `Patient registered: ${result.patient_uid}`;
        }

        if (result.patient_account_error) {
            msg.innerHTML += `<br>Patient account warning: ${result.patient_account_error}`;
        }

        document.getElementById('patient-form').reset();
        await loadOverview?.();
    } catch (error) {
        msg.textContent = error.message;
    }
}

async function searchPatients() {
    const query = document.getElementById('patient-search').value.trim();
    if (!query) return;
    const patients = await hospitalApi(`/api/patients/search?q=${encodeURIComponent(query)}`);
    renderPatientList('patient-results', patients);
}

async function loadRegisteredPatients() {
    const patients = await hospitalApi('/api/patients?limit=100');
    renderPatientList('patient-results', patients);
}

function renderReportForm() {
    const form = document.getElementById('report-form');
    if (!form) return;

    form.innerHTML = `
        <label>Patient ID<input id="report-patient-id" type="number" min="1" required></label>
        <label>Report Type<select id="report-type"><option value="diabetes">Diabetes Report</option><option value="heart_simple">Simple Heart Screening</option></select></label>
        <label>Visit Reason<input id="report-reason" value="AI screening"></label>

        <div class="report-title">Diabetes Values</div>
        <label>Patient Gender<select id="diabetes-gender"><option value="male">Male</option><option value="female">Female</option><option value="other">Other</option></select></label>
        <label id="pregnancy-field">Pregnancies<input id="diabetes-pregnancies" type="number" step="1" value="0"></label>
        <label>Glucose<input id="diabetes-glucose" type="number" step="0.1"></label>
        <label>Blood Pressure<input id="diabetes-bp" type="number" step="0.1"></label>
        <label>Skin Thickness<input id="diabetes-skin" type="number" step="0.1"></label>
        <label>Insulin Level<input id="diabetes-insulin" type="number" step="0.1"></label>
        <label>BMI<input id="diabetes-bmi" type="number" step="0.1"></label>
        <label>Family History Score<input id="diabetes-dpf" type="number" step="0.01"></label>

        <div class="report-title">Simple Heart Screening</div>
        <label>Age<input id="heart-age" type="number" step="1"></label>
        <label>Gender<select id="heart-gender"><option value="male">Male</option><option value="female">Female</option><option value="other">Other</option></select></label>
        ${yesNo('heart-chest-pain', 'Chest Pain?')}
        ${yesNo('heart-breathless', 'Breathless While Walking?')}
        ${yesNo('heart-high-bp', 'High BP?')}
        ${yesNo('heart-diabetes', 'Diabetes?')}
        ${yesNo('heart-smoking', 'Smoking?')}
        ${yesNo('heart-cholesterol', 'High Cholesterol?')}
        ${yesNo('heart-tired', 'Tired Easily?')}
        ${yesNo('heart-family', 'Family History?')}
        ${yesNo('heart-recovery', 'Poor Exercise Recovery?')}
        ${yesNo('heart-exercise-pain', 'Chest Pain During Exercise?')}
        <button type="submit">Analyze & Save</button>
    `;

    document.getElementById('diabetes-gender').addEventListener('change', syncPregnancyField);
    syncPregnancyField();
    form.addEventListener('submit', submitReport);
}

function yesNo(id, label) {
    return `<label>${label}<select id="${id}"><option value="0">No</option><option value="1">Yes</option></select></label>`;
}

function renderStandalonePredictionForm() {
    const form = document.getElementById('standalone-prediction-form');
    if (!form) return;

    form.innerHTML = `
        <label>Prediction Type
            <select id="quick-prediction-type">
                <option value="diabetes">Diabetes Risk</option>
                <option value="heart_simple">Simple Heart Risk</option>
            </select>
        </label>

        <div class="report-title">Diabetes Values</div>
        <label>Gender<select id="quick-diabetes-gender"><option value="male">Male</option><option value="female">Female</option><option value="other">Other</option></select></label>
        <label id="quick-pregnancy-field">Pregnancies<input id="quick-diabetes-pregnancies" type="number" step="1" value="0"></label>
        <label>Age<input id="quick-diabetes-age" type="number" step="1"></label>
        <label>Glucose<input id="quick-diabetes-glucose" type="number" step="0.1"></label>
        <label>Blood Pressure<input id="quick-diabetes-bp" type="number" step="0.1"></label>
        <label>Skin Thickness<input id="quick-diabetes-skin" type="number" step="0.1"></label>
        <label>Insulin<input id="quick-diabetes-insulin" type="number" step="0.1"></label>
        <label>BMI<input id="quick-diabetes-bmi" type="number" step="0.1"></label>
        <label>Family History Score<input id="quick-diabetes-dpf" type="number" step="0.01" value="0.3"></label>

        <div class="report-title">Simple Heart Screening</div>
        <label>Age<input id="quick-heart-age" type="number" step="1"></label>
        <label>Gender<select id="quick-heart-gender"><option value="male">Male</option><option value="female">Female</option><option value="other">Other</option></select></label>
        ${yesNo('quick-heart-chest-pain', 'Chest Pain?')}
        ${yesNo('quick-heart-breathless', 'Breathless While Walking?')}
        ${yesNo('quick-heart-high-bp', 'High BP?')}
        ${yesNo('quick-heart-diabetes', 'Diabetes?')}
        ${yesNo('quick-heart-smoker', 'Smoking?')}
        ${yesNo('quick-heart-cholesterol', 'High Cholesterol?')}
        ${yesNo('quick-heart-tired', 'Tired Easily?')}
        ${yesNo('quick-heart-family', 'Family History?')}
        <label>Exercise Recovery
            <select id="quick-heart-recovery">
                <option value="normal">Normal</option>
                <option value="average">Average</option>
                <option value="poor">Poor</option>
            </select>
        </label>
        ${yesNo('quick-heart-exercise-pain', 'Chest Pain During Exercise?')}
        <button type="submit">Analyze</button>
    `;

    document.getElementById('quick-diabetes-gender').addEventListener('change', syncQuickPregnancyField);
    syncQuickPregnancyField();
    form.addEventListener('submit', submitStandalonePrediction);
}

function syncQuickPregnancyField() {
    const gender = document.getElementById('quick-diabetes-gender')?.value;
    const field = document.getElementById('quick-pregnancy-field');
    const input = document.getElementById('quick-diabetes-pregnancies');
    if (!field || !input) return;
    field.style.display = gender === 'female' ? 'grid' : 'none';
    if (gender !== 'female') input.value = '0';
}

async function submitStandalonePrediction(event) {
    event.preventDefault();
    const type = document.getElementById('quick-prediction-type').value;
    const msg = document.getElementById('standalone-prediction-message');
    const output = document.getElementById('standalone-prediction-output');
    msg.textContent = 'Running prediction...';
    output.innerHTML = '';

    let endpoint = '/predict/diabetes';
    let payload = {
        Pregnancies: numberValue('quick-diabetes-pregnancies') || 0,
        Glucose: numberValue('quick-diabetes-glucose') || 120,
        BloodPressure: numberValue('quick-diabetes-bp') || 70,
        SkinThickness: numberValue('quick-diabetes-skin') || 20,
        Insulin: numberValue('quick-diabetes-insulin') || 100,
        BMI: numberValue('quick-diabetes-bmi') || 25,
        DiabetesPedigreeFunction: numberValue('quick-diabetes-dpf') || 0.3,
        Age: numberValue('quick-diabetes-age') || 30,
    };

    if (type === 'heart_simple') {
        endpoint = '/screen/heart-simple';
        payload = {
            age: numberValue('quick-heart-age') || 40,
            gender: document.getElementById('quick-heart-gender').value,
            chest_pain: intValue('quick-heart-chest-pain'),
            breathless_walking: intValue('quick-heart-breathless'),
            high_bp: intValue('quick-heart-high-bp'),
            diabetes: intValue('quick-heart-diabetes'),
            smoker: intValue('quick-heart-smoker'),
            high_cholesterol: intValue('quick-heart-cholesterol'),
            tired_easily: intValue('quick-heart-tired'),
            family_history: intValue('quick-heart-family'),
            exercise_recovery: document.getElementById('quick-heart-recovery').value,
            exercise_chest_pain: intValue('quick-heart-exercise-pain'),
        };
    }

    try {
        const response = await fetch(`${HOSPITAL_API_BASE}${endpoint}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        const result = await response.json();
        if (!response.ok || result.success === false) {
            throw new Error(result.error || 'Prediction failed');
        }

        msg.textContent = '';
        output.innerHTML = renderStandalonePredictionResult(result);
    } catch (error) {
        msg.textContent = error.message;
    }
}

function renderStandalonePredictionResult(result) {
    const explanation = result.explanation || {};
    const factors = explanation.top_factors || result.top_factors || [];
    const nextSteps = explanation.next_steps || result.next_steps || [];
    const title = result.result || result.type || 'Prediction Complete';
    const risk = result.risk || result.type_risk || 'NA';
    const confidence = result.confidence != null ? `${result.confidence}%` : 'NA';
    const isHeart = result.mode === 'simple_heart_screening' || title.toLowerCase().includes('heart');
    const reportTitle = isHeart ? 'Heart Disease Report' : 'Diabetes Risk Report';
    const icon = isHeart ? '❤️' : '🩸';
    const riskClass = String(risk).toLowerCase().includes('high') || String(risk).toLowerCase().includes('very')
        ? 'danger'
        : String(risk).toLowerCase().includes('moderate')
            ? 'warning'
            : 'success';
    const clinicalText = explanation.clinical_interpretation || result.description || '';

    return `
        <div class="prediction-report ${riskClass}">
            <div class="prediction-complete">MediRisk Analysis Complete ✅</div>
            <div class="prediction-card">
                <div class="prediction-card-head">
                    <h3>${icon} ${reportTitle}</h3>
                    <span class="risk-pill ${riskClass}">${risk} Risk</span>
                </div>
                <div class="prediction-rows">
                    <div><span>Result</span><strong>${title}</strong></div>
                    <div><span>Confidence</span><strong>${confidence}</strong></div>
                    ${result.score != null ? `<div><span>Score</span><strong>${result.score}</strong></div>` : ''}
                    ${result.description ? `<div><span>What it means</span><strong>${result.description}</strong></div>` : ''}
                    ${result.action ? `<div><span>Action Required</span><strong>${result.action}</strong></div>` : ''}
                    ${result.diet ? `<div><span>Diet Advice</span><strong>${result.diet}</strong></div>` : ''}
                    ${result.exercise ? `<div><span>Exercise</span><strong>${result.exercise}</strong></div>` : ''}
                </div>
                ${explanation.plain_explanation ? `
                    <section class="prediction-section">
                        <h4>Why this result?</h4>
                        <p>${explanation.plain_explanation}</p>
                    </section>
                ` : ''}
                ${clinicalText ? `
                    <section class="prediction-section">
                        <h4>Clinical interpretation</h4>
                        <p>${clinicalText}</p>
                    </section>
                ` : ''}
                ${factors.length ? `
                    <section class="prediction-section">
                        <h4>Top contributing factors</h4>
                        <div class="factor-list">
                            ${factors.slice(0, 6).map((factor) => `
                                <div class="factor-row">
                                    <strong>${factor.name || factor}</strong>
                                    ${factor.status ? `<span>${factor.status}</span>` : factor.points != null ? `<span>${factor.points} point(s)</span>` : ''}
                                    <p>${factor.explanation || ''}</p>
                                </div>
                            `).join('')}
                        </div>
                    </section>
                ` : ''}
                ${nextSteps.length ? `
                    <section class="prediction-section">
                        <h4>Recommended next steps</h4>
                        <ul>${nextSteps.slice(0, 5).map((step) => `<li>${step}</li>`).join('')}</ul>
                    </section>
                ` : ''}
                <div class="prediction-note">⚠️ This is AI screening guidance, not a diagnosis. Please consult a qualified doctor.</div>
            </div>
        </div>
    `;
}

function syncPregnancyField() {
    const gender = document.getElementById('diabetes-gender')?.value;
    const field = document.getElementById('pregnancy-field');
    const input = document.getElementById('diabetes-pregnancies');
    if (!field || !input) return;
    field.style.display = gender === 'female' ? 'grid' : 'none';
    if (gender !== 'female') input.value = '0';
}

function numberValue(id) {
    const value = document.getElementById(id)?.value;
    return value === '' || value == null ? null : Number(value);
}

function intValue(id) {
    return Number(document.getElementById(id)?.value || 0);
}

async function submitReport(event) {
    event.preventDefault();
    const msg = document.getElementById('report-message');
    msg.textContent = 'Saving report...';
    const patientId = Number(document.getElementById('report-patient-id').value);
    const reportType = document.getElementById('report-type').value;

    try {
        const visit = await hospitalApi('/api/visits/create', {
            method: 'POST',
            body: JSON.stringify({
                patient_id: patientId,
                visit_reason: document.getElementById('report-reason').value || 'AI screening',
                visit_status: 'completed',
            }),
        });

        let endpoint = '/api/reports/diabetes';
        let body = {
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

        if (reportType === 'heart_simple') {
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

        const saved = await hospitalApi(endpoint, { method: 'POST', body: JSON.stringify(body) });
        msg.textContent = `Report saved for visit ${visit.id}`;
        document.getElementById('report-output').innerHTML = item(
            saved.prediction.result || saved.report.risk_level || 'Report saved',
            `Risk: ${saved.prediction.risk || saved.report.risk_level || 'NA'}`
        );
    } catch (error) {
        msg.textContent = error.message;
    }
}

async function loadInsights() {
    const patientId = document.getElementById('insight-patient-id').value;
    if (!patientId) return;
    const [patient, insights, doctorSummaries] = await Promise.all([
        hospitalApi(`/api/patients/${patientId}`),
        hospitalApi(`/api/patients/${patientId}/insights`),
        hospitalApi(`/api/patients/${patientId}/doctor-summaries`),
    ]);
    const doctorWrittenSummary = doctorSummaries.length
        ? doctorSummaries.map((summary) => `
            <div class="item">
                <strong>${summary.doctor_name || 'Doctor'} - ${summary.created_at || ''}</strong>
                <ul>
                    <li>${summary.summary_text}</li>
                    ${summary.medication_suggestions ? `<li><strong>Medication:</strong> ${summary.medication_suggestions}</li>` : ''}
                    ${summary.lifestyle_suggestions ? `<li><strong>Lifestyle:</strong> ${summary.lifestyle_suggestions}</li>` : ''}
                    ${summary.follow_up_advice ? `<li><strong>Follow-up:</strong> ${summary.follow_up_advice}</li>` : ''}
                </ul>
            </div>
        `).join('')
        : item('No doctor-written summary found', 'A doctor has not shared a patient-facing summary yet.');

    document.getElementById('insight-output').innerHTML = `
        ${item(patient.full_name, `${patient.patient_uid} | Age ${patient.age ?? 'NA'} | ${patient.gender}`)}
        <div class="item"><strong>AI Report Summary</strong><ul>${insights.doctor_summary.map((x) => `<li>${x}</li>`).join('')}</ul></div>
        <div class="item"><strong>Doctor-Written Patient Summary</strong></div>
        ${doctorWrittenSummary}
        <div class="item"><strong>Recommendations</strong><ul>${insights.recommendations.map((x) => `<li>${x}</li>`).join('')}</ul></div>
        <button class="no-print" onclick="printPatientInsights()">Print Report</button>
    `;
}

function printPatientInsights() {
    document.body.classList.add('printing-insights');
    window.print();
    window.setTimeout(() => {
        document.body.classList.remove('printing-insights');
    }, 300);
}

async function loadPortalAccess() {
    const patientId = document.getElementById('portal-patient-id')?.value;
    const output = document.getElementById('portal-access-output');
    if (!patientId || !output) return;

    output.innerHTML = item('Loading portal access...');

    try {
        const data = await hospitalApi(`/api/patients/${patientId}/portal-access`);
        const patient = data.patient;
        const account = data.account;

        if (!account) {
            output.innerHTML = `
                ${item(patient.full_name, `${patient.patient_uid} | Patient ID ${patient.id}`)}
                ${item('No patient portal account found', 'Registering new patients now creates access automatically. Add account generation for old patients next.')}
            `;
            return;
        }

        output.innerHTML = `
            ${item(patient.full_name, `${patient.patient_uid} | Patient ID ${patient.id}`)}
            <div class="item">
                <strong>Patient Username</strong>
                <span>${account.username}</span>
            </div>
            <div class="item">
                <strong>Password</strong>
                <span>Hidden for security. Click reset to generate a new temporary password.</span>
            </div>
            <div class="item">
                <strong>Account Status</strong>
                <span>${account.is_active ? 'Active' : 'Inactive'} | Created ${account.created_at || 'NA'}</span>
            </div>
            <button onclick="resetPortalPassword()">Reset Temporary Password</button>
        `;
    } catch (error) {
        output.innerHTML = item('Could not load portal access', error.message);
    }
}

async function resetPortalPassword() {
    const patientId = document.getElementById('portal-patient-id')?.value;
    const output = document.getElementById('portal-access-output');
    if (!patientId || !output) return;

    try {
        const data = await hospitalApi(`/api/patients/${patientId}/portal-access/reset-password`, {
            method: 'POST',
            body: JSON.stringify({}),
        });

        output.innerHTML += `
            <div class="item">
                <strong>New Temporary Password</strong>
                <span>${data.temporary_password}</span>
                <span>Show this to the patient now. It will not be visible again.</span>
            </div>
        `;
    } catch (error) {
        output.innerHTML += item('Could not reset password', error.message);
    }
}
