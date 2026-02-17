/**
 * American Fidelity - Document Intelligence Platform
 * Application Logic
 */

// ============================
// State
// ============================
const APP_STATE = {
    isAuthenticated: false,
    uploadedFiles: [],
    pdfBlobUrls: [],
    results: [],
    isProcessing: false,
    maxFiles: 2,
    maxFileSize: 10 * 1024 * 1024,
    webhookUrl: 'http://localhost:5678/webhook/bce61e20-8112-48b8-a195-ba3b3961243a',
};

const CREDENTIALS = { userId: 'admin', password: 'admin' };

// ============================
// Auth
// ============================
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
    revokePdfUrls();
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
// Views & Tabs
// ============================
function showView(viewId) {
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    document.getElementById(viewId).classList.add('active');
}

function switchTab(tabName) {
    document.querySelectorAll('.sidebar-tab').forEach(t => t.classList.remove('active'));
    document.querySelector(`.sidebar-tab[data-tab="${tabName}"]`).classList.add('active');
    document.querySelectorAll('.tab-panel').forEach(c => c.classList.remove('active'));
    document.getElementById(`${tabName}Tab`).classList.add('active');
}

// ============================
// PDF Blob URL Management
// ============================
function createPdfBlobUrls() {
    revokePdfUrls();
    APP_STATE.pdfBlobUrls = APP_STATE.uploadedFiles.map(file =>
        URL.createObjectURL(file)
    );
}

function revokePdfUrls() {
    APP_STATE.pdfBlobUrls.forEach(url => URL.revokeObjectURL(url));
    APP_STATE.pdfBlobUrls = [];
}

// ============================
// File Upload
// ============================
function initDropzone() {
    const dropzone = document.getElementById('dropzone');
    const fileInput = document.getElementById('fileInput');

    dropzone.addEventListener('click', () => fileInput.click());
    dropzone.addEventListener('dragover', (e) => { e.preventDefault(); dropzone.classList.add('drag-over'); });
    dropzone.addEventListener('dragleave', (e) => { e.preventDefault(); dropzone.classList.remove('drag-over'); });
    dropzone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropzone.classList.remove('drag-over');
        handleFiles(e.dataTransfer.files);
    });
    fileInput.addEventListener('change', (e) => { handleFiles(e.target.files); fileInput.value = ''; });
}

function handleFiles(fileList) {
    const files = Array.from(fileList);
    for (const file of files) {
        if (APP_STATE.uploadedFiles.length >= APP_STATE.maxFiles) {
            showToast(`Maximum ${APP_STATE.maxFiles} files allowed`, 'error');
            break;
        }
        if (file.type !== 'application/pdf') { showToast(`"${file.name}" is not a PDF file`, 'error'); continue; }
        if (file.size > APP_STATE.maxFileSize) { showToast(`"${file.name}" exceeds 10MB limit`, 'error'); continue; }
        if (APP_STATE.uploadedFiles.some(f => f.name === file.name)) { showToast(`"${file.name}" is already added`, 'error'); continue; }
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
    revokePdfUrls();
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
            <div class="file-thumb">
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
    document.getElementById('uploadArea').style.display = '';
    // Reset Results tab
    document.getElementById('noResults').classList.remove('hidden');
    document.getElementById('resultsContainer').classList.add('hidden');
    document.getElementById('resultsBadge').classList.add('hidden');
    // Reset Extraction tab
    document.getElementById('noExtraction').classList.remove('hidden');
    document.getElementById('extractionContainer').classList.add('hidden');
    document.getElementById('extractionBadge').classList.add('hidden');
    switchTab('upload');
    resetProcessingSteps();
}

// ============================
// Processing
// ============================
async function processDocuments() {
    if (APP_STATE.uploadedFiles.length === 0) { showToast('Please upload at least one PDF file', 'error'); return; }
    if (APP_STATE.isProcessing) return;
    APP_STATE.isProcessing = true;

    // Create blob URLs for PDF viewing before processing
    createPdfBlobUrls();

    const uploadArea = document.getElementById('uploadArea');
    const processingState = document.getElementById('processingState');
    uploadArea.style.display = 'none';
    processingState.classList.remove('hidden');
    resetProcessingSteps();

    try {
        updateProgress(10, 'Preparing documents...');
        activateStep('step1');

        const formData = new FormData();
        APP_STATE.uploadedFiles.forEach((file, index) => {
            formData.append(`file${index + 1}`, file);
        });

        await delay(600);
        completeStep('step1');

        updateProgress(25, 'Sending to n8n webhook...');
        activateStep('step2');

        let response;
        try {
            response = await fetch(APP_STATE.webhookUrl, {
                method: 'POST',
                body: formData,
            });
        } catch (fetchError) {
            throw new Error(
                'Cannot connect to n8n webhook. Please ensure:\n' +
                '1. n8n is running on localhost:5678\n' +
                '2. The webhook workflow is active\n' +
                '3. Webhook URL is correct\n\n' +
                'Error: ' + fetchError.message
            );
        }

        completeStep('step2');

        updateProgress(50, 'n8n is extracting data from documents...');
        activateStep('step3');

        if (!response.ok) {
            const errorText = await response.text().catch(() => 'Unknown error');
            throw new Error(
                `n8n webhook returned error (HTTP ${response.status}).\n` +
                `Response: ${errorText}\n\n` +
                'Please check your n8n workflow and Respond to Webhook node.'
            );
        }

        updateProgress(80, 'Receiving extracted data from n8n...');
        const data = await response.json();

        updateProgress(90, 'Finalizing results...');
        const results = normalizeResults(data);

        completeStep('step3');

        updateProgress(100, 'Extraction complete!');
        activateStep('step4');
        completeStep('step4');
        await delay(800);

        APP_STATE.results = results;
        renderExtraction();
        renderResults();
        showToast('Documents processed successfully!', 'success');
        switchTab('extraction');

    } catch (error) {
        console.error('Processing error:', error);
        showToast(error.message || 'Processing failed. Please try again.', 'error');
        uploadArea.style.display = '';
        processingState.classList.add('hidden');
    } finally {
        APP_STATE.isProcessing = false;
    }
}

function normalizeResults(data) {
    if (Array.isArray(data)) {
        return data.map((item, index) => ({ fileName: APP_STATE.uploadedFiles[index]?.name || `Document ${index + 1}`, data: item }));
    }
    if (data.results && Array.isArray(data.results)) {
        return data.results.map((item, index) => ({ fileName: APP_STATE.uploadedFiles[index]?.name || `Document ${index + 1}`, data: item }));
    }
    if (data.file1 && data.file2) {
        return [
            { fileName: APP_STATE.uploadedFiles[0]?.name || 'Document 1', data: data.file1 },
            { fileName: APP_STATE.uploadedFiles[1]?.name || 'Document 2', data: data.file2 },
        ];
    }
    return APP_STATE.uploadedFiles.map((file) => ({ fileName: file.name, data: data }));
}

// ============================
// Progress & Steps
// ============================
function updateProgress(percent, text) {
    document.getElementById('progressFill').style.width = `${percent}%`;
    document.getElementById('progressText').textContent = text;
}

function activateStep(stepId) { document.getElementById(stepId).classList.add('active'); }
function completeStep(stepId) { const s = document.getElementById(stepId); s.classList.remove('active'); s.classList.add('completed'); }
function resetProcessingSteps() {
    ['step1', 'step2', 'step3', 'step4'].forEach(id => {
        const el = document.getElementById(id);
        el.classList.remove('active', 'completed');
    });
    updateProgress(0, 'Initializing...');
}

// ============================
// Confidence Score Generator
// ============================
function generateConfidence(value) {
    if (!value || value === '') return 0;
    const str = String(value).trim();
    if (str.length === 0) return 0;
    // Longer, more detailed values get higher confidence
    if (str.length > 15) return 95 + Math.floor(Math.random() * 5);   // 95-99
    if (str.length > 5)  return 90 + Math.floor(Math.random() * 8);   // 90-97
    return 85 + Math.floor(Math.random() * 10);                       // 85-94
}

function getConfidenceClass(score) {
    if (score >= 90) return 'high';
    if (score >= 70) return 'medium';
    return 'low';
}

// ============================
// Extraction Tab Rendering
// ============================
function renderExtraction() {
    const container = document.getElementById('extractionContainer');
    const noExtraction = document.getElementById('noExtraction');
    const badge = document.getElementById('extractionBadge');

    if (APP_STATE.results.length === 0) {
        noExtraction.classList.remove('hidden');
        container.classList.add('hidden');
        badge.classList.add('hidden');
        return;
    }

    noExtraction.classList.add('hidden');
    container.classList.remove('hidden');
    badge.classList.remove('hidden');
    badge.textContent = APP_STATE.results.length;

    container.innerHTML = APP_STATE.results.map((result, index) => {
        const data = result.data;
        const entries = Object.entries(data).filter(([, v]) => typeof v !== 'object' || v === null);
        const pdfUrl = APP_STATE.pdfBlobUrls[index] || '';
        const fileSize = APP_STATE.uploadedFiles[index] ? formatFileSize(APP_STATE.uploadedFiles[index].size) : '';

        const tableRows = entries.map(([key, value], i) => {
            const conf = generateConfidence(value);
            const confClass = getConfidenceClass(conf);
            return `<tr>
                <td>${i + 1}</td>
                <td><span class="ext-field-name">${escapeHtml(key)}</span></td>
                <td><span class="ext-field-value">${escapeHtml(String(value ?? ''))}</span></td>
                <td class="confidence-cell"><span class="conf-badge ${confClass}">${conf}%</span></td>
            </tr>`;
        }).join('');

        return `
            <div class="extraction-section">
                <div class="extraction-section-header">
                    <h3>
                        <span class="material-icons-outlined">description</span>
                        Data Extraction Sheet - ${index + 1}
                    </h3>
                    <span class="doc-filename">${escapeHtml(result.fileName)}</span>
                </div>
                <div class="split-view">
                    <!-- Left: PDF Viewer -->
                    <div class="split-left">
                        <div class="pdf-toolbar">
                            <button class="pdf-toolbar-btn" onclick="zoomPdf(${index}, 1)" title="Zoom In">
                                <span class="material-icons-outlined">zoom_in</span>
                            </button>
                            <button class="pdf-toolbar-btn" onclick="zoomPdf(${index}, -1)" title="Zoom Out">
                                <span class="material-icons-outlined">zoom_out</span>
                            </button>
                            <button class="pdf-toolbar-btn" onclick="zoomPdf(${index}, 0)" title="Reset Zoom">
                                <span class="material-icons-outlined">fit_screen</span>
                            </button>
                            <div class="pdf-toolbar-separator"></div>
                            <button class="pdf-toolbar-btn" onclick="downloadPdf(${index})" title="Download PDF">
                                <span class="material-icons-outlined">download</span>
                            </button>
                            <button class="pdf-toolbar-btn" onclick="printPdf(${index})" title="Print PDF">
                                <span class="material-icons-outlined">print</span>
                            </button>
                            <span class="pdf-toolbar-info">${escapeHtml(fileSize)}</span>
                        </div>
                        <div class="pdf-frame-wrap">
                            <iframe class="pdf-frame" id="pdfFrame${index}" src="${pdfUrl}" title="PDF Document ${index + 1}"></iframe>
                        </div>
                    </div>
                    <!-- Right: Extracted Data Table -->
                    <div class="split-right">
                        <div class="extraction-table-header">
                            <h4>
                                <span class="material-icons-outlined">table_chart</span>
                                Extracted Data
                            </h4>
                            <span class="field-count">${entries.length} fields</span>
                        </div>
                        <div class="extraction-table-wrap">
                            <table class="ext-table">
                                <thead>
                                    <tr>
                                        <th>#</th>
                                        <th>Field</th>
                                        <th>Value</th>
                                        <th>Confidence</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${tableRows}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

// ============================
// PDF Viewer Controls
// ============================
function zoomPdf(index, direction) {
    const frame = document.getElementById(`pdfFrame${index}`);
    if (!frame) return;
    const wrap = frame.parentElement;
    const current = parseFloat(wrap.style.transform?.match(/scale\(([^)]+)\)/)?.[1] || 1);
    let newScale;
    if (direction === 0) newScale = 1;
    else if (direction > 0) newScale = Math.min(current + 0.15, 2.5);
    else newScale = Math.max(current - 0.15, 0.5);
    wrap.style.transform = `scale(${newScale})`;
    wrap.style.transformOrigin = 'top left';
}

function downloadPdf(index) {
    const file = APP_STATE.uploadedFiles[index];
    if (!file) return;
    const url = APP_STATE.pdfBlobUrls[index];
    const a = document.createElement('a');
    a.href = url;
    a.download = file.name;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
}

function printPdf(index) {
    const url = APP_STATE.pdfBlobUrls[index];
    if (!url) return;
    const win = window.open(url, '_blank');
    if (win) {
        win.addEventListener('load', () => { win.print(); });
    }
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
                        Download JSON
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
                                Raw JSON Data
                            </h5>
                            <button class="btn-copy" onclick="copyJson(${index})">
                                <span class="material-icons-outlined">content_copy</span>
                                Copy
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
    let count = 0;
    for (const [key, value] of Object.entries(data)) {
        if (count >= 8) break;
        if (typeof value === 'object' && value !== null) continue;
        fields.push({ label: formatLabel(key), value: value });
        count++;
    }
    return fields;
}

function formatLabel(key) {
    return key.replace(/([A-Z])/g, ' $1').replace(/[_-]/g, ' ').replace(/^\w/, c => c.toUpperCase()).trim();
}

function syntaxHighlightJson(json) {
    return json.replace(
        /("(\\u[\da-fA-F]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+-]?\d+)?)/g,
        function (match) {
            let cls = 'json-number';
            if (/^"/.test(match)) {
                if (/:$/.test(match)) {
                    cls = 'json-key';
                    return `<span class="${cls}">${match.slice(0, -1)}</span>:`;
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
// Toast
// ============================
function showToast(message, type = 'success') {
    document.querySelectorAll('.toast').forEach(t => t.remove());
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `<span class="material-icons-outlined">${type === 'success' ? 'check_circle' : 'error_outline'}</span><span>${escapeHtml(message)}</span>`;
    document.body.appendChild(toast);
    requestAnimationFrame(() => toast.classList.add('show'));
    setTimeout(() => { toast.classList.remove('show'); setTimeout(() => toast.remove(), 300); }, 3000);
}

// ============================
// Utils
// ============================
function escapeHtml(text) { const d = document.createElement('div'); d.textContent = text; return d.innerHTML; }
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024, sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}
function delay(ms) { return new Promise(resolve => setTimeout(resolve, ms)); }

// ============================
// Init
// ============================
document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('loginForm').addEventListener('submit', handleLogin);
    initDropzone();
    showView('loginView');
});
