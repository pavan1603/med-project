setupShell('Register Patients');
renderReportForm();
renderStandalonePredictionForm();

document.getElementById('patient-form').addEventListener('submit', registerPatient);
document.getElementById('patient-search-btn').addEventListener('click', searchPatients);
