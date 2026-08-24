import os
import sqlite3
import streamlit as st

st.set_page_config(
    page_title="AI Mental Health Monitoring System - SIH26094",
    page_icon="🛡️",
    layout="centered"
)

st.markdown("""
<style>
    .hero-card {
        background: linear-gradient(135deg, #0F172A 0%, #1E3A8A 100%);
        color: white;
        padding: 2rem;
        border-radius: 12px;
        text-align: center;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .hero-card h1 {
        color: #FFFFFF !important;
        font-size: 2rem;
        margin-bottom: 0.5rem;
    }
    .hero-card p {
        color: #94A3B8;
        font-size: 1.05rem;
        margin-bottom: 0;
    }
    .feature-box {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 1.2rem;
        margin-bottom: 1rem;
    }
    .feature-box h4 {
        color: #1E3A8A;
        margin-top: 0;
        margin-bottom: 0.4rem;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero-card">
    <h1>🛡️ AI-Powered Dynamic Mental Health Monitoring System</h1>
    <p>Smart India Hackathon Prototype (SIH26094) | Ministry of Social Justice & Empowerment</p>
</div>
""", unsafe_allow_html=True)

st.markdown("""
### 📌 Project Overview
This system provides continuous psychological well-being monitoring and distress prediction for victims of atrocities throughout legal proceedings, rehabilitation, and compensation. Victims complete periodic check-ins combining structured ratings with free-text responses, which are scored locally and tracked over time to detect rising distress trends, threat language, or sudden silence. Cases are automatically prioritized on a counsellor triage dashboard, providing transparent, rule-based explainability for every risk level.
""")

st.divider()

st.markdown("### 🧭 System Navigation")
st.info("Please use the **sidebar menu** on the left to navigate between the two main modules:")

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    <div class="feature-box">
        <h4>📝 1. Victim Check-in</h4>
        <p>Simulates the victim-facing portal where victims submit weekly well-being check-ins, answering Likert sliders and free-text updates.</p>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div class="feature-box">
        <h4>📊 2. Counsellor Dashboard</h4>
        <p>Triage dashboard sorting cases by composite risk score (0–100), displaying Plotly trend lines, factor breakdowns, and plain-text explainability.</p>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# System Database Status Indicator
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "db", "victims.db")

st.markdown("### ⚙️ System Status")
if os.path.exists(DB_PATH):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(DISTINCT case_id), COUNT(*) FROM checkins;")
        num_cases, total_checkins = cursor.fetchone()
        conn.close()
        st.success(f"✅ **Database Connected**: `{num_cases}` victim profiles loaded with `{total_checkins}` total check-in records.")
    except Exception as e:
        st.warning(f"Database error: {e}")
else:
    st.warning("⚠️ Database not found. Please run `python data/generate_synthetic_data.py` to seed the database.")
