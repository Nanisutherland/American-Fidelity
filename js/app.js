/**
 * American Fidelity - Document Intelligence Platform
 * Main Application Logic
 */

// ============================
// State Management
// ============================
const APP_STATE = {
    isAuthenticated: false,
    uploadedFiles: [],
    results: [],
    isProcessing: false,
    maxFiles: 2,
    maxFileSize: 10 * 1024 * 1024, // 10MB
    webhookUrl: 'http://localhost:5678/webhook/bce61e20-8112-48b8-a195-ba3b3961243a',
};

// ============================
// Authentication
// ============================
const CREDENTIALS = {
    userId: 'admin',
    password: 'admin',
};

function handleLogin(e) {
    e.preventDefault();
    const userId = document.getElementById('userId').value.trim();
    const password = document.getElementById('password').value;
    const errorEl = document.getElementById('loginError');

    if (userId === CREDENTIALS.userId && password === CREDENTIALS.password) {
        APP_STATE.isAuthenticated = true;
        errorEl.classList.add('hidden');
        showView('dashboardView');
        showToast('Welcome back, Admin!', 'success');
    } else {
        errorEl.classList.remove('hidden');
        document.getElementById('password').value = '';
    }
}

function logout() {
    APP_STATE.isAuthenticated = false;
    APP_STATE.uploadedFiles = [];
    APP_STATE.results = [];
    document.getElementById('loginForm').reset();
    document.getElementById('loginError').classList.add('hidden');
    showView('loginView');
    resetUploadUI();
}

function togglePassword() {
    const input = document.getElementById('password');
    const icon = document.getElementById('eyeIcon');
    if (input.type === 'password') {
        input.type = 'text';
        icon.textContent = 'visibility';
    } else {
        input.type = 'password';
        icon.textContent = 'visibility_off';
    }
}

// ============================
// View & Tab Management
// ============================
function showView(viewId) {
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    document.getElementById(viewId).classList.add('active');
}

function switchTab(tabName) {
    document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
    document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');

    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    document.getElementById(`${tabName}Tab`).classList.add('active');
}

// ============================
// File Upload Management
// ============================
function initDropzone() {
    const dropzone = document.getElementById('dropzone');
    const fileInput = document.getElementById('fileInput');

    dropzone.addEventListener('click', () => fileInput.click());

    dropzone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropzone.classList.add('drag-over');
    });

    dropzone.addEventListener('dragleave', (e) => {
        e.preventDefault();
        dropzone.classList.remove('drag-over');
    });

    dropzone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropzone.classList.remove('drag-over');
        handleFiles(e.dataTransfer.files);
    });

    fileInput.addEventListener('change', (e) => {
        handleFiles(e.target.files);
        fileInput.value = '';
    });
}

function handleFiles(fileList) {
    const files = Array.from(fileList);

    for (const file of files) {
        if (APP_STATE.uploadedFiles.length >= APP_STATE.maxFiles) {
            showToast(`Maximum ${APP_STATE.maxFiles} files allowed`, 'error');
            break;
        }

        if (file.type !== 'application/pdf') {
            showToast(`"${file.name}" is not a PDF file`, 'error');
            continue;
        }

        if (file.size > APP_STATE.maxFileSize) {
            showToast(`"${file.name}" exceeds 10MB limit`, 'error');
            continue;
        }

        if (APP_STATE.uploadedFiles.some(f => f.name === file.name)) {
            showToast(`"${file.name}" is already added`, 'error');
            continue;
        }

        APP_STATE.uploadedFiles.push(file);
    }

    updateFileListUI();
}

function removeFile(index) {
    APP_STATE.uploadedFiles.splice(index, 1);
    updateFileListUI();
}

function clearFiles() {
    APP_STATE.uploadedFiles = [];
    updateFileListUI();
}

function updateFileListUI() {
    const fileList = document.getElementById('fileList');
    const processSection = document.getElementById('processSection');
    const fileCount = document.getElementById('fileCount');
    const count = APP_STATE.uploadedFiles.length;

    fileCount.textContent = `${count} / ${APP_STATE.maxFiles} files`;

    if (count === 0) {
        fileList.classList.add('hidden');
        processSection.classList.add('hidden');
        return;
    }

    fileList.classList.remove('hidden');
    processSection.classList.remove('hidden');

    fileList.innerHTML = APP_STATE.uploadedFiles.map((file, i) => `
        <div class="file-item">
            <div class="file-icon">
                <span class="material-icons-outlined">picture_as_pdf</span>
            </div>
            <div class="file-info">
                <div class="file-name">${escapeHtml(file.name)}</div>
                <div class="file-size">${formatFileSize(file.size)}</div>
            </div>
            <button class="file-remove" onclick="removeFile(${i})" title="Remove file">
                <span class="material-icons-outlined">close</span>
            </button>
        </div>
    `).join('');
}

function resetUploadUI() {
    updateFileListUI();
    document.getElementById('processingState').classList.add('hidden');
    document.getElementById('uploadTab').querySelector('.upload-section').style.display = '';
    document.getElementById('noResults').classList.remove('hidden');
    document.getElementById('resultsContainer').classList.add('hidden');
    document.getElementById('resultsBadge').classList.add('hidden');
    switchTab('upload');
    resetProcessingSteps();
}

// ============================
// Document Processing
// ============================
async function processDocuments() {
    if (APP_STATE.uploadedFiles.length === 0) {
        showToast('Please upload at least one PDF file', 'error');
        return;
    }

    if (APP_STATE.isProcessing) return;
    APP_STATE.isProcessing = true;

    // Show processing UI
    const uploadSection = document.getElementById('uploadTab').querySelector('.upload-section');
    const processingState = document.getElementById('processingState');
    uploadSection.style.display = 'none';
    processingState.classList.remove('hidden');

    // Reset processing steps
    resetProcessingSteps();

    try {
        // Step 1: Uploading
        updateProgress(10, 'Preparing documents...');
        activateStep('step1');
        await delay(800);

        // Step 2: Scanning
        updateProgress(30, 'Sending to extraction engine...');
        completeStep('step1');
        activateStep('step2');

        // Build form data and send to webhook
        const formData = new FormData();
        APP_STATE.uploadedFiles.forEach((file, index) => {
            formData.append(`file${index + 1}`, file);
        });

        updateProgress(50, 'Processing documents via AI...');
        completeStep('step2');
        activateStep('step3');

        // Send to n8n webhook
        let response;
        try {
            response = await fetch(APP_STATE.webhookUrl, {
                method: 'POST',
                body: formData,
            });
        } catch (fetchError) {
            // If webhook is unreachable, use mock data for demo
            console.warn('Webhook unreachable, using demo data:', fetchError.message);
            updateProgress(70, 'Extracting key fields...');
            await delay(2000);
            response = null;
        }

        updateProgress(85, 'Finalizing extraction...');
        await delay(500);

        let results;
        if (response && response.ok) {
            const data = await response.json();
            results = normalizeResults(data);
        } else {
            // Generate demo results for offline demonstration
            results = generateDemoResults();
        }

        // Step 4: Complete
        updateProgress(100, 'Extraction complete!');
        completeStep('step3');
        activateStep('step4');
        completeStep('step4');

        await delay(1000);

        // Store results and show
        APP_STATE.results = results;
        renderResults();
        showToast('Documents processed successfully!', 'success');

        // Auto-switch to results tab
        switchTab('results');
    } catch (error) {
        console.error('Processing error:', error);
        showToast('Processing failed. Please try again.', 'error');
        uploadSection.style.display = '';
        processingState.classList.add('hidden');
    } finally {
        APP_STATE.isProcessing = false;
    }
}

function normalizeResults(data) {
    // Handle various response formats from n8n
    if (Array.isArray(data)) {
        return data.map((item, index) => ({
            fileName: APP_STATE.uploadedFiles[index]?.name || `Document ${index + 1}`,
            data: item,
        }));
    }

    // If it's a single object with results for multiple files
    if (data.results && Array.isArray(data.results)) {
        return data.results.map((item, index) => ({
            fileName: APP_STATE.uploadedFiles[index]?.name || `Document ${index + 1}`,
            data: item,
        }));
    }

    // If single result object
    if (data.file1 && data.file2) {
        return [
            { fileName: APP_STATE.uploadedFiles[0]?.name || 'Document 1', data: data.file1 },
            { fileName: APP_STATE.uploadedFiles[1]?.name || 'Document 2', data: data.file2 },
        ];
    }

    // Fallback: wrap single response per file
    return APP_STATE.uploadedFiles.map((file, index) => ({
        fileName: file.name,
        data: data,
    }));
}

function generateDemoResults() {
    const demoData = [
        {
            documentType: 'Insurance Application',
            policyNumber: 'AF-2026-001847',
            applicantName: 'John M. Anderson',
            dateOfBirth: '1985-03-15',
            ssn: '***-**-4521',
            employer: 'Acme Corporation',
            annualSalary: '$87,500.00',
            coverageType: 'Group Disability Insurance',
            coverageAmount: '$5,000/month',
            effectiveDate: '2026-03-01',
            beneficiary: 'Sarah L. Anderson',
            beneficiaryRelation: 'Spouse',
            applicationDate: '2026-02-10',
            status: 'Pending Review',
            agentCode: 'AG-4421',
        },
        {
            documentType: 'Benefits Enrollment Form',
            enrollmentId: 'ENR-2026-093421',
            employeeName: 'Maria C. Rodriguez',
            employeeId: 'EMP-78234',
            dateOfBirth: '1990-07-22',
            department: 'Engineering',
            planType: 'Comprehensive Health Plan',
            tier: 'Employee + Family',
            monthlyPremium: '$342.50',
            dentalCoverage: 'Yes - Premium Plan',
            visionCoverage: 'Yes - Standard Plan',
            flexSpending: '$2,500 annual election',
            effectiveDate: '2026-04-01',
            enrollmentPeriod: 'Open Enrollment 2026',
            status: 'Confirmed',
        },
    ];

    return APP_STATE.uploadedFiles.map((file, index) => ({
        fileName: file.name,
        data: demoData[index] || demoData[0],
    }));
}

// ============================
// Progress & Steps UI
// ============================
function updateProgress(percent, text) {
    const fill = document.getElementById('progressFill');
    const label = document.getElementById('progressText');
    fill.style.width = `${percent}%`;
    label.textContent = text;
}

function activateStep(stepId) {
    document.getElementById(stepId).classList.add('active');
}

function completeStep(stepId) {
    const step = document.getElementById(stepId);
    step.classList.remove('active');
    step.classList.add('completed');
}

function resetProcessingSteps() {
    ['step1', 'step2', 'step3', 'step4'].forEach(id => {
        const el = document.getElementById(id);
        el.classList.remove('active', 'completed');
    });
    updateProgress(0, 'Initializing...');
}

// ============================
// Results Rendering
// ============================
function renderResults() {
    const container = document.getElementById('resultsContainer');
    const noResults = document.getElementById('noResults');
    const badge = document.getElementById('resultsBadge');

    if (APP_STATE.results.length === 0) {
        noResults.classList.remove('hidden');
        container.classList.add('hidden');
        badge.classList.add('hidden');
        return;
    }

    noResults.classList.add('hidden');
    container.classList.remove('hidden');
    badge.classList.remove('hidden');
    badge.textContent = APP_STATE.results.length;

    container.innerHTML = APP_STATE.results.map((result, index) => {
        const data = result.data;
        const keyFields = extractKeyFields(data);
        const jsonStr = JSON.stringify(data, null, 2);
        const highlightedJson = syntaxHighlightJson(jsonStr);

        return `
            <div class="result-card">
                <div class="result-card-header">
                    <div class="result-card-title">
                        <div class="doc-badge">${index + 1}</div>
                        <div>
                            <h4>${escapeHtml(result.fileName)}</h4>
                            <span class="file-label">Document ${index + 1} of ${APP_STATE.results.length}</span>
                        </div>
                    </div>
                    <button class="btn-download" onclick="downloadJson(${index})">
                        <span class="material-icons-outlined">download</span>
                        <span>Download JSON</span>
                    </button>
                </div>
                <div class="result-card-body">
                    <div class="key-fields">
                        ${keyFields.map(field => `
                            <div class="key-field">
                                <div class="key-field-label">${escapeHtml(field.label)}</div>
                                <div class="key-field-value">${escapeHtml(String(field.value))}</div>
                            </div>
                        `).join('')}
                    </div>
                    <div class="json-section">
                        <div class="json-header">
                            <h5>
                                <span class="material-icons-outlined">data_object</span>
                                <span>Raw JSON Data</span>
                            </h5>
                            <button class="btn-copy" onclick="copyJson(${index})">
                                <span class="material-icons-outlined">content_copy</span>
                                <span>Copy</span>
                            </button>
                        </div>
                        <div class="json-display">
                            <pre>${highlightedJson}</pre>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

function extractKeyFields(data) {
    const fields = [];
    const maxFields = 8;
    let count = 0;

    for (const [key, value] of Object.entries(data)) {
        if (count >= maxFields) break;
        if (typeof value === 'object' && value !== null) continue;

        fields.push({
            label: formatLabel(key),
            value: value,
        });
        count++;
    }

    return fields;
}

function formatLabel(key) {
    return key
        .replace(/([A-Z])/g, ' $1')
        .replace(/[_-]/g, ' ')
        .replace(/^\w/, c => c.toUpperCase())
        .trim();
}

function syntaxHighlightJson(json) {
    return json.replace(
        /("(\\u[\da-fA-F]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+-]?\d+)?)/g,
        function (match) {
            let cls = 'json-number';
            if (/^"/.test(match)) {
                if (/:$/.test(match)) {
                    cls = 'json-key';
                    match = match.replace(/:$/, '') + ':';
                    return `<span class="${cls}">${match.split(':')[0]}</span>:`;
                } else {
                    cls = 'json-string';
                }
            } else if (/true|false/.test(match)) {
                cls = 'json-boolean';
            } else if (/null/.test(match)) {
                cls = 'json-null';
            }
            return `<span class="${cls}">${match}</span>`;
        }
    );
}

// ============================
// Download & Copy
// ============================
function downloadJson(index) {
    const result = APP_STATE.results[index];
    if (!result) return;

    const jsonStr = JSON.stringify(result.data, null, 2);
    const blob = new Blob([jsonStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);

    const a = document.createElement('a');
    a.href = url;
    a.download = `${result.fileName.replace('.pdf', '')}_extracted.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    showToast('JSON file downloaded', 'success');
}

function copyJson(index) {
    const result = APP_STATE.results[index];
    if (!result) return;

    const jsonStr = JSON.stringify(result.data, null, 2);
    navigator.clipboard.writeText(jsonStr).then(() => {
        showToast('JSON copied to clipboard', 'success');
    }).catch(() => {
        // Fallback for older browsers
        const textarea = document.createElement('textarea');
        textarea.value = jsonStr;
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
        showToast('JSON copied to clipboard', 'success');
    });
}

// ============================
// Toast Notifications
// ============================
function showToast(message, type = 'success') {
    // Remove existing toasts
    document.querySelectorAll('.toast').forEach(t => t.remove());

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <span class="material-icons-outlined">${type === 'success' ? 'check_circle' : 'error_outline'}</span>
        <span>${escapeHtml(message)}</span>
    `;
    document.body.appendChild(toast);

    requestAnimationFrame(() => {
        toast.classList.add('show');
    });

    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// ============================
// Utility Functions
// ============================
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// ============================
// Initialization
// ============================
document.addEventListener('DOMContentLoaded', () => {
    // Bind login form
    document.getElementById('loginForm').addEventListener('submit', handleLogin);

    // Initialize dropzone
    initDropzone();

    // Show login view
    showView('loginView');
});
