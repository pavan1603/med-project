const API_URL = 'http://127.0.0.1:5000';
let currentPredictType = null;
let selectedGender = null;

function createSessionId() {
    if (window.crypto && window.crypto.randomUUID) {
        return window.crypto.randomUUID();
    }
    return `session-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function getChatSessionId() {
    let sessionId = sessionStorage.getItem('medirisk_session_id');
    if (!sessionId) {
        sessionId = createSessionId();
        sessionStorage.setItem('medirisk_session_id', sessionId);
    }
    return sessionId;
}

function resetChatSession() {
    const sessionId = createSessionId();
    sessionStorage.setItem('medirisk_session_id', sessionId);
    return sessionId;
}

function getSelectedLanguage() {
    return localStorage.getItem('medirisk_language') || 'en';
}

function setSelectedLanguage(language) {
    localStorage.setItem('medirisk_language', language);
    const languageSelect = document.getElementById('language-select');
    if (languageSelect && languageSelect.value !== language) {
        languageSelect.value = language;
    }
}

function getPatientIdFromUrl() {
    const params = new URLSearchParams(window.location.search);
    return params.get('patient_id');
}

function setChatbotStatus(text, isReady = false) {
    const status = document.querySelector('.nav-status');
    if (!status) return;
    status.innerHTML = `
        <span class="status-dot"></span>
        ${text}
    `;
    status.classList.toggle('ready', isReady);
}

async function warmupChatbot() {
    setChatbotStatus('Loading AI...');
    try {
        await fetch(`${API_URL}/api/system/warmup-chatbot`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({}),
        });
        setChatbotStatus('AI Ready', true);
    } catch (error) {
        setChatbotStatus('AI Assistant');
    }
}

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

// ===== TIME GREETING =====
function getTimeGreeting() {
    const hour = new Date().getHours();
    if (hour < 12) return "Good Morning";
    if (hour < 17) return "Good Afternoon";
    return "Good Evening";
}

// ===== WELCOME MESSAGE =====
function setWelcomeMessage() {
    const greeting = getTimeGreeting();
    const welcomeEl = document.getElementById('welcome-message');
    if (welcomeEl) {
        welcomeEl.innerHTML = `
            <p>${greeting}! 😊 I'm <strong>MediRisk AI</strong> — your personal health assistant.</p>
            <p>I can help you with:</p>
            <ul>
                <li>🩸 Diabetes risk prediction</li>
                <li>❤️ Heart disease detection</li>
                <li>🥗 Indian diet plans</li>
                <li>💊 Medical questions & advice</li>
            </ul>
            <p>How can I help you today?</p>`;
    }
}

// ===== SEND MESSAGE =====
async function sendMessage() {
    const input = document.getElementById('chat-input');
    const query = input.value.trim();
    if (!query) return;

    addUserMessage(query);
    input.value = '';
    showTyping();

    try {
        const response = await fetch(`${API_URL}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                query,
                session_id: getChatSessionId(),
                language: getSelectedLanguage(),
                patient_id: getPatientIdFromUrl()
            })
        });

        const data = await response.json();
        removeTyping();

        if (data.error) {
            addBotMessage('Sorry, something went wrong. Please try again! 😊');
        } else {
            addBotMessage(data.answer);
        }

    } catch (error) {
        removeTyping();
        addBotMessage('Cannot connect to server. Please make sure the backend is running! 🔧');
    }
}

// ===== ADD USER MESSAGE =====
function addUserMessage(text) {
    const messages = document.getElementById('chat-messages');
    const html = `
        <div class="message user-message">
            <div class="message-avatar"><i class="fas fa-user"></i></div>
            <div class="message-content">
                <div class="message-bubble">${text}</div>
                <span class="message-time">${getCurrentTime()}</span>
            </div>
        </div>`;
    messages.insertAdjacentHTML('beforeend', html);
    scrollToBottom();
}

// ===== ADD BOT MESSAGE — NO SOURCES =====
function addBotMessage(text) {
    const messages = document.getElementById('chat-messages');
    const html = `
        <div class="message bot-message">
            <div class="message-avatar"><i class="fas fa-robot"></i></div>
            <div class="message-content">
                <div class="message-bubble">
                    ${formatMessage(text)}
                </div>
                <span class="message-time">${getCurrentTime()}</span>
            </div>
        </div>`;
    messages.insertAdjacentHTML('beforeend', html);
    scrollToBottom();
}

function escapeHtml(value) {
    return String(value ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

function buildExplanationHtml(explanation) {
    if (!explanation) return '';

    const topFactors = Array.isArray(explanation.top_factors)
        ? explanation.top_factors.slice(0, 5)
        : [];

    const nextSteps = Array.isArray(explanation.next_steps)
        ? explanation.next_steps.slice(0, 4)
        : [];

    const factorHtml = topFactors.map(factor => `
        <li>
            <div class="factor-line">
                <span class="factor-name">${escapeHtml(factor.name)}</span>
                <span class="factor-status ${escapeHtml(factor.status)}">${escapeHtml(factor.status)}</span>
            </div>
            <div class="factor-detail">
                ${escapeHtml(factor.value)} - ${escapeHtml(factor.explanation)}
            </div>
        </li>
    `).join('');

    const nextStepHtml = nextSteps.map(step => `
        <li>${escapeHtml(step)}</li>
    `).join('');

    return `
        <div class="result-explanation">
            <div class="explanation-section">
                <h4>Why this result?</h4>
                <p>${escapeHtml(explanation.plain_explanation)}</p>
            </div>

            <div class="explanation-section">
                <h4>Clinical interpretation</h4>
                <p>${escapeHtml(explanation.clinical_interpretation)}</p>
            </div>

            ${factorHtml ? `
                <div class="explanation-section">
                    <h4>Top contributing factors</h4>
                    <ul class="factor-list">${factorHtml}</ul>
                </div>
            ` : ''}

            ${nextStepHtml ? `
                <div class="explanation-section">
                    <h4>Recommended next steps</h4>
                    <ul class="next-step-list">${nextStepHtml}</ul>
                </div>
            ` : ''}
        </div>
    `;
}

function addSimpleHeartResultCard(result) {
    const messages = document.getElementById('chat-messages');
    const cardClass = result.risk === 'Low' ? 'success' :
                      result.risk === 'Moderate' ? 'warning' : 'danger';

    const factors = Array.isArray(result.top_factors)
        ? result.top_factors.slice(0, 6)
        : [];

    const steps = Array.isArray(result.next_steps)
        ? result.next_steps
        : [];

    const factorHtml = factors.map(factor => `
        <li>
            <strong>${escapeHtml(factor.name)}</strong><br>
            ${escapeHtml(factor.explanation)}
        </li>
    `).join('');

    const stepHtml = steps.map(step => `<li>${escapeHtml(step)}</li>`).join('');

    const html = `
        <div class="message bot-message">
            <div class="message-avatar"><i class="fas fa-robot"></i></div>
            <div class="message-content">
                <div class="message-bubble">
                    <p><strong>Simple Heart Risk Check Complete</strong></p>
                    <div class="result-card ${cardClass}">
                        <div class="result-header">
                            <span class="result-title">Heart Screening Report</span>
                            <span class="result-badge badge-${result.risk === 'Low' ? 'success' : result.risk === 'Moderate' ? 'warning' : 'danger'}">
                                ${escapeHtml(result.risk)} Risk
                            </span>
                        </div>

                        <div class="result-row">
                            <span class="result-label">Result</span>
                            <span class="result-value">${escapeHtml(result.result)}</span>
                        </div>

                        <div class="result-row">
                            <span class="result-label">Score</span>
                            <span class="result-value">${escapeHtml(result.score)}</span>
                        </div>

                        <div class="result-explanation">
                            <div class="explanation-section">
                                <h4>What this means</h4>
                                <p>${escapeHtml(result.description)}</p>
                            </div>

                            <div class="explanation-section">
                                <h4>Recommended action</h4>
                                <p>${escapeHtml(result.action)}</p>
                            </div>

                            ${factorHtml ? `
                                <div class="explanation-section">
                                    <h4>Main risk factors</h4>
                                    <ul class="next-step-list">${factorHtml}</ul>
                                </div>
                            ` : ''}

                            ${stepHtml ? `
                                <div class="explanation-section">
                                    <h4>Next steps</h4>
                                    <ul class="next-step-list">${stepHtml}</ul>
                                </div>
                            ` : ''}
                        </div>
                    </div>

                    <p style="margin-top:10px;font-size:0.75rem;color:var(--text-soft);">
                        This is a screening result, not a diagnosis. Please consult a qualified doctor.
                    </p>
                </div>
                <span class="message-time">${getCurrentTime()}</span>
            </div>
        </div>`;

    messages.insertAdjacentHTML('beforeend', html);
    scrollToBottom();
}


// ===== ADD RESULT CARD =====
function addResultCard(result, type) {
    const messages = document.getElementById('chat-messages');
    const cardClass = result.risk === 'Low' ? 'success' :
                      result.risk === 'Moderate' ? 'warning' : 'danger';
    const badgeClass = result.risk === 'Low' ? 'badge-success' :
                       result.risk === 'Moderate' ? 'badge-warning' : 'badge-danger';

    let rows = '';
    if (type === 'diabetes') {
        rows = `
            <div class="result-row">
                <span class="result-label">Diabetes Type</span>
                <span class="result-value">${result.diabetes_type || 'Requires clinical confirmation'}</span>
            </div>
            ${result.type_description ? `
                <div class="result-row">
                    <span class="result-label">Type Note</span>
                    <span class="result-value">${escapeHtml(result.type_description)}</span>
                </div>
            ` : ''}
            <div class="result-row">
                <span class="result-label">Confidence</span>
                <span class="result-value">${result.confidence}%</span>
            </div>
            <div class="result-row">
                <span class="result-label">Diabetes Type</span>
                <span class="result-value">${result.diabetes_type}</span>
            </div>
            <div class="result-row">
                <span class="result-label">What it means</span>
                <span class="result-value">${result.description}</span>
            </div>
            <div class="result-row">
                <span class="result-label">Action Required</span>
                <span class="result-value">${result.action}</span>
            </div>
            <div class="result-row">
                <span class="result-label">Diet Advice</span>
                <span class="result-value">${result.diet}</span>
            </div>
            <div class="result-row">
                <span class="result-label">Exercise</span>
                <span class="result-value">${result.exercise}</span>
            </div>`;
    } else {
        rows = `
            <div class="result-row">
                <span class="result-label">Result</span>
                <span class="result-value">${result.result}</span>
            </div>
            <div class="result-row">
                <span class="result-label">Confidence</span>
                <span class="result-value">${result.confidence}%</span>
            </div>
            <div class="result-row">
                <span class="result-label">What it means</span>
                <span class="result-value">${result.description}</span>
            </div>
            <div class="result-row">
                <span class="result-label">Action Required</span>
                <span class="result-value">${result.action}</span>
            </div>
            <div class="result-row">
                <span class="result-label">Diet Advice</span>
                <span class="result-value">${result.diet}</span>
            </div>
            <div class="result-row">
                <span class="result-label">Exercise</span>
                <span class="result-value">${result.exercise}</span>
            </div>`;
    }
        const explanationHtml = buildExplanationHtml(result.explanation);

    const html = `
        <div class="message bot-message">
            <div class="message-avatar"><i class="fas fa-robot"></i></div>
            <div class="message-content">
                <div class="message-bubble">
                    <p><strong>MediRisk Analysis Complete ✅</strong></p>
                    <div class="result-card ${cardClass}">
                        <div class="result-header">
                            <span class="result-title">
                                ${type === 'diabetes' ? '🩸 Diabetes Risk Report' : '❤️ Heart Disease Report'}
                            </span>
                            <span class="result-badge ${badgeClass}">${result.risk} Risk</span>
                        </div>
                        ${rows}
                        ${explanationHtml}
                    </div>
                    <p style="margin-top:10px;font-size:0.75rem;color:var(--text-soft);">
                        ⚠️ Always consult a qualified doctor for proper diagnosis.
                    </p>
                </div>
                <span class="message-time">${getCurrentTime()}</span>
            </div>
        </div>`;
    messages.insertAdjacentHTML('beforeend', html);
    scrollToBottom();
}

// ===== TYPING =====
function showTyping() {
    const messages = document.getElementById('chat-messages');
    const html = `
        <div class="typing-indicator" id="typing">
            <div class="message-avatar"><i class="fas fa-robot"></i></div>
            <div class="typing-dots">
                <span></span><span></span><span></span>
            </div>
        </div>`;
    messages.insertAdjacentHTML('beforeend', html);
    scrollToBottom();
}

function removeTyping() {
    const typing = document.getElementById('typing');
    if (typing) typing.remove();
}

// ===== GENDER =====
function selectGender(gender) {
    selectedGender = gender;
    document.querySelectorAll('.gender-btn').forEach(b => b.classList.remove('active'));
    document.getElementById(`gender-${gender}`).classList.add('active');
    const pf = document.getElementById('pregnancies-field');
    if (pf) pf.style.display = gender === 'female' ? 'flex' : 'none';
}

function addHeartModeChoice() {
    const messages = document.getElementById('chat-messages');

    const html = `
        <div class="message bot-message">
            <div class="message-avatar"><i class="fas fa-robot"></i></div>
            <div class="message-content">
                <div class="message-bubble">
                    <p><strong>Choose Heart Check Type</strong></p>
                    <div class="heart-mode-actions">
                        <button onclick="showSimpleHeartForm()" class="heart-mode-btn">
                            <i class="fas fa-heart-pulse"></i>
                            <span>
                                <strong>Simple Heart Risk Check</strong>
                                <small>For users without medical reports</small>
                            </span>
                        </button>
                        <button onclick="showPredictForm('heart-advanced')" class="heart-mode-btn">
                            <i class="fas fa-file-medical"></i>
                            <span>
                                <strong>Advanced Medical Report Mode</strong>
                                <small>Use only if you have medical report values such as cholesterol, ECG or stress-test data</small>
                            </span>
                        </button>
                    </div>
                </div>
                <span class="message-time">${getCurrentTime()}</span>
            </div>
        </div>`;

    messages.insertAdjacentHTML('beforeend', html);
    scrollToBottom();
}

// ===== PREDICT FORMS =====
function showPredictForm(type) {
    if (type === 'heart') {
        addHeartModeChoice();
        return;
    }

    currentPredictType = type === 'heart-advanced' ? 'heart' : type;
    selectedGender = null;

    const form = document.getElementById('predict-form');
    const title = document.getElementById('form-title');
    const body = document.getElementById('form-body');
    form.style.display = 'flex';

    if (type === 'diabetes') {
        title.textContent = '🩸 Diabetes Risk Assessment';
        body.innerHTML = `
            <div class="form-group full-width">
                <label>Select Your Gender</label>
                <div class="gender-selector">
                    <button class="gender-btn" id="gender-male" onclick="selectGender('male')">
                        <i class="fas fa-mars"></i> Male
                    </button>
                    <button class="gender-btn" id="gender-female" onclick="selectGender('female')">
                        <i class="fas fa-venus"></i> Female
                    </button>
                </div>
            </div>
            <div class="form-group" id="pregnancies-field" style="display:none;">
                <label>Number of Pregnancies</label>
                <input type="number" id="f_pregnancies" placeholder="e.g. 2" min="0" max="17">
                <span class="field-hint">How many times have you been pregnant?</span>
            </div>
            <div class="form-group">
                <label>Glucose Level (mg/dL)</label>
                <input type="number" id="f_glucose" placeholder="e.g. 120">
                <span class="field-hint">Fasting blood sugar level</span>
            </div>
            <div class="form-group">
                <label>Blood Pressure (mmHg)</label>
                <input type="number" id="f_bp" placeholder="e.g. 80">
                <span class="field-hint">Diastolic blood pressure</span>
            </div>
            <div class="form-group">
                <label>Skin Thickness (mm)</label>
                <input type="number" id="f_skin" placeholder="e.g. 20">
                <span class="field-hint">Tricep skin fold thickness</span>
            </div>
            <div class="form-group">
                <label>Insulin Level (mu U/ml)</label>
                <input type="number" id="f_insulin" placeholder="e.g. 100">
                <span class="field-hint">2-hour serum insulin level</span>
            </div>
            <div class="form-group">
                <label>BMI (Body Mass Index)</label>
                <input type="number" id="f_bmi" placeholder="e.g. 28.5" step="0.1">
                <span class="field-hint">Weight(kg) divided by Height(m)²</span>
            </div>
            <div class="form-group">
                <label>Age (Years)</label>
                <input type="number" id="f_age" placeholder="e.g. 35">
                <span class="field-hint">Your current age</span>
            </div>`;

    } else if (type === 'heart-advanced') {
        title.textContent = '❤️ Heart Disease Risk Assessment';
        body.innerHTML = `
            <div class="form-group">
                <label>Age (Years)</label>
                <input type="number" id="h_age" placeholder="e.g. 50">
            </div>
            <div class="form-group">
                <label>Sex</label>
                <select id="h_sex">
                    <option value="1">Male</option>
                    <option value="0">Female</option>
                </select>
            </div>
            <div class="form-group full-width">
                <label>Chest Pain Type</label>
                <select id="h_cp">
                    <option value="asymptomatic">No chest pain at all - report-based risk can still exist</option>
                    <option value="typical angina">Pressure or squeezing in chest during activity</option>
                    <option value="atypical angina">Unusual chest discomfort, not typical heart pain</option>
                    <option value="non-anginal">Chest pain clearly not related to heart</option>
                </select>
                <span class="field-hint">Choose the option that best describes your chest symptoms</span>
            </div>
            <div class="form-group">
                <label>Blood Pressure (mmHg)</label>
                <input type="number" id="h_bp" placeholder="e.g. 130">
                <span class="field-hint">Resting blood pressure reading</span>
            </div>
            <div class="form-group">
                <label>Cholesterol (mg/dL)</label>
                <input type="number" id="h_chol" placeholder="e.g. 200">
                <span class="field-hint">Total cholesterol from blood test</span>
            </div>
            <div class="form-group">
                <label>Fasting Blood Sugar above 120 mg/dL?</label>
                <select id="h_fbs">
                    <option value="0">No — My blood sugar is normal</option>
                    <option value="1">Yes — My blood sugar is high</option>
                </select>
            </div>
            <div class="form-group">
                <label>Maximum Heart Rate During Exercise</label>
                <input type="number" id="h_thalch" placeholder="e.g. 150">
                <span class="field-hint">Highest heart rate you reached during exercise</span>
            </div>
            <div class="form-group">
                <label>Do you feel chest pain during exercise?</label>
                <select id="h_exang">
                    <option value="0">No — No chest pain during exercise</option>
                    <option value="1">Yes — I feel chest pain when exercising</option>
                </select>
            </div>
            <div class="form-group full-width">
                <label>Heart Stress Level During Exercise (ST Depression)</label>
                <input type="number" id="h_oldpeak" placeholder="e.g. 1.5" step="0.1">
                <span class="field-hint">0 = Normal heart | 1-2 = Mild stress | 3-6 = Severe stress. Check your ECG report for this value. If unsure enter 0.</span>
            </div>
            <div class="form-group">
                <label>Number of Blocked Heart Vessels (0-3)</label>
                <input type="number" id="h_ca" placeholder="0" min="0" max="3">
                <span class="field-hint">0 = No blockage (healthy) | 1-3 = Blocked arteries</span>
            </div>
            <div class="form-group full-width">
                <label>How does your heart recover after exercise?</label>
                <select id="h_slope">
                    <option value="upsloping">Gets better quickly — Heart recovers well (healthy)</option>
                    <option value="flat">Stays the same — Moderate concern</option>
                    <option value="downsloping">Gets worse — Heart struggling (high risk)</option>
                </select>
                <span class="field-hint">How you feel after peak exercise — if unsure choose "Gets better quickly"</span>
            </div>
            <div class="form-group">
                <label>Do you have any blood disorder (Thalassemia)?</label>
                <select id="h_thal">
                    <option value="normal">No — I have no blood disorder</option>
                    <option value="fixed defect">Yes — I have a permanent blood/heart condition</option>
                    <option value="reversable defect">Sometimes — I have a temporary blood condition</option>
                </select>
            </div>
            <div class="form-group">
                <label>Have you ever been told you have heart problems?</label>
                <select id="h_restecg">
                    <option value="normal">No — My heart tests are normal</option>
                    <option value="lv hypertrophy">Yes — I have enlarged heart muscle</option>
                    <option value="st-t abnormality">Yes — I have irregular heart signals</option>
                </select>
            </div>`;
    }
}


function showSimpleHeartForm() {
    currentPredictType = 'heart-simple';

    const form = document.getElementById('predict-form');
    const title = document.getElementById('form-title');
    const body = document.getElementById('form-body');

    form.style.display = 'flex';
    title.textContent = 'Simple Heart Risk Check';

    body.innerHTML = `
        <div class="form-group">
            <label>Age</label>
            <input type="number" id="s_age" placeholder="e.g. 45">
        </div>

        <div class="form-group">
            <label>Gender</label>
            <select id="s_gender">
                <option value="male">Male</option>
                <option value="female">Female</option>
            </select>
        </div>

        <div class="form-group">
            <label>Do you have chest pain?</label>
            <select id="s_chest_pain">
                <option value="no">No</option>
                <option value="yes">Yes</option>
            </select>
        </div>

        <div class="form-group">
            <label>Do you feel breathless while walking?</label>
            <select id="s_breathless">
                <option value="no">No</option>
                <option value="yes">Yes</option>
            </select>
        </div>

        <div class="form-group">
            <label>Do you have high BP?</label>
            <select id="s_high_bp">
                <option value="no">No</option>
                <option value="yes">Yes</option>
            </select>
        </div>

        <div class="form-group">
            <label>Do you have diabetes?</label>
            <select id="s_diabetes">
                <option value="no">No</option>
                <option value="yes">Yes</option>
            </select>
        </div>

        <div class="form-group">
            <label>Do you smoke?</label>
            <select id="s_smoker">
                <option value="no">No</option>
                <option value="yes">Yes</option>
            </select>
        </div>

        <div class="form-group">
            <label>Do you have high cholesterol?</label>
            <select id="s_cholesterol">
                <option value="no">No</option>
                <option value="yes">Yes</option>
            </select>
        </div>

        <div class="form-group">
            <label>Do you get tired easily?</label>
            <select id="s_tired">
                <option value="no">No</option>
                <option value="yes">Yes</option>
            </select>
        </div>

        <div class="form-group">
            <label>Family history of heart disease?</label>
            <select id="s_family">
                <option value="no">No</option>
                <option value="yes">Yes</option>
            </select>
        </div>

        <div class="form-group">
            <label>How does your heart recover after exercise?</label>
            <select id="s_recovery">
                <option value="normal">Normal</option>
                <option value="average">Slow sometimes</option>
                <option value="poor">Poor / very slow</option>
            </select>
        </div>

        <div class="form-group">
            <label>Chest pain during exercise?</label>
            <select id="s_exercise_chest_pain">
                <option value="no">No</option>
                <option value="yes">Yes</option>
            </select>
        </div>`;
}

function closePredictForm() {
    document.getElementById('predict-form').style.display = 'none';
}

// ===== SUBMIT PREDICTION =====
async function submitPrediction() {
    const predictType = currentPredictType;
    let data = {};
    let endpoint = '';

    if (predictType === 'diabetes') {
        if (!selectedGender) {
            alert('Please select your gender first!');
            return;
        }
        data = {
            Pregnancies: selectedGender === 'female' ?
                (parseFloat(document.getElementById('f_pregnancies').value) || 0) : 0,
            Glucose: parseFloat(document.getElementById('f_glucose').value) || 120,
            BloodPressure: parseFloat(document.getElementById('f_bp').value) || 70,
            SkinThickness: parseFloat(document.getElementById('f_skin').value) || 20,
            Insulin: parseFloat(document.getElementById('f_insulin').value) || 100,
            BMI: parseFloat(document.getElementById('f_bmi').value) || 25,
            DiabetesPedigreeFunction: 0.3,
            Age: parseFloat(document.getElementById('f_age').value) || 30
        };
        endpoint = '/predict/diabetes';
    } else if (predictType === 'heart-simple') {
        data = {
            age: parseFloat(document.getElementById('s_age').value) || 40,
            gender: document.getElementById('s_gender').value,
            chest_pain: document.getElementById('s_chest_pain').value,
            breathless_walking: document.getElementById('s_breathless').value,
            high_bp: document.getElementById('s_high_bp').value,
            diabetes: document.getElementById('s_diabetes').value,
            smoker: document.getElementById('s_smoker').value,
            high_cholesterol: document.getElementById('s_cholesterol').value,
            tired_easily: document.getElementById('s_tired').value,
            family_history: document.getElementById('s_family').value,
            exercise_recovery: document.getElementById('s_recovery').value,
            exercise_chest_pain: document.getElementById('s_exercise_chest_pain').value
        };

        endpoint = '/screen/heart-simple';
    } else if (predictType === 'heart') {
        const cp = document.getElementById('h_cp').value;
        const slope = document.getElementById('h_slope').value;
        const thal = document.getElementById('h_thal').value;
        const restecg = document.getElementById('h_restecg').value;

        data = {
            age: parseFloat(document.getElementById('h_age').value) || 50,
            sex: parseInt(document.getElementById('h_sex').value),
            trestbps: parseFloat(document.getElementById('h_bp').value) || 130,
            chol: parseFloat(document.getElementById('h_chol').value) || 200,
            fbs: parseInt(document.getElementById('h_fbs').value),
            thalch: parseFloat(document.getElementById('h_thalch').value) || 140,
            exang: parseInt(document.getElementById('h_exang').value),
            oldpeak: parseFloat(document.getElementById('h_oldpeak').value) || 0,
            ca: parseFloat(document.getElementById('h_ca').value) || 0,
            'cp_asymptomatic': cp === 'asymptomatic' ? 1 : 0,
            'cp_atypical angina': cp === 'atypical angina' ? 1 : 0,
            'cp_non-anginal': cp === 'non-anginal' ? 1 : 0,
            'cp_typical angina': cp === 'typical angina' ? 1 : 0,
            'restecg_lv hypertrophy': restecg === 'lv hypertrophy' ? 1 : 0,
            'restecg_normal': restecg === 'normal' ? 1 : 0,
            'restecg_st-t abnormality': restecg === 'st-t abnormality' ? 1 : 0,
            'slope_downsloping': slope === 'downsloping' ? 1 : 0,
            'slope_flat': slope === 'flat' ? 1 : 0,
            'slope_upsloping': slope === 'upsloping' ? 1 : 0,
            'thal_fixed defect': thal === 'fixed defect' ? 1 : 0,
            'thal_normal': thal === 'normal' ? 1 : 0,
            'thal_reversable defect': thal === 'reversable defect' ? 1 : 0
        };
        endpoint = '/predict/heart';
    }

    closePredictForm();
    addUserMessage(`Analyzing my ${predictType === 'diabetes' ? 'diabetes' : 'heart disease'} risk...`);
    showTyping();

    try {
        const response = await fetch(`${API_URL}${endpoint}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        const result = await response.json();
        removeTyping();
        if (predictType === 'heart-simple') {
            addSimpleHeartResultCard(result);
        } else {
            addResultCard(result, predictType);
        }

    } catch (error) {
        removeTyping();
        addBotMessage('Cannot connect to server. Please make sure the backend is running! 🔧');
    }
}

// ===== QUICK ASK =====
function quickAsk(question) {
    document.getElementById('chat-input').value = question;
    sendMessage();
}

// ===== NEW CHAT =====
function newChat() {
    resetChatSession();
    const greeting = getTimeGreeting();
    document.getElementById('chat-messages').innerHTML = `
        <div class="message bot-message">
            <div class="message-avatar"><i class="fas fa-robot"></i></div>
            <div class="message-content">
                <div class="message-bubble">
                    <p id="welcome-message">${greeting}! 😊 I'm <strong>MediRisk AI</strong> — your personal health assistant.</p>
                    <p>How can I help you today?</p>
                </div>
                <span class="message-time">Just now</span>
            </div>
        </div>`;
}

// ===== HELPERS =====
function handleKeyPress(e) { if (e.key === 'Enter') sendMessage(); }

function scrollToBottom() {
    const m = document.getElementById('chat-messages');
    m.scrollTop = m.scrollHeight;
}

function getCurrentTime() {
    return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function formatMessage(text) {
    return text
        .replace(/\n/g, '<br>')
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/🩸|❤️|💊|📊|🥗|😊|✅|⚠️|💪|🔧/g, match => `<span>${match}</span>`);
}

// ===== INIT =====
window.addEventListener('load', () => {
    const languageSelect = document.getElementById('language-select');
    if (languageSelect) {
        languageSelect.value = getSelectedLanguage();
    }
    setWelcomeMessage();
    warmupChatbot();
});
