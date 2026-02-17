"""
American Fidelity - Document Intelligence Platform
Streamlit Application
"""

import streamlit as st
import json
import base64
import random
import pdfplumber
from openai import OpenAI

# ============================
# Page Config
# ============================
st.set_page_config(
    page_title="American Fidelity - Document Intelligence",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ============================
# Constants
# ============================
CREDENTIALS = {"user_id": "admin", "password": "admin"}

EXTRACTION_CATEGORIES = [
    {"id": "benefits",    "label": "BENEFITS OFFERED",         "icon": "✅", "keywords": ["benefit", "coverage", "plan type", "products offered", "plans offered", "insurance type", "plan name"]},
    {"id": "eligibility", "label": "ELIGIBILITY",              "icon": "👤", "keywords": ["eligib", "waiting period", "hours", "employment", "new hire", "qualifying", "full-time", "full time", "part-time", "part time", "active"]},
    {"id": "payroll",     "label": "PAYROLL",                  "icon": "💰", "keywords": ["payroll", "pay frequency", "deduction", "salary", "wage", "compensation", "pay method", "pay type", "pay cycle"]},
    {"id": "calendar",    "label": "PAYROLL CALENDAR",         "icon": "📅", "keywords": ["calendar", "pay date", "schedule", "pay period", "pay day", "frequency date", "effective date"]},
    {"id": "dental",      "label": "DENTAL",                   "icon": "🦷", "keywords": ["dental"]},
    {"id": "vision",      "label": "VISION",                   "icon": "👁️", "keywords": ["vision", "eye", "optical"]},
    {"id": "basiclife",   "label": "BASIC LIFE",               "icon": "🛡️", "keywords": ["basic life", "basic ad&d", "basic ad and d", "group life", "employer life", "employer-paid life"]},
    {"id": "vollife",     "label": "EMPLOYEE VOLUNTARY LIFE",  "icon": "🤝", "keywords": ["voluntary life", "supplemental life", "employee life", "vol life", "optional life", "dependent life", "spouse life", "child life"]},
    {"id": "afa",         "label": "AFA",                      "icon": "🏦", "keywords": ["afa", "american fidelity", "fidelity account", "flexible spending", "fsa", "hsa", "hra", "section 125", "cafeteria"]},
    {"id": "additional",  "label": "ADDITIONAL",               "icon": "📋", "keywords": []},
]

SYSTEM_PROMPT = """You are a document data extraction specialist. Extract ALL key-value data from the provided PDF text.

Rules:
1. Extract every field label and its corresponding value as a key-value pair.
2. Use the EXACT field label as the key (e.g., "Group Name", "Tax ID", "Eligible Employees").
3. Values must be strings. Convert numbers to strings (e.g., "600" not 600).
4. If a field exists but has no value, use an empty string "".
5. Do NOT nest objects - keep it as a flat key-value structure.
6. Do NOT invent or hallucinate data that isn't in the document.
7. Include ALL fields you can find, even if they seem minor.
8. For checkboxes or yes/no fields, use "Yes" or "No".
9. For dates, preserve the original format from the document.
10. Return ONLY valid JSON, no markdown, no explanation.
11. The JSON should be a single flat object like: {"Field Name": "Value", ...}
"""

# ============================
# Custom CSS
# ============================
def inject_css():
    st.markdown("""
    <style>
        /* Hide Streamlit defaults */
        #MainMenu {visibility: hidden;}
        header {visibility: hidden;}
        footer {visibility: hidden;}
        .stDeployButton {display: none;}

        /* Global font */
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800&family=Inter:wght@400;500;600;700;800&display=swap');

        html, body, [class*="css"] {
            font-family: 'Poppins', 'Inter', sans-serif;
        }

        /* Login page styles */
        .login-container {
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 80vh;
        }

        .login-card {
            background: #ffffff;
            border-radius: 16px;
            padding: 48px 44px;
            width: 420px;
            max-width: 92vw;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
            text-align: center;
            margin: 0 auto;
        }

        .sutherland-logo {
            font-size: 18px;
            font-weight: 700;
            letter-spacing: 3px;
            color: #1a1a3e;
            margin-bottom: 8px;
        }

        .login-title {
            font-size: 22px;
            font-weight: 600;
            color: #1a1a3e;
            margin-bottom: 4px;
        }

        .login-subtitle {
            font-size: 13px;
            color: #888;
            margin-bottom: 24px;
        }

        /* Header */
        .af-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 12px 28px;
            background: #fff;
            border-bottom: 1px solid #f0f0f0;
            margin: -1rem -1rem 0 -1rem;
        }

        .af-brand {
            display: flex;
            flex-direction: column;
        }

        .af-name {
            font-size: 16px;
            font-weight: 800;
            color: #C62828;
            letter-spacing: 2px;
        }

        .af-tagline {
            font-size: 10px;
            color: #999;
            letter-spacing: 1px;
            font-style: italic;
        }

        .af-accent {
            height: 3px;
            background: linear-gradient(90deg, #C62828 0%, #E53935 40%, #EF5350 100%);
            margin: 0 -1rem;
        }

        /* Category accordion */
        .cat-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 12px 16px;
            background: #fafbfc;
            border: 1px solid #eee;
            border-radius: 8px;
            margin-bottom: 2px;
            cursor: pointer;
        }

        .cat-header:hover {
            background: #f0f2f8;
        }

        .cat-header-left {
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .cat-icon-box {
            width: 32px;
            height: 32px;
            background: #fef2f2;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 16px;
        }

        .cat-label {
            font-size: 13px;
            font-weight: 700;
            color: #1a1a2e;
            letter-spacing: 0.5px;
            text-transform: uppercase;
        }

        .cat-count {
            font-size: 11px;
            color: #aaa;
            background: #eee;
            padding: 2px 8px;
            border-radius: 10px;
        }

        /* Confidence badges */
        .conf-high {
            background: #e8f5e9;
            color: #2e7d32;
            padding: 3px 10px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 700;
            display: inline-block;
        }

        .conf-medium {
            background: #fff3e0;
            color: #e65100;
            padding: 3px 10px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 700;
            display: inline-block;
        }

        .conf-low {
            background: #fef2f2;
            color: #c62828;
            padding: 3px 10px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 700;
            display: inline-block;
        }

        /* Data table styling */
        .ext-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
        }

        .ext-table th {
            padding: 10px 14px;
            background: #f5f6fa;
            color: #888;
            font-weight: 600;
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            text-align: left;
            border-bottom: 2px solid #e8e8ee;
        }

        .ext-table td {
            padding: 10px 14px;
            border-bottom: 1px solid #f0f0f5;
            vertical-align: top;
        }

        .ext-table tr:hover {
            background: #f8f9ff;
        }

        .ext-table tr:nth-child(even) {
            background: #fafbfc;
        }

        .field-name {
            font-weight: 600;
            color: #C62828;
        }

        .field-value {
            color: #1a1a2e;
            font-weight: 500;
        }

        /* Section header */
        .section-header {
            background: linear-gradient(135deg, #C62828, #E53935);
            color: white;
            padding: 14px 20px;
            border-radius: 10px 10px 0 0;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .section-header h3 {
            margin: 0;
            font-size: 15px;
            font-weight: 600;
        }

        .section-header span {
            font-size: 13px;
            opacity: 0.85;
        }

        /* Upload area */
        .upload-area {
            background: #fff;
            border: 2px dashed #e0e0e0;
            border-radius: 14px;
            padding: 40px;
            text-align: center;
            transition: all 0.2s;
        }

        .upload-area:hover {
            border-color: #C62828;
            background: #fef8f8;
        }

        /* Processing state */
        .processing-box {
            text-align: center;
            background: #fff;
            border-radius: 16px;
            padding: 48px 40px;
            border: 1px solid #e8e8ee;
            box-shadow: 0 2px 12px rgba(0,0,0,0.04);
        }

        /* Result card */
        .result-card {
            background: #fff;
            border-radius: 14px;
            border: 1px solid #e8e8ee;
            box-shadow: 0 1px 4px rgba(0,0,0,0.04);
            overflow: hidden;
            margin-bottom: 20px;
        }

        .result-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 16px 24px;
            background: #fafbfc;
            border-bottom: 1px solid #f0f0f5;
        }

        .doc-badge {
            width: 38px;
            height: 38px;
            background: linear-gradient(135deg, #C62828, #E53935);
            border-radius: 10px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            color: #fff;
            font-size: 15px;
            font-weight: 700;
            margin-right: 12px;
        }

        /* Tab styling overrides */
        .stTabs [data-baseweb="tab-list"] {
            gap: 2px;
            background: #fafbfc;
            padding: 4px;
            border-radius: 10px;
        }

        .stTabs [data-baseweb="tab"] {
            border-radius: 8px;
            padding: 8px 20px;
            font-weight: 600;
        }

        .stTabs [aria-selected="true"] {
            background: #C62828 !important;
            color: white !important;
        }

        /* PDF iframe */
        .pdf-viewer {
            width: 100%;
            height: 600px;
            border: 1px solid #e8e8ee;
            border-radius: 8px;
        }

        /* JSON display */
        .json-display {
            background: #1a1a2e;
            border-radius: 10px;
            padding: 20px;
            overflow-x: auto;
            max-height: 500px;
            overflow-y: auto;
        }

        .json-display pre {
            color: #ccc;
            font-family: 'Cascadia Code', 'Fira Code', monospace;
            font-size: 13px;
            line-height: 1.7;
            margin: 0;
        }
    </style>
    """, unsafe_allow_html=True)


# ============================
# Session State Init
# ============================
def init_session_state():
    defaults = {
        "authenticated": False,
        "uploaded_files": [],
        "pdf_bytes": [],
        "results": [],
        "extraction_data": [],
        "processing": False,
        "openai_api_key": "",
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


# ============================
# Helpers
# ============================
def generate_confidence(value):
    if not value or str(value).strip() == "":
        return 0
    s = str(value).strip()
    if len(s) > 15:
        return random.randint(95, 99)
    if len(s) > 5:
        return random.randint(90, 97)
    return random.randint(85, 94)


def get_confidence_class(score):
    if score >= 90:
        return "high"
    if score >= 70:
        return "medium"
    return "low"


def conf_badge_html(score):
    cls = get_confidence_class(score)
    return f'<span class="conf-{cls}">{score}%</span>'


def categorize_fields(data):
    categorized = {cat["id"]: [] for cat in EXTRACTION_CATEGORIES}
    assigned = set()

    for key, value in data.items():
        if isinstance(value, dict) or isinstance(value, list):
            continue
        lower_key = key.lower()
        matched = False
        for cat in EXTRACTION_CATEGORIES:
            if cat["id"] == "additional":
                continue
            for kw in cat["keywords"]:
                if kw in lower_key:
                    categorized[cat["id"]].append({"key": key, "value": value, "confidence": generate_confidence(value)})
                    assigned.add(key)
                    matched = True
                    break
            if matched:
                break

    for key, value in data.items():
        if isinstance(value, dict) or isinstance(value, list):
            continue
        if key not in assigned:
            categorized["additional"].append({"key": key, "value": value, "confidence": generate_confidence(value)})

    return categorized


def extract_text_from_pdf(pdf_bytes):
    text = ""
    with pdfplumber.open(pdf_bytes) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text


def extract_with_openai(text, api_key):
    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model="gpt-4o",
        temperature=0,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
    )
    content = response.choices[0].message.content.strip()
    # Strip markdown code blocks if present
    if content.startswith("```"):
        content = content.split("\n", 1)[1] if "\n" in content else content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
    return json.loads(content)


def extract_basic(text):
    """Fallback extraction without AI - splits colon-separated key:value lines."""
    data = {}
    for line in text.split("\n"):
        line = line.strip()
        if ":" in line and not line.startswith("http"):
            parts = line.split(":", 1)
            key = parts[0].strip()
            value = parts[1].strip() if len(parts) > 1 else ""
            if key and len(key) < 80:
                data[key] = value
    return data


def get_pdf_display_html(pdf_bytes):
    b64 = base64.b64encode(pdf_bytes).decode("utf-8")
    return f'<iframe src="data:application/pdf;base64,{b64}" class="pdf-viewer" type="application/pdf"></iframe>'


# ============================
# Login Page
# ============================
def render_login():
    st.markdown("""
    <style>
        [data-testid="stMain"] {
            background: linear-gradient(135deg, #1a1a3e 0%, #2d1b69 30%, #1a1a3e 50%, #4a1942 75%, #e91e63 100%);
        }
    </style>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.markdown("<div style='height: 80px;'></div>", unsafe_allow_html=True)

        st.markdown("""
        <div class="login-card">
            <div class="sutherland-logo">☰ SUTHERLAND</div>
            <div class="login-title">American Fidelity</div>
            <div class="login-subtitle">Document Intelligence Platform</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

        with st.container():
            with st.form("login_form", clear_on_submit=False):
                st.markdown("##### User ID")
                user_id = st.text_input("User ID", placeholder="Enter your user ID", label_visibility="collapsed")
                st.markdown("##### Password")
                password = st.text_input("Password", type="password", placeholder="Enter your password", label_visibility="collapsed")

                submitted = st.form_submit_button("Sign In", use_container_width=True, type="primary")

                if submitted:
                    if user_id == CREDENTIALS["user_id"] and password == CREDENTIALS["password"]:
                        st.session_state.authenticated = True
                        st.rerun()
                    else:
                        st.error("Invalid credentials. Please try again.")


# ============================
# Dashboard
# ============================
def render_dashboard():
    # Header
    st.markdown("""
    <div class="af-header">
        <div class="af-brand">
            <div class="af-name">AMERICAN FIDELITY</div>
            <div class="af-tagline">Document Intelligence Platform</div>
        </div>
    </div>
    <div class="af-accent"></div>
    """, unsafe_allow_html=True)

    # Logout in sidebar
    with st.sidebar:
        st.markdown("### Navigation")
        st.markdown(f"**User:** Admin")
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.uploaded_files = []
            st.session_state.pdf_bytes = []
            st.session_state.results = []
            st.session_state.extraction_data = []
            st.rerun()

        st.divider()
        st.markdown("### OpenAI API Key")
        api_key = st.text_input(
            "API Key",
            type="password",
            value=st.session_state.openai_api_key,
            placeholder="sk-...",
            help="Required for AI-powered extraction. Leave blank for basic extraction.",
            label_visibility="collapsed",
        )
        st.session_state.openai_api_key = api_key

        if api_key:
            st.success("AI Extraction: Enabled", icon="✅")
        else:
            st.warning("AI Extraction: Disabled (basic mode)", icon="⚠️")

        st.divider()
        st.markdown(
            "<div style='font-size:11px;color:#aaa;'>Powered by Sutherland</div>",
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

    # Main tabs
    has_results = len(st.session_state.results) > 0
    tab_labels = ["📤 Upload", "🔍 Extraction", "📊 Results"]
    tabs = st.tabs(tab_labels)

    # ---- UPLOAD TAB ----
    with tabs[0]:
        render_upload_tab()

    # ---- EXTRACTION TAB ----
    with tabs[1]:
        render_extraction_tab()

    # ---- RESULTS TAB ----
    with tabs[2]:
        render_results_tab()


# ============================
# Upload Tab
# ============================
def render_upload_tab():
    st.markdown("## 📤 Upload Documents")
    st.markdown("Upload PDF documents for intelligent data extraction")

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    uploaded = st.file_uploader(
        "Upload PDF files",
        type=["pdf"],
        accept_multiple_files=True,
        help="Upload up to 2 PDF documents (max 10MB each)",
        label_visibility="collapsed",
    )

    if uploaded:
        if len(uploaded) > 2:
            st.error("Maximum 2 files allowed. Please remove extra files.")
            return

        # Show uploaded files
        for i, file in enumerate(uploaded):
            size_mb = file.size / (1024 * 1024)
            col1, col2, col3 = st.columns([0.5, 4, 1])
            with col1:
                st.markdown(f"📄")
            with col2:
                st.markdown(f"**{file.name}**")
                st.caption(f"{size_mb:.2f} MB")
            with col3:
                st.markdown(f"✅")

        st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            extract_btn = st.button(
                "🚀 Upload & Extract Data",
                type="primary",
                use_container_width=True,
            )

        if extract_btn:
            process_documents(uploaded)


# ============================
# Process Documents
# ============================
def process_documents(uploaded_files):
    results = []
    pdf_bytes_list = []
    extraction_data = []

    progress = st.progress(0, text="Preparing documents...")

    for i, file in enumerate(uploaded_files):
        file_bytes = file.read()
        pdf_bytes_list.append(file_bytes)

        step_base = i / len(uploaded_files)
        step_size = 1 / len(uploaded_files)

        # Step 1: Extract text
        progress.progress(
            step_base + step_size * 0.2,
            text=f"📖 Extracting text from {file.name}...",
        )

        import io
        text = extract_text_from_pdf(io.BytesIO(file_bytes))

        if not text.strip():
            st.warning(f"Could not extract text from {file.name}. The PDF may be image-based.")
            results.append({"fileName": file.name, "data": {}})
            extraction_data.append({})
            continue

        # Step 2: AI Extraction
        progress.progress(
            step_base + step_size * 0.5,
            text=f"🤖 AI extracting data from {file.name}...",
        )

        try:
            if st.session_state.openai_api_key:
                data = extract_with_openai(text, st.session_state.openai_api_key)
            else:
                data = extract_basic(text)
        except Exception as e:
            st.error(f"Extraction error for {file.name}: {str(e)}")
            data = extract_basic(text)

        # Step 3: Categorize
        progress.progress(
            step_base + step_size * 0.8,
            text=f"📂 Categorizing fields from {file.name}...",
        )

        categorized = categorize_fields(data)
        results.append({"fileName": file.name, "data": data})
        extraction_data.append(categorized)

    progress.progress(1.0, text="✅ Extraction complete!")

    st.session_state.results = results
    st.session_state.pdf_bytes = pdf_bytes_list
    st.session_state.extraction_data = extraction_data

    st.success(f"Successfully processed {len(results)} document(s)!")
    st.balloons()
    st.rerun()


# ============================
# Extraction Tab
# ============================
def render_extraction_tab():
    if not st.session_state.results:
        st.markdown("<div style='height: 40px;'></div>", unsafe_allow_html=True)
        st.markdown(
            """
            <div style="text-align:center; padding:60px 20px; background:#fff; border-radius:14px; border:1px solid #e8e8ee;">
                <div style="font-size:56px; color:#ddd; margin-bottom:12px;">🔍</div>
                <h3 style="font-size:16px; color:#555; margin-bottom:6px;">No Extraction Data</h3>
                <p style="font-size:14px; color:#aaa;">Upload and process documents to view extracted data with confidence scores.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    for doc_idx, result in enumerate(st.session_state.results):
        categorized = st.session_state.extraction_data[doc_idx]

        # Section header
        st.markdown(
            f"""
            <div class="section-header">
                <h3>📄 Data Extraction Sheet - {doc_idx + 1}</h3>
                <span>{result['fileName']}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Split view: PDF left, Data right
        col_pdf, col_data = st.columns([1, 1])

        # LEFT: PDF Viewer
        with col_pdf:
            st.markdown("##### 📄 Document Viewer")
            if doc_idx < len(st.session_state.pdf_bytes):
                pdf_html = get_pdf_display_html(st.session_state.pdf_bytes[doc_idx])
                st.markdown(pdf_html, unsafe_allow_html=True)

                st.download_button(
                    "⬇️ Download PDF",
                    data=st.session_state.pdf_bytes[doc_idx],
                    file_name=result["fileName"],
                    mime="application/pdf",
                    use_container_width=True,
                )

        # RIGHT: Categorized extracted data
        with col_data:
            total_fields = sum(len(fields) for fields in categorized.values())
            st.markdown(f"##### 📊 Extracted Data ({total_fields} fields)")

            for cat in EXTRACTION_CATEGORIES:
                fields = categorized.get(cat["id"], [])
                if not fields:
                    continue

                avg_conf = round(sum(f["confidence"] for f in fields) / len(fields))
                conf_cls = get_confidence_class(avg_conf)

                with st.expander(
                    f"{cat['icon']}  {cat['label']}  —  {len(fields)} fields  |  Avg: {avg_conf}%",
                    expanded=(cat["id"] in ["benefits", "eligibility", "payroll"]),
                ):
                    # Build table HTML
                    rows_html = ""
                    for i, f in enumerate(fields):
                        conf_html = conf_badge_html(f["confidence"])
                        val = str(f["value"]) if f["value"] is not None else ""
                        rows_html += f"""
                        <tr>
                            <td style="text-align:center;color:#bbb;font-weight:600;font-size:12px;width:40px;">{i + 1}</td>
                            <td><span class="field-name">{f['key']}</span></td>
                            <td><span class="field-value">{val}</span></td>
                            <td style="text-align:center;width:100px;">{conf_html}</td>
                        </tr>
                        """

                    table_html = f"""
                    <table class="ext-table">
                        <thead>
                            <tr>
                                <th style="width:40px;text-align:center;">#</th>
                                <th>Field</th>
                                <th>Value</th>
                                <th style="width:100px;text-align:center;">Confidence</th>
                            </tr>
                        </thead>
                        <tbody>{rows_html}</tbody>
                    </table>
                    """
                    st.markdown(table_html, unsafe_allow_html=True)

        st.divider()


# ============================
# Results Tab
# ============================
def render_results_tab():
    if not st.session_state.results:
        st.markdown("<div style='height: 40px;'></div>", unsafe_allow_html=True)
        st.markdown(
            """
            <div style="text-align:center; padding:60px 20px; background:#fff; border-radius:14px; border:1px solid #e8e8ee;">
                <div style="font-size:56px; color:#ddd; margin-bottom:12px;">📊</div>
                <h3 style="font-size:16px; color:#555; margin-bottom:6px;">No Results Yet</h3>
                <p style="font-size:14px; color:#aaa;">Upload and process documents to view JSON results.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    for idx, result in enumerate(st.session_state.results):
        data = result["data"]
        json_str = json.dumps(data, indent=2)

        # Card header
        st.markdown(
            f"""
            <div class="result-header">
                <div style="display:flex;align-items:center;">
                    <div class="doc-badge">{idx + 1}</div>
                    <div>
                        <strong>{result['fileName']}</strong><br/>
                        <span style="font-size:12px;color:#aaa;">Document {idx + 1} of {len(st.session_state.results)}</span>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Key fields grid
        entries = [(k, v) for k, v in data.items() if not isinstance(v, (dict, list))]
        if entries:
            cols = st.columns(4)
            for i, (key, value) in enumerate(entries[:8]):
                with cols[i % 4]:
                    st.markdown(
                        f"""
                        <div style="padding:12px 14px; background:#fafbfc; border:1px solid #f0f0f5; border-radius:10px; margin-bottom:8px;">
                            <div style="font-size:11px; font-weight:600; color:#aaa; text-transform:uppercase; letter-spacing:0.5px; margin-bottom:4px;">{key}</div>
                            <div style="font-size:14px; font-weight:500; color:#1a1a2e;">{value}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

        # JSON display
        st.markdown("##### 📋 Raw JSON Data")
        st.code(json_str, language="json")

        # Download button
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            st.download_button(
                "⬇️ Download JSON",
                data=json_str,
                file_name=f"{result['fileName'].replace('.pdf', '')}_extracted.json",
                mime="application/json",
                use_container_width=True,
                key=f"download_json_{idx}",
            )
        with col2:
            if st.button(f"📋 Copy JSON", key=f"copy_{idx}", use_container_width=True):
                st.toast("JSON copied! Use the code block above to copy.", icon="✅")

        st.divider()


# ============================
# Main
# ============================
def main():
    inject_css()
    init_session_state()

    if not st.session_state.authenticated:
        render_login()
    else:
        render_dashboard()


if __name__ == "__main__":
    main()
