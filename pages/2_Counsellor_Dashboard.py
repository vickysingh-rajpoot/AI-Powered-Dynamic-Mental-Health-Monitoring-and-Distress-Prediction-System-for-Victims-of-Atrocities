import os
import sys
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Add parent directory to path for engine imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.risk import get_all_cases_ranked, explain_risk
from engine.trend import get_trend_for_case
from engine.scoring import score_all_checkins

st.set_page_config(
    page_title="Counsellor Triage Dashboard",
    page_icon="📊",
    layout="wide"
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "db", "victims.db")

st.markdown("""
<style>
    .dash-header {
        background: linear-gradient(135deg, #0F172A 0%, #1E3A8A 100%);
        color: white;
        padding: 1.2rem 1.8rem;
        border-radius: 10px;
        margin-bottom: 1.2rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .dash-header h2 {
        color: white !important;
        margin: 0;
        font-size: 1.8rem;
    }
    .dash-header p {
        color: #94A3B8;
        margin: 0.2rem 0 0 0;
        font-size: 0.95rem;
    }
    .badge-high {
        background-color: #FEE2E2;
        color: #991B1B;
        padding: 0.25rem 0.6rem;
        border-radius: 6px;
        font-weight: 700;
        display: inline-block;
    }
    .badge-mod {
        background-color: #FEF3C7;
        color: #92400E;
        padding: 0.25rem 0.6rem;
        border-radius: 6px;
        font-weight: 700;
        display: inline-block;
    }
    .badge-low {
        background-color: #D1FAE5;
        color: #065F46;
        padding: 0.25rem 0.6rem;
        border-radius: 6px;
        font-weight: 700;
        display: inline-block;
    }
    .rationale-box {
        background-color: #F8FAFC;
        border-left: 4px solid #2563EB;
        padding: 1rem;
        border-radius: 6px;
        margin-top: 1rem;
        font-size: 1.05rem;
        color: #1E293B;
    }
</style>
""", unsafe_allow_html=True)

# Header Section with Refresh Button
head_col1, head_col2 = st.columns([4, 1])

with head_col1:
    st.markdown("""
    <div>
        <h2 style="color: #1E3A8A; margin-bottom: 0.2rem;">🏛️ Victim Case Triage & Risk Dashboard</h2>
        <p style="color: #64748B; margin-top: 0;">Ministry of Social Justice & Empowerment | SIH26094 Monitoring Pipeline</p>
    </div>
    """, unsafe_allow_html=True)

with head_col2:
    st.write("")
    if st.button("🔄 Refresh Data", type="primary", use_container_width=True):
        st.cache_data.clear()
        st.toast("✅ Dashboard refreshed with live database check-ins!", icon="🔄")
        st.rerun()

st.divider()

if not os.path.exists(DB_PATH):
    from data.generate_synthetic_data import main as init_db
    init_db()

# Fetch ranked cases data
ranked_df = get_all_cases_ranked()

if ranked_df.empty:
    st.warning("⚠️ No victim case data available.")
    st.stop()

# Fetch categories from database to enrich main display table
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
cursor.execute("SELECT DISTINCT case_id, category FROM checkins;")
cat_map = dict(cursor.fetchall())
conn.close()

ranked_df["category"] = ranked_df["case_id"].map(cat_map).fillna("Unknown Category")

# Calculate summary metric numbers
total_cases = len(ranked_df)
high_cases = len(ranked_df[ranked_df["classification"] == "High"])
mod_cases = len(ranked_df[ranked_df["classification"] == "Moderate"])
low_cases = len(ranked_df[ranked_df["classification"] == "Low"])

# Summary Cards Row
m1, m2, m3, m4 = st.columns(4)
m1.metric("📊 Total Tracked Cases", total_cases)
m2.metric("🔴 High Risk Cases", high_cases, delta="Action Required", delta_color="inverse")
m3.metric("🟡 Moderate Risk Cases", mod_cases)
m4.metric("🟢 Low Risk Cases", low_cases)

st.subheader("📋 Case Risk Priority Matrix (Sorted Highest to Lowest Risk)")

# Build presentation table with HTML color badges for clear visual distinction
display_df = ranked_df[["case_id", "category", "composite_score", "classification"]].copy()

def format_risk_badge(val):
    if val == "High":
        return "🔴 HIGH RISK"
    elif val == "Moderate":
        return "🟡 MODERATE RISK"
    else:
        return "🟢 LOW RISK"

display_df["Risk Badge"] = display_df["classification"].apply(format_risk_badge)
display_df.rename(columns={
    "case_id": "Case ID",
    "category": "Victim Crime Category",
    "composite_score": "Composite Risk Score (0-100)"
}, inplace=True)

# Display Table using Streamlit Dataframe with styled column config
st.dataframe(
    display_df[["Case ID", "Victim Crime Category", "Composite Risk Score (0-100)", "Risk Badge"]],
    use_container_width=True,
    hide_index=True,
    column_config={
        "Composite Risk Score (0-100)": st.column_config.ProgressColumn(
            "Composite Risk Score (0-100)",
            format="%d / 100",
            min_value=0,
            max_value=100
        ),
        "Risk Badge": st.column_config.TextColumn(
            "Risk Level Badge",
            help="High >= 60 | Moderate >= 35 | Low < 35"
        )
    }
)

st.divider()

# Detailed Case Inspection Section
st.subheader("🔎 Individual Case Inspection & Explainability Analysis")

case_id_list = ranked_df["case_id"].tolist()
selected_case_id = st.selectbox("Select Case ID to inspect detailed distress trajectory & factor breakdown:", case_id_list)

# Load data for selected case
case_scores_df = score_all_checkins(selected_case_id)
trend_info = get_trend_for_case(selected_case_id)
risk_explanation = explain_risk(selected_case_id)

factors = risk_explanation["factors"]
classification = risk_explanation["classification"]
score_val = risk_explanation["composite_score"]

# Side-by-Side Plotly Charts
col_chart_left, col_chart_right = st.columns(2)

with col_chart_left:
    st.markdown("##### 📈 Dynamic Distress Trajectory Across Check-ins")
    
    fig_line = px.line(
        case_scores_df,
        x="week_number",
        y="dynamic_distress_score",
        markers=True,
        title=f"Distress Over Time ({selected_case_id}) — Trend: {trend_info['classification'].upper()}",
        labels={"week_number": "Check-in Week Number", "dynamic_distress_score": "Dynamic Distress Score (Max 35)"},
        color_discrete_sequence=["#1E3A8A"]
    )
    
    fig_line.add_hline(y=20.0, line_dash="dash", line_color="#F59E0B", annotation_text="Elevated Warning (20)")
    fig_line.add_hline(y=28.0, line_dash="dash", line_color="#EF4444", annotation_text="Critical Distress (28)")
    fig_line.update_layout(yaxis_range=[0, 36], margin=dict(l=20, r=20, t=40, b=20))
    st.plotly_chart(fig_line, use_container_width=True)

with col_chart_right:
    st.markdown("##### 📊 Risk Contribution Factor Breakdown")
    
    factor_labels = {
        "trend_contribution": "Distress Trend Slope",
        "category_contribution": "Crime Severity Weight",
        "threat_contribution": "Threat Language Flag",
        "disengagement_contribution": "Disengagement Flag"
    }
    
    bar_df = pd.DataFrame({
        "Factor": [factor_labels[k] for k in factors.keys()],
        "Points": list(factors.values())
    })
    
    fig_bar = px.bar(
        bar_df,
        x="Points",
        y="Factor",
        orientation="h",
        title=f"Explainability Factors (Total Composite Score: {score_val} / 100)",
        color="Points",
        color_continuous_scale="Tealgrn"
    )
    fig_bar.update_layout(xaxis_range=[0, 45], showlegend=False, margin=dict(l=20, r=20, t=40, b=20))
    st.plotly_chart(fig_bar, use_container_width=True)

# One-line plain text summary built purely via Python string formatting
trend_class = trend_info["classification"]
threat_text = "detected in recent text" if factors["threat_contribution"] > 0 else "not detected"
disengage_text = "victim is disengaged (missed consecutive check-ins)" if factors["disengagement_contribution"] > 0 else "victim is actively responding"

plain_text_summary = f"Flagged as {classification} risk: distress trend is {trend_class}, threat-related language {threat_text}, {disengage_text}."

if classification == "High":
    st.error(f"🚨 **Case Rationale**: {plain_text_summary}")
elif classification == "Moderate":
    st.warning(f"⚠️ **Case Rationale**: {plain_text_summary}")
else:
    st.success(f"✅ **Case Rationale**: {plain_text_summary}")
