# MediRisk Hospital Login Integration - Work Summary

## 1. Overview

After integrating the hospital login workflow, MediRisk was expanded from a prediction and chatbot application into a role-based hospital healthcare assistant. The system now supports hospital staff login, patient registration, report entry, AI prediction, patient history, doctor-written summaries, patient portal access, super admin monitoring, and patient-aware chatbot support.

The work focused on making the project usable in a real hospital-style workflow where hospitals, administrators, doctors, receptionists, and patients have different access levels and responsibilities.

## 2. Role-Based Login System

Implemented a hospital login flow with separate behavior for each role:

- Super Admin
- Hospital Admin
- Doctor
- Receptionist
- Patient

The login system validates staff users and patient users separately. Staff users are authenticated from the `users` table, while patient users are authenticated from the `patient_accounts` table.

After login, users are redirected to role-specific pages:

- Super Admin: `super-admin.html`
- Hospital Admin: `hospital-admin.html`
- Doctor: `doctor.html`
- Receptionist: `receptionist.html`
- Patient: `patient.html`

The patient login was intentionally changed to open the patient portal first instead of directly opening the chatbot, so patients can view their summaries before using the AI assistant.

## 3. Role-Based UI Pages

The original shared hospital dashboard was separated into dedicated role pages for easier maintenance and clearer workflows.

Created or updated:

- `super-admin.html`
- `hospital-admin.html`
- `doctor.html`
- `receptionist.html`
- `patient.html`

Each page has its own JavaScript file:

- `super-admin.js`
- `hospital-admin.js`
- `doctor.js`
- `receptionist.js`
- `patient.js`

Shared role behavior is handled through:

- `hospital-api.js`
- `role-common.js`
- `role-base.css`

This structure makes future editing easier because each role has a focused interface instead of one large mixed dashboard.

## 4. Permission Model

Role permissions were added in `permissions.py`.

Implemented permissions include:

- Hospital admins can manage hospital-level data, register patients, search patients, create visits, run predictions, view hospital analytics, and manage patient portal access.
- Doctors can view patient history, compare visits, view AI explanations, register patients, run predictions, add doctor summaries, and view hospital overview data.
- Receptionists can register patients, search patients, create visits, enter report values, and run predictions.
- Patients can view their own reports, recommendations, and chatbot context.
- Super admins can view all hospitals, all analytics, all patients, audit logs, and global portal access.

The permission model prevents patients and unauthorized roles from accessing global hospital data.

## 5. Database Architecture

A modular SQLite database layer was created under `backend/database`.

Main database tables include:

- `hospital_networks`
- `hospitals`
- `users`
- `patients`
- `patient_consents`
- `patient_accounts`
- `visits`
- `diabetes_reports`
- `heart_reports`
- `doctor_notes`
- `patient_doctor_summaries`
- `chat_sessions`
- `chat_messages`
- `audit_logs`

Indexes were added for faster access to hospitals, users, patients, visits, reports, patient accounts, doctor summaries, chat sessions, and audit logs.

The active database file is:

`backend/medirisk.db`

## 6. Hospital and Patient Workflow

The hospital workflow now supports the following:

- Registering a patient with name, date of birth, gender, phone, language, and address.
- Generating a unique patient UID.
- Searching registered patients by name, phone, or UID.
- Viewing registered patients as a patient-details list.
- Creating visits for patients.
- Saving diabetes and heart reports against visits.
- Viewing patient insights from stored reports.
- Comparing latest and previous patient reports where available.

The hospital admin overview now shows the hospital name and registered patient count instead of unnecessary visit-status widgets.

## 7. Patient Account Generation

Patient portal access was added.

When a new patient is registered, the system automatically creates a patient login account:

- Username is generated using the patient ID.
- A temporary password is generated.
- The password is shown only once after registration.
- The password is stored only as a hash in the database.

Hospital admin and super admin can view:

- Patient name
- Patient UID
- Patient username
- Account active status
- Created date

They cannot view old passwords because passwords are securely hashed. Instead, they can reset the password and generate a new temporary password.

For old patients who do not already have an account, the reset-password workflow can create a new patient account automatically.

## 8. Patient Portal

The patient portal allows patients to view:

- Their health summary
- AI-generated patient guidance
- Doctor-written summaries
- Recommendations
- Chatbot access with stored patient context

The patient can open the chatbot from the portal. The chatbot receives the patient ID so it can include stored hospital report context in responses.

## 9. Doctor Workflow

The doctor login was improved to include:

- Overview dashboard similar to hospital admin
- Registered patient list
- Patient report creation
- Quick prediction
- Patient insights
- Doctor-written patient summary
- Read-only patient chat section placeholder

Doctors can write patient-facing summaries that include:

- Patient condition summary
- Medication suggestions
- Lifestyle or diet suggestions
- Follow-up advice

These summaries are stored in `patient_doctor_summaries` and are visible to hospital admin, super admin, and the patient.

## 10. Hospital Admin Workflow

Hospital admin can:

- View hospital overview
- View registered patients
- Register patients
- Create diabetes and heart reports
- Run quick prediction
- View patient insights
- View doctor-written patient summaries
- View patient portal access
- Reset patient temporary passwords
- Print patient insights

The registered patients view was corrected so clicking the overview patient count opens the patient details list, not the registration form.

## 11. Receptionist Workflow

Receptionist can:

- Register patients
- Search registered patients
- Create patient reports
- Run quick predictions

Receptionist access is intentionally limited compared with doctor and hospital admin. The receptionist does not have super admin analytics or patient portal credential management.

## 12. Super Admin Workflow

Super admin can:

- View global dashboard metrics
- View hospital-wise summaries
- View audit activity
- View patient insights
- View doctor-written patient summaries
- View patient portal usernames
- Reset patient temporary passwords

Super admin is designed for network-level monitoring and governance rather than direct clinical report entry.

## 13. Prediction Features Added to Staff Dashboards

A quick prediction section was added for:

- Hospital Admin
- Doctor
- Receptionist

Supported quick predictions:

- Diabetes risk prediction
- Simple heart risk screening

This quick prediction workflow does not save data to the patient record. It is intended for quick screening only.

Saved patient reports are still handled separately through the patient report workflow.

The quick prediction result UI was improved to match the chatbot-style prediction report. It now shows:

- MediRisk analysis complete status
- Disease report heading
- Risk badge
- Result
- Confidence
- Explanation
- Clinical interpretation
- Top contributing factors
- Recommended next steps
- Medical disclaimer

## 14. Diabetes Prediction Improvements

The diabetes prediction backend was fixed to ensure the model receives input columns in the correct order.

This fixed an XGBoost feature-name mismatch that occurred when prediction inputs were sent from newer UI forms.

Prediction results now include:

- Prediction result
- Confidence
- Risk level
- Clinical explanation
- Top contributing factors
- Next steps

The system no longer claims a diabetes type directly from the basic screening model. Instead, it says diabetes type requires clinical confirmation.

## 15. Heart Disease Workflow Improvements

The heart disease workflow was improved by separating two modes:

- Simple heart risk screening for general users and staff
- Advanced medical report mode for clinical report values

Simple heart screening uses understandable questions such as:

- Age
- Gender
- Chest pain
- Breathlessness while walking
- High blood pressure
- Diabetes
- Smoking
- High cholesterol
- Easy tiredness
- Family history
- Exercise recovery
- Chest pain during exercise

This makes the heart workflow easier for non-technical users.

## 16. Patient Insights and Report Printing

Patient insights were enhanced to include:

- Patient details
- AI report summary
- Doctor-written patient summary
- Recommendations

Printing was corrected so the print action prints only the patient insights/report content, not the sidebar, header, or input controls.

## 17. Chatbot Improvements After Hospital Integration

The chatbot was connected to stored patient context through `patient_id`.

When a patient opens the chatbot from the patient portal, the backend can include stored patient report context in the RAG prompt.

Additional chatbot improvements include:

- Language detection and response translation support
- Telugu and Hindi response support
- Emergency response handling
- Medical safety disclaimers
- Local fallback answers when LLM service fails
- RAG warmup endpoint to reduce first-response delay
- Direct guard responses for common questions such as normal glucose level and heart warning signs

## 18. Multilingual Support

The chatbot supports:

- English
- Telugu
- Hindi

The system can detect the query language and translate queries for English knowledge-base retrieval. Responses can be translated back into the user's language.

Emergency responses include localized fallbacks so urgent cases do not depend entirely on the LLM.

## 19. RAG and Knowledge Base Work

The RAG pipeline was improved with:

- Intent detection
- Query expansion
- Metadata filtering
- Top chunk retrieval
- Context-aware chunk handling
- Reranking logic
- Local fallback answers
- Prompt externalization
- Response cleanup
- Memory summary improvements

The knowledge base was cleaned and re-indexed. The retrieval tests confirmed better retrieval for:

- Diabetes weekly meal plans
- Heart diet Indian plans
- Foods to avoid in diabetes
- Heart disease tests
- South Indian diabetes diet plans

## 20. Safety Layer

The safety layer includes:

- Emergency detection
- Fixed emergency responses
- Medical disclaimers
- Unsafe advice prevention through controlled prompts and fallbacks

Chest pain and emergency symptoms are handled before calling the LLM, so urgent advice does not depend on external AI availability.

## 21. Backend API Additions

Important backend routes include:

- `/api/auth/login`
- `/api/patients/register`
- `/api/patients`
- `/api/patients/search`
- `/api/patients/<patient_id>`
- `/api/patients/<patient_id>/insights`
- `/api/patients/<patient_id>/doctor-summaries`
- `/api/patients/<patient_id>/portal-access`
- `/api/patients/<patient_id>/portal-access/reset-password`
- `/api/visits/create`
- `/api/reports/diabetes`
- `/api/reports/heart`
- `/api/analytics/dashboard`
- `/api/analytics/hospitals`
- `/api/analytics/recent-activity`
- `/predict/diabetes`
- `/screen/heart-simple`
- `/chat`
- `/api/system/warmup-ai`
- `/api/system/warmup-chatbot`

## 22. Testing Performed

Manual and terminal tests were performed for:

- Backend health endpoint
- Login by role
- Hospital admin dashboard
- Doctor dashboard
- Receptionist workflow
- Patient account login
- Patient registration
- Automatic patient credential generation
- Patient portal access reset
- Doctor summary creation
- Doctor summary visibility to hospital admin and super admin
- Diabetes prediction endpoint
- Heart screening endpoint
- Chatbot response endpoint
- RAG warmup
- Knowledge-base retrieval
- JavaScript syntax checks

## 23. Current Limitations

The current implementation is suitable for a demo or academic project, but production deployment would still require:

- Migration from SQLite to PostgreSQL or MySQL for multi-user production use
- Full password reset/change-password flow for patients
- Stronger audit logging for every sensitive action
- Encryption for sensitive medical data
- Session/JWT authentication instead of demo headers
- Better chat persistence UI
- Better hospital user management UI
- Full migrations using Alembic or another migration system
- Deployment hardening and environment-based secrets management
- Rate-limit and API-key cost monitoring for external LLM/translation services

## 24. Final Outcome

After hospital login integration, MediRisk now behaves more like a hospital-ready healthcare assistant instead of a standalone prediction demo.

The project supports:

- Hospital login
- Role-based dashboards
- Patient registration
- Patient portal accounts
- Doctor summaries
- Patient insights
- AI prediction
- Report storage
- Hospital analytics
- Multilingual chatbot support
- Patient-aware AI guidance
- Emergency safety handling

This makes the project suitable for demonstrating a complete AI-assisted healthcare workflow involving hospitals, staff, doctors, patients, reports, and explainable AI guidance.
