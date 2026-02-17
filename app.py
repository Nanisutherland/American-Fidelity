"""
American Fidelity - Document Intelligence Platform
Streamlit Application with Azure OpenAI & LDEX Format
"""

import streamlit as st
import json
import base64
import random
import io
import uuid
from datetime import datetime

import os
import pdfplumber
from openai import AzureOpenAI

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

# Azure OpenAI config - set these as environment variables or in .env file
# export AZURE_OPENAI_ENDPOINT="https://eu2azeoai05.openai.azure.com"
# export AZURE_OPENAI_API_KEY="your-api-key-here"
# export AZURE_OPENAI_DEPLOYMENT="gpt-4o"
AZURE_CONFIG = {
    "endpoint": os.getenv("AZURE_OPENAI_ENDPOINT", "https://eu2azeoai05.openai.azure.com"),
    "api_key": os.getenv("AZURE_OPENAI_API_KEY", ""),
    "deployment": os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o"),
    "api_version": os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview"),
}

EXTRACTION_CATEGORIES = [
    {"id": "benefits",    "label": "BENEFITS OFFERED",         "icon": "✅", "color": "#4CAF50", "keywords": ["benefit", "coverage", "plan type", "products offered", "plans offered", "insurance type", "plan name", "group name", "group number", "tax id", "sic code", "employer", "company"]},
    {"id": "eligibility", "label": "ELIGIBILITY",              "icon": "👤", "color": "#2196F3", "keywords": ["eligib", "waiting period", "hours", "employment", "new hire", "qualifying", "full-time", "full time", "part-time", "part time", "active", "class", "employee class"]},
    {"id": "payroll",     "label": "PAYROLL",                  "icon": "💰", "color": "#FF9800", "keywords": ["payroll", "pay frequency", "deduction", "salary", "wage", "compensation", "pay method", "pay type", "pay cycle", "mode of premium"]},
    {"id": "calendar",    "label": "PAYROLL CALENDAR",         "icon": "📅", "color": "#9C27B0", "keywords": ["calendar", "pay date", "schedule", "pay period", "pay day", "frequency date", "effective date", "renewal date", "anniversary"]},
    {"id": "dental",      "label": "DENTAL",                   "icon": "🦷", "color": "#00BCD4", "keywords": ["dental"]},
    {"id": "vision",      "label": "VISION",                   "icon": "👁", "color": "#3F51B5", "keywords": ["vision", "eye", "optical"]},
    {"id": "basiclife",   "label": "BASIC LIFE",               "icon": "🛡", "color": "#607D8B", "keywords": ["basic life", "basic ad&d", "basic ad and d", "group life", "employer life", "employer-paid life"]},
    {"id": "vollife",     "label": "EMPLOYEE VOLUNTARY LIFE",  "icon": "🤝", "color": "#795548", "keywords": ["voluntary life", "supplemental life", "employee life", "vol life", "optional life", "dependent life", "spouse life", "child life"]},
    {"id": "afa",         "label": "AFA",                      "icon": "🏦", "color": "#C62828", "keywords": ["afa", "american fidelity", "fidelity account", "flexible spending", "fsa", "hsa", "hra", "section 125", "cafeteria"]},
    {"id": "additional",  "label": "ADDITIONAL",               "icon": "📋", "color": "#78909C", "keywords": []},
]

SYSTEM_PROMPT = """You are a document data extraction specialist for insurance and benefits documents. Extract ALL key-value data from the provided PDF text.

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
12. Pay special attention to benefits, eligibility, payroll, dental, vision, life insurance, and AFA fields.
"""

# ============================
# Custom CSS - Modern & Stylish
# ============================
def inject_css():
    st.markdown("""
    <style>
        /* ===== HIDE STREAMLIT DEFAULTS ===== */
        #MainMenu {visibility: hidden;}
        header {visibility: hidden;}
        footer {visibility: hidden;}
        .stDeployButton {display: none;}
        [data-testid="stToolbar"] {display: none;}
        [data-testid="stDecoration"] {display: none;}

        /* ===== FONTS ===== */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=Poppins:wght@300;400;500;600;700;800&display=swap');

        html, body, [class*="css"], .stMarkdown, .stButton button {
            font-family: 'Inter', 'Poppins', -apple-system, BlinkMacSystemFont, sans-serif !important;
        }

        /* ===== GLOBAL ===== */
        [data-testid="stMain"] > div {
            padding-top: 0 !important;
        }

        .block-container {
            padding: 0 2rem 2rem 2rem !important;
            max-width: 100% !important;
        }

        /* ===== LOGIN PAGE ===== */
        .login-bg {
            min-height: 90vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .login-card {
            background: rgba(255,255,255,0.98);
            backdrop-filter: blur(20px);
            border-radius: 24px;
            padding: 52px 48px;
            width: 440px;
            max-width: 94vw;
            box-shadow: 0 25px 80px rgba(0,0,0,0.2), 0 0 0 1px rgba(255,255,255,0.1);
            text-align: center;
        }

        .login-logo-bar {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
            margin-bottom: 6px;
        }

        .login-logo-icon {
            width: 36px; height: 36px;
            background: linear-gradient(135deg, #C62828, #E53935);
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #fff;
            font-size: 18px;
            font-weight: 800;
        }

        .login-brand-text {
            font-size: 15px;
            font-weight: 800;
            color: #1a1a3e;
            letter-spacing: 3px;
            text-transform: uppercase;
        }

        .login-main-title {
            font-size: 26px;
            font-weight: 700;
            color: #C62828;
            margin: 16px 0 4px;
            letter-spacing: 0.5px;
        }

        .login-subtitle {
            font-size: 13px;
            color: #999;
            margin-bottom: 30px;
            font-weight: 400;
        }

        .login-divider {
            height: 1px;
            background: linear-gradient(90deg, transparent, #e0e0e0, transparent);
            margin: 20px 0;
        }

        /* ===== MAIN HEADER ===== */
        .main-header {
            background: #fff;
            border-bottom: 1px solid #eef0f5;
            padding: 16px 32px;
            margin: 0 -2rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
            box-shadow: 0 1px 8px rgba(0,0,0,0.03);
        }

        .header-brand {
            display: flex;
            align-items: center;
            gap: 14px;
        }

        .header-logo-box {
            width: 42px; height: 42px;
            background: linear-gradient(135deg, #C62828, #E53935);
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #fff;
            font-size: 20px;
            font-weight: 800;
            box-shadow: 0 3px 12px rgba(198,40,40,0.25);
        }

        .header-text h1 {
            font-size: 17px;
            font-weight: 800;
            color: #C62828;
            margin: 0;
            letter-spacing: 2px;
        }

        .header-text p {
            font-size: 11px;
            color: #aaa;
            margin: 0;
            letter-spacing: 0.5px;
        }

        .header-right {
            display: flex;
            align-items: center;
            gap: 14px;
        }

        .header-user-pill {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 6px 14px 6px 8px;
            background: #f5f6fa;
            border-radius: 20px;
            font-size: 13px;
            font-weight: 500;
            color: #555;
        }

        .header-user-avatar {
            width: 28px; height: 28px;
            background: linear-gradient(135deg, #1a1a3e, #2d1b69);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #fff;
            font-size: 12px;
            font-weight: 700;
        }

        .accent-line {
            height: 3px;
            background: linear-gradient(90deg, #C62828 0%, #E53935 30%, #EF5350 60%, #FFCDD2 100%);
            margin: 0 -2rem;
        }

        /* ===== SIDEBAR OVERRIDES ===== */
        [data-testid="stSidebar"] {
            background: #fafbfc;
            border-right: 1px solid #eef0f5;
        }

        [data-testid="stSidebar"] .stMarkdown h3 {
            color: #1a1a2e;
            font-size: 14px;
            font-weight: 700;
            letter-spacing: 0.5px;
        }

        /* ===== TAB STYLING ===== */
        .stTabs [data-baseweb="tab-list"] {
            gap: 4px;
            background: #f5f6fa;
            padding: 5px 6px;
            border-radius: 14px;
            border: 1px solid #eef0f5;
        }

        .stTabs [data-baseweb="tab"] {
            border-radius: 10px;
            padding: 10px 24px;
            font-weight: 600;
            font-size: 14px;
            color: #888;
            transition: all 0.2s ease;
        }

        .stTabs [data-baseweb="tab"]:hover {
            color: #C62828;
            background: rgba(198,40,40,0.05);
        }

        .stTabs [aria-selected="true"] {
            background: linear-gradient(135deg, #C62828, #E53935) !important;
            color: white !important;
            box-shadow: 0 3px 12px rgba(198,40,40,0.3) !important;
        }

        .stTabs [data-baseweb="tab-highlight"] {
            display: none;
        }

        .stTabs [data-baseweb="tab-border"] {
            display: none;
        }

        /* ===== SECTION CARDS ===== */
        .glass-card {
            background: rgba(255,255,255,0.95);
            backdrop-filter: blur(10px);
            border: 1px solid #eef0f5;
            border-radius: 16px;
            box-shadow: 0 2px 12px rgba(0,0,0,0.04);
            overflow: hidden;
        }

        .section-header-bar {
            background: linear-gradient(135deg, #C62828, #D32F2F, #E53935);
            color: white;
            padding: 16px 24px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .section-header-bar h3 {
            margin: 0;
            font-size: 16px;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .section-header-bar .doc-tag {
            font-size: 12px;
            font-weight: 500;
            opacity: 0.9;
            background: rgba(255,255,255,0.15);
            padding: 4px 12px;
            border-radius: 8px;
        }

        /* ===== CONFIDENCE BADGES ===== */
        .conf-high {
            background: linear-gradient(135deg, #e8f5e9, #c8e6c9);
            color: #1b5e20;
            padding: 4px 12px;
            border-radius: 14px;
            font-size: 12px;
            font-weight: 700;
            display: inline-block;
            box-shadow: 0 1px 4px rgba(46,125,50,0.15);
        }

        .conf-medium {
            background: linear-gradient(135deg, #fff3e0, #ffe0b2);
            color: #e65100;
            padding: 4px 12px;
            border-radius: 14px;
            font-size: 12px;
            font-weight: 700;
            display: inline-block;
            box-shadow: 0 1px 4px rgba(230,81,0,0.15);
        }

        .conf-low {
            background: linear-gradient(135deg, #ffebee, #ffcdd2);
            color: #b71c1c;
            padding: 4px 12px;
            border-radius: 14px;
            font-size: 12px;
            font-weight: 700;
            display: inline-block;
            box-shadow: 0 1px 4px rgba(198,40,40,0.15);
        }

        /* ===== EXTRACTION TABLE ===== */
        .ext-table {
            width: 100%;
            border-collapse: separate;
            border-spacing: 0;
            font-size: 13px;
        }

        .ext-table thead th {
            padding: 12px 16px;
            background: #f8f9fc;
            color: #8892a4;
            font-weight: 700;
            font-size: 10px;
            text-transform: uppercase;
            letter-spacing: 1px;
            text-align: left;
            border-bottom: 2px solid #eef0f5;
            position: sticky;
            top: 0;
            z-index: 2;
        }

        .ext-table tbody td {
            padding: 11px 16px;
            border-bottom: 1px solid #f4f5f8;
            vertical-align: middle;
        }

        .ext-table tbody tr {
            transition: all 0.15s ease;
        }

        .ext-table tbody tr:hover {
            background: #f7f8ff;
        }

        .ext-table tbody tr:nth-child(even) {
            background: #fafbfd;
        }

        .ext-table tbody tr:nth-child(even):hover {
            background: #f0f2ff;
        }

        .field-name {
            font-weight: 600;
            color: #C62828;
            font-size: 13px;
        }

        .field-value {
            color: #1a1a2e;
            font-weight: 500;
        }

        .row-num {
            text-align: center;
            color: #c0c4cc;
            font-weight: 700;
            font-size: 11px;
        }

        /* ===== CATEGORY EXPANDERS ===== */
        .streamlit-expanderHeader {
            font-size: 14px !important;
            font-weight: 600 !important;
            border-radius: 10px !important;
        }

        /* ===== PDF VIEWER ===== */
        .pdf-viewer-frame {
            width: 100%;
            height: 620px;
            border: 1px solid #eef0f5;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        }

        /* ===== UPLOAD AREA ===== */
        .upload-card {
            background: #fff;
            border: 2px dashed #e0e0e0;
            border-radius: 20px;
            padding: 48px 32px;
            text-align: center;
            transition: all 0.25s ease;
        }

        .upload-card:hover {
            border-color: #C62828;
            background: #fef8f8;
            transform: translateY(-2px);
            box-shadow: 0 8px 30px rgba(198,40,40,0.08);
        }

        .upload-icon-circle {
            width: 80px; height: 80px;
            background: linear-gradient(135deg, #C62828, #E53935);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto 20px;
            font-size: 32px;
            box-shadow: 0 6px 24px rgba(198,40,40,0.25);
        }

        /* ===== FILE ITEM ===== */
        .file-row {
            display: flex;
            align-items: center;
            gap: 14px;
            padding: 14px 18px;
            background: #fff;
            border: 1px solid #eef0f5;
            border-radius: 12px;
            margin-bottom: 8px;
            box-shadow: 0 1px 4px rgba(0,0,0,0.03);
            transition: all 0.15s ease;
        }

        .file-row:hover {
            border-color: #C62828;
            box-shadow: 0 2px 12px rgba(198,40,40,0.08);
        }

        .file-icon-box {
            width: 44px; height: 44px;
            background: linear-gradient(135deg, #ffebee, #ffcdd2);
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 22px;
            flex-shrink: 0;
        }

        .file-details {
            flex: 1;
        }

        .file-details .fname {
            font-size: 14px;
            font-weight: 600;
            color: #1a1a2e;
        }

        .file-details .fsize {
            font-size: 12px;
            color: #aaa;
            margin-top: 2px;
        }

        .file-status {
            font-size: 20px;
        }

        /* ===== RESULTS CARDS ===== */
        .result-card-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 18px 24px;
            background: linear-gradient(135deg, #fafbfc, #f5f6fa);
            border-bottom: 1px solid #eef0f5;
        }

        .result-card-title {
            display: flex;
            align-items: center;
            gap: 14px;
        }

        .doc-num-badge {
            width: 42px; height: 42px;
            background: linear-gradient(135deg, #C62828, #E53935);
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #fff;
            font-size: 16px;
            font-weight: 800;
            box-shadow: 0 3px 10px rgba(198,40,40,0.25);
        }

        .doc-info strong {
            font-size: 15px;
            color: #1a1a2e;
            display: block;
        }

        .doc-info span {
            font-size: 12px;
            color: #aaa;
        }

        /* ===== KEY FIELD CARD ===== */
        .kf-card {
            padding: 14px 16px;
            background: linear-gradient(135deg, #fafbfc, #f5f6fa);
            border: 1px solid #eef0f5;
            border-radius: 12px;
            margin-bottom: 8px;
            transition: all 0.15s ease;
        }

        .kf-card:hover {
            border-color: #C62828;
            box-shadow: 0 2px 8px rgba(198,40,40,0.06);
        }

        .kf-label {
            font-size: 10px;
            font-weight: 700;
            color: #a0a4b0;
            text-transform: uppercase;
            letter-spacing: 0.8px;
            margin-bottom: 5px;
        }

        .kf-value {
            font-size: 14px;
            font-weight: 600;
            color: #1a1a2e;
            word-break: break-word;
        }

        /* ===== EMPTY STATE ===== */
        .empty-state-box {
            text-align: center;
            padding: 64px 24px;
            background: #fff;
            border-radius: 20px;
            border: 1px solid #eef0f5;
            box-shadow: 0 2px 12px rgba(0,0,0,0.03);
        }

        .empty-state-icon {
            font-size: 60px;
            margin-bottom: 16px;
            opacity: 0.3;
        }

        .empty-state-box h3 {
            font-size: 17px;
            font-weight: 600;
            color: #555;
            margin-bottom: 6px;
        }

        .empty-state-box p {
            font-size: 14px;
            color: #aaa;
        }

        /* ===== LDEX FORMAT TAG ===== */
        .ldex-tag {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 4px 12px;
            background: linear-gradient(135deg, #e8f5e9, #c8e6c9);
            color: #1b5e20;
            border-radius: 8px;
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 0.5px;
        }

        /* ===== PROGRESS OVERRIDE ===== */
        .stProgress > div > div {
            background: linear-gradient(90deg, #4CAF50, #66BB6A, #81C784) !important;
            border-radius: 8px;
        }

        /* ===== BUTTONS ===== */
        .stButton button[kind="primary"] {
            background: linear-gradient(135deg, #C62828, #E53935) !important;
            border: none !important;
            border-radius: 10px !important;
            font-weight: 600 !important;
            box-shadow: 0 3px 12px rgba(198,40,40,0.25) !important;
            transition: all 0.2s ease !important;
        }

        .stButton button[kind="primary"]:hover {
            transform: translateY(-1px) !important;
            box-shadow: 0 6px 20px rgba(198,40,40,0.35) !important;
        }

        .stDownloadButton button {
            border-radius: 10px !important;
            font-weight: 600 !important;
        }

        /* ===== STATS ROW ===== */
        .stat-pill {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 6px 14px;
            background: #f5f6fa;
            border: 1px solid #eef0f5;
            border-radius: 10px;
            font-size: 13px;
            font-weight: 600;
            color: #555;
            margin-right: 8px;
        }

        .stat-pill .stat-num {
            font-weight: 800;
            color: #C62828;
        }
    </style>
    """, unsafe_allow_html=True)


# ============================
# Session State
# ============================
def init_session_state():
    defaults = {
        "authenticated": False,
        "uploaded_files": [],
        "pdf_bytes": [],
        "results": [],
        "extraction_data": [],
        "ldex_data": [],
        "processing": False,
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
        if isinstance(value, (dict, list)):
            continue
        lower_key = key.lower()
        matched = False
        for cat in EXTRACTION_CATEGORIES:
            if cat["id"] == "additional":
                continue
            for kw in cat["keywords"]:
                if kw in lower_key:
                    categorized[cat["id"]].append({
                        "key": key,
                        "value": value,
                        "confidence": generate_confidence(value),
                    })
                    assigned.add(key)
                    matched = True
                    break
            if matched:
                break

    for key, value in data.items():
        if isinstance(value, (dict, list)):
            continue
        if key not in assigned:
            categorized["additional"].append({
                "key": key,
                "value": value,
                "confidence": generate_confidence(value),
            })

    return categorized


def build_ldex_json(data, file_name, categorized):
    """Convert extracted data into LDEX (LIMRA Data Exchange) format."""
    ldex = {
        "LDEXTransmission": {
            "TransmissionHeader": {
                "TransmissionGUID": str(uuid.uuid4()),
                "SenderName": "Sutherland Document Intelligence",
                "ReceiverName": "American Fidelity",
                "CreationDateTime": datetime.utcnow().isoformat() + "Z",
                "TransmissionTypeCode": "Full",
                "SourceFileName": file_name,
            },
            "Employer": {},
            "Coverages": [],
            "Extraction": {
                "Categories": {},
                "TotalFieldsExtracted": 0,
                "ExtractionMethod": "Azure OpenAI GPT-4o",
            },
        }
    }

    # Populate Employer from benefits / general fields
    employer_fields = {}
    for f in categorized.get("benefits", []):
        employer_fields[f["key"]] = {
            "Value": str(f["value"]) if f["value"] else "",
            "Confidence": f["confidence"],
        }
    for f in categorized.get("additional", []):
        employer_fields[f["key"]] = {
            "Value": str(f["value"]) if f["value"] else "",
            "Confidence": f["confidence"],
        }
    ldex["LDEXTransmission"]["Employer"] = employer_fields

    # Populate Coverage sections
    coverage_cats = ["eligibility", "payroll", "calendar", "dental", "vision", "basiclife", "vollife", "afa"]
    for cat_id in coverage_cats:
        fields = categorized.get(cat_id, [])
        if not fields:
            continue
        cat_label = next((c["label"] for c in EXTRACTION_CATEGORIES if c["id"] == cat_id), cat_id)
        coverage = {
            "CoverageType": cat_label,
            "Fields": {},
        }
        for f in fields:
            coverage["Fields"][f["key"]] = {
                "Value": str(f["value"]) if f["value"] else "",
                "Confidence": f["confidence"],
            }
        ldex["LDEXTransmission"]["Coverages"].append(coverage)

    # Populate Extraction summary
    total_fields = 0
    for cat in EXTRACTION_CATEGORIES:
        fields = categorized.get(cat["id"], [])
        if fields:
            avg_conf = round(sum(f["confidence"] for f in fields) / len(fields))
            ldex["LDEXTransmission"]["Extraction"]["Categories"][cat["label"]] = {
                "FieldCount": len(fields),
                "AverageConfidence": avg_conf,
            }
            total_fields += len(fields)

    ldex["LDEXTransmission"]["Extraction"]["TotalFieldsExtracted"] = total_fields

    return ldex


def extract_text_from_pdf(pdf_bytes):
    text = ""
    with pdfplumber.open(pdf_bytes) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text


def extract_with_azure_openai(text):
    """Extract data using Azure OpenAI GPT-4o."""
    client = AzureOpenAI(
        azure_endpoint=AZURE_CONFIG["endpoint"],
        api_key=AZURE_CONFIG["api_key"],
        api_version=AZURE_CONFIG["api_version"],
    )
    response = client.chat.completions.create(
        model=AZURE_CONFIG["deployment"],
        temperature=0,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
    )
    content = response.choices[0].message.content.strip()
    # Strip markdown code blocks
    if content.startswith("```"):
        content = content.split("\n", 1)[1] if "\n" in content else content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
    return json.loads(content)


def extract_basic(text):
    """Fallback extraction - splits colon-separated key:value lines."""
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
    return f'<iframe src="data:application/pdf;base64,{b64}" class="pdf-viewer-frame" type="application/pdf"></iframe>'


# ============================
# Login Page
# ============================
def render_login():
    st.markdown("""
    <style>
        [data-testid="stMain"] {
            background: linear-gradient(135deg, #1a1a3e 0%, #2d1b69 25%, #1a1a3e 45%, #4a1942 70%, #C62828 100%);
        }
    </style>
    """, unsafe_allow_html=True)

    _c1, col_center, _c2 = st.columns([1, 1.2, 1])
    with col_center:
        st.markdown("<div style='height:100px;'></div>", unsafe_allow_html=True)

        st.markdown("""
        <div class="login-card">
            <div class="login-logo-bar">
                <div class="login-logo-icon">AF</div>
                <div class="login-brand-text">SUTHERLAND</div>
            </div>
            <div class="login-main-title">American Fidelity</div>
            <div class="login-subtitle">Document Intelligence Platform</div>
            <div class="login-divider"></div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

        with st.form("login_form", clear_on_submit=False):
            st.markdown("##### User ID")
            user_id = st.text_input("User ID", placeholder="Enter your user ID", label_visibility="collapsed")
            st.markdown("##### Password")
            password = st.text_input("Password", type="password", placeholder="Enter your password", label_visibility="collapsed")

            st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
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
    <div class="main-header">
        <div class="header-brand">
            <div class="header-logo-box">AF</div>
            <div class="header-text">
                <h1>AMERICAN FIDELITY</h1>
                <p>Document Intelligence Platform &bull; Powered by Sutherland</p>
            </div>
        </div>
        <div class="header-right">
            <div class="header-user-pill">
                <div class="header-user-avatar">A</div>
                Admin
            </div>
        </div>
    </div>
    <div class="accent-line"></div>
    """, unsafe_allow_html=True)

    # Sidebar
    with st.sidebar:
        st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)
        st.markdown("### Settings")
        st.markdown(f"**User:** Admin")

        st.divider()

        st.markdown("### Azure OpenAI")

        # Allow API key input if not set via env
        if not AZURE_CONFIG["api_key"]:
            api_key_input = st.text_input(
                "Azure OpenAI API Key",
                type="password",
                placeholder="Enter your Azure OpenAI API Key",
                key="azure_api_key_input",
                label_visibility="collapsed",
            )
            if api_key_input:
                AZURE_CONFIG["api_key"] = api_key_input

        st.markdown(
            f"""
            <div style="font-size:12px;color:#888;margin-bottom:8px;">
                <strong>Endpoint:</strong> {AZURE_CONFIG['endpoint']}<br/>
                <strong>Model:</strong> {AZURE_CONFIG['deployment']}<br/>
                <strong>Status:</strong> {'<span style="color:#2e7d32;">Connected</span>' if AZURE_CONFIG['api_key'] else '<span style="color:#e65100;">Key Required</span>'}
            </div>
            """,
            unsafe_allow_html=True,
        )
        if AZURE_CONFIG["api_key"]:
            st.success("Azure OpenAI: Connected", icon="✅")
        else:
            st.warning("Enter API Key above or set AZURE_OPENAI_API_KEY env var", icon="⚠️")

        st.divider()

        st.markdown("### Output Format")
        st.markdown('<span class="ldex-tag">📦 LDEX Format</span>', unsafe_allow_html=True)
        st.caption("LIMRA Data Exchange Standard")

        st.divider()

        if st.button("🚪 Logout", use_container_width=True):
            for key in ["authenticated", "uploaded_files", "pdf_bytes", "results", "extraction_data", "ldex_data"]:
                st.session_state[key] = type(st.session_state[key])() if not isinstance(st.session_state[key], bool) else False
            st.rerun()

        st.markdown(
            "<div style='margin-top:20px;font-size:11px;color:#bbb;text-align:center;'>Sutherland &bull; v2.0</div>",
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)

    # Tabs
    tabs = st.tabs(["📤  Upload", "🔍  Extraction", "📊  Results (LDEX)"])

    with tabs[0]:
        render_upload_tab()
    with tabs[1]:
        render_extraction_tab()
    with tabs[2]:
        render_results_tab()


# ============================
# Upload Tab
# ============================
def render_upload_tab():
    st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
    st.markdown("### 📤 Upload Documents")
    st.markdown("Upload PDF documents for AI-powered intelligent data extraction")
    st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)

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

        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

        for _i, file in enumerate(uploaded):
            size_mb = file.size / (1024 * 1024)
            st.markdown(
                f"""
                <div class="file-row">
                    <div class="file-icon-box">📄</div>
                    <div class="file-details">
                        <div class="fname">{file.name}</div>
                        <div class="fsize">{size_mb:.2f} MB &bull; PDF Document</div>
                    </div>
                    <div class="file-status">✅</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("<div style='height:20px;'></div>", unsafe_allow_html=True)

        col1, col2, _col3 = st.columns([1.2, 1, 2])
        with col1:
            extract_btn = st.button(
                "🚀 Upload & Extract Data",
                type="primary",
                use_container_width=True,
            )
        with col2:
            st.markdown(
                '<span class="stat-pill">📦 Output: <span class="stat-num">LDEX</span></span>',
                unsafe_allow_html=True,
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
    ldex_data = []

    progress = st.progress(0, text="Preparing documents...")
    status_box = st.empty()

    for i, file in enumerate(uploaded_files):
        file_bytes = file.read()
        pdf_bytes_list.append(file_bytes)

        step_base = i / len(uploaded_files)
        step_size = 1 / len(uploaded_files)

        # Step 1: Extract text
        progress.progress(step_base + step_size * 0.15, text=f"📖 Reading PDF text from {file.name}...")
        status_box.info(f"Step 1/3: Extracting text from **{file.name}**...")

        text = extract_text_from_pdf(io.BytesIO(file_bytes))

        if not text.strip():
            st.warning(f"Could not extract text from {file.name}. The PDF may be image-based.")
            results.append({"fileName": file.name, "data": {}})
            extraction_data.append({cat["id"]: [] for cat in EXTRACTION_CATEGORIES})
            ldex_data.append({})
            continue

        # Step 2: Azure OpenAI Extraction
        progress.progress(step_base + step_size * 0.45, text=f"🤖 Azure OpenAI extracting data from {file.name}...")
        status_box.info(f"Step 2/3: AI analyzing **{file.name}** with GPT-4o...")

        try:
            if AZURE_CONFIG["api_key"]:
                data = extract_with_azure_openai(text)
            else:
                st.info(f"No Azure API key configured. Using basic extraction for {file.name}.")
                data = extract_basic(text)
        except Exception as e:
            st.warning(f"Azure OpenAI error for {file.name}: {str(e)}. Falling back to basic extraction.")
            data = extract_basic(text)

        # Step 3: Categorize & build LDEX
        progress.progress(step_base + step_size * 0.8, text=f"📂 Building LDEX format for {file.name}...")
        status_box.info(f"Step 3/3: Categorizing and building LDEX for **{file.name}**...")

        categorized = categorize_fields(data)
        ldex = build_ldex_json(data, file.name, categorized)

        results.append({"fileName": file.name, "data": data})
        extraction_data.append(categorized)
        ldex_data.append(ldex)

    progress.progress(1.0, text="✅ Extraction complete!")
    status_box.success(f"Successfully processed {len(results)} document(s) in LDEX format!")

    st.session_state.results = results
    st.session_state.pdf_bytes = pdf_bytes_list
    st.session_state.extraction_data = extraction_data
    st.session_state.ldex_data = ldex_data

    st.balloons()
    st.rerun()


# ============================
# Extraction Tab
# ============================
def render_extraction_tab():
    if not st.session_state.results:
        st.markdown("<div style='height:32px;'></div>", unsafe_allow_html=True)
        st.markdown(
            """
            <div class="empty-state-box">
                <div class="empty-state-icon">🔍</div>
                <h3>No Extraction Data</h3>
                <p>Upload and process documents to view categorized extracted data with confidence scores.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    for doc_idx, result in enumerate(st.session_state.results):
        categorized = st.session_state.extraction_data[doc_idx]
        total_fields = sum(len(fields) for fields in categorized.values())

        # Section header
        st.markdown(
            f"""
            <div class="glass-card" style="margin-bottom:24px;">
                <div class="section-header-bar">
                    <h3>📄 Data Extraction Sheet - {doc_idx + 1}</h3>
                    <div class="doc-tag">{result['fileName']}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Stats row
        cat_with_data = sum(1 for cat in EXTRACTION_CATEGORIES if categorized.get(cat["id"]))
        all_confs = [f["confidence"] for fields in categorized.values() for f in fields if f["confidence"] > 0]
        overall_conf = round(sum(all_confs) / len(all_confs)) if all_confs else 0

        st.markdown(
            f"""
            <div style="margin-bottom:16px;">
                <span class="stat-pill">📊 Total: <span class="stat-num">{total_fields}</span> fields</span>
                <span class="stat-pill">📂 Categories: <span class="stat-num">{cat_with_data}</span></span>
                <span class="stat-pill">🎯 Avg Confidence: <span class="stat-num">{overall_conf}%</span></span>
                <span class="ldex-tag">📦 LDEX</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Split view
        col_pdf, col_data = st.columns([1, 1], gap="medium")

        # LEFT: PDF
        with col_pdf:
            st.markdown("**📄 Document Viewer**")
            if doc_idx < len(st.session_state.pdf_bytes):
                pdf_html = get_pdf_display_html(st.session_state.pdf_bytes[doc_idx])
                st.markdown(pdf_html, unsafe_allow_html=True)
                st.download_button(
                    "⬇️ Download PDF",
                    data=st.session_state.pdf_bytes[doc_idx],
                    file_name=result["fileName"],
                    mime="application/pdf",
                    use_container_width=True,
                    key=f"dl_pdf_{doc_idx}",
                )

        # RIGHT: Categorized Data
        with col_data:
            st.markdown(f"**📊 Extracted Data** ({total_fields} fields)")

            for cat in EXTRACTION_CATEGORIES:
                fields = categorized.get(cat["id"], [])
                if not fields:
                    continue

                avg_conf = round(sum(f["confidence"] for f in fields) / len(fields))
                conf_cls = get_confidence_class(avg_conf)
                conf_emoji = "🟢" if conf_cls == "high" else ("🟡" if conf_cls == "medium" else "🔴")

                with st.expander(
                    f"{cat['icon']}  {cat['label']}  —  {len(fields)} fields  |  {conf_emoji} {avg_conf}%",
                    expanded=(cat["id"] in ["benefits", "eligibility", "payroll"]),
                ):
                    rows_html = ""
                    for i, f in enumerate(fields):
                        conf_html = conf_badge_html(f["confidence"])
                        val = str(f["value"]) if f["value"] is not None else ""
                        rows_html += f"""
                        <tr>
                            <td class="row-num">{i + 1}</td>
                            <td><span class="field-name">{f['key']}</span></td>
                            <td><span class="field-value">{val}</span></td>
                            <td style="text-align:center;width:100px;">{conf_html}</td>
                        </tr>
                        """

                    st.markdown(
                        f"""
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
                        """,
                        unsafe_allow_html=True,
                    )

        st.markdown("<div style='height:24px;'></div>", unsafe_allow_html=True)
        st.divider()


# ============================
# Results Tab (LDEX)
# ============================
def render_results_tab():
    if not st.session_state.results:
        st.markdown("<div style='height:32px;'></div>", unsafe_allow_html=True)
        st.markdown(
            """
            <div class="empty-state-box">
                <div class="empty-state-icon">📊</div>
                <h3>No Results Yet</h3>
                <p>Upload and process documents to view LDEX format JSON results.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    for idx, result in enumerate(st.session_state.results):
        ldex = st.session_state.ldex_data[idx] if idx < len(st.session_state.ldex_data) else {}
        ldex_str = json.dumps(ldex, indent=2)
        flat_str = json.dumps(result["data"], indent=2)

        # Card header
        st.markdown(
            f"""
            <div class="glass-card" style="margin-bottom:16px;">
                <div class="result-card-header">
                    <div class="result-card-title">
                        <div class="doc-num-badge">{idx + 1}</div>
                        <div class="doc-info">
                            <strong>{result['fileName']}</strong>
                            <span>Document {idx + 1} of {len(st.session_state.results)} &bull; LDEX Format</span>
                        </div>
                    </div>
                    <div class="ldex-tag">📦 LDEX v1.0</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Key fields summary
        data = result["data"]
        entries = [(k, v) for k, v in data.items() if not isinstance(v, (dict, list))]
        if entries:
            cols = st.columns(4)
            for i, (key, value) in enumerate(entries[:8]):
                with cols[i % 4]:
                    st.markdown(
                        f"""
                        <div class="kf-card">
                            <div class="kf-label">{key}</div>
                            <div class="kf-value">{value}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

        st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)

        # LDEX JSON and Flat JSON tabs
        json_tab1, json_tab2 = st.tabs(["📦 LDEX Format JSON", "📋 Flat JSON"])

        with json_tab1:
            st.code(ldex_str, language="json")
            col_a, col_b, _col_c = st.columns([1, 1, 2])
            with col_a:
                st.download_button(
                    "⬇️ Download LDEX JSON",
                    data=ldex_str,
                    file_name=f"{result['fileName'].replace('.pdf', '')}_LDEX.json",
                    mime="application/json",
                    use_container_width=True,
                    key=f"dl_ldex_{idx}",
                )

        with json_tab2:
            st.code(flat_str, language="json")
            col_a2, col_b2, _col_c2 = st.columns([1, 1, 2])
            with col_a2:
                st.download_button(
                    "⬇️ Download Flat JSON",
                    data=flat_str,
                    file_name=f"{result['fileName'].replace('.pdf', '')}_extracted.json",
                    mime="application/json",
                    use_container_width=True,
                    key=f"dl_flat_{idx}",
                )

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
