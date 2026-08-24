import os
import sys
import sqlite3
import pandas as pd
import plotly.express as px
import streamlit as st


sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.risk import get_all_cases_ranked, explain_risk
from engine.trend import get_trend_for_case
from engine.scoring import score_all_checkins
from engine.interventions import generate_interventions, get_sos_notice, URGENCY_COLOR

st.set_page_config(
    page_title="Counsellor Triage Dashboard",
    page_icon="📊",
    layout="wide"
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "db", "victims.db")

st.markdown("""
<style>
    .dash-header h2 {
        color: #1E3A8A;
        margin-bottom: 0.2rem;
    }
    .dash-header p {
        color: #64748B;
        margin-top: 0;
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
    .intervention-card {
        border-radius: 8px;
        padding: 0.85rem 1rem;
        margin-bottom: 0.6rem;
        border-left: 5px solid;
    }
    .intervention-title {
        font-weight: 700;
        font-size: 0.95rem;
        margin-bottom: 0.3rem;
    }
    .intervention-action {
        font-size: 0.88rem;
        color: #374151;
    }
    .channel-badge {
        display: inline-block;
        padding: 0.15rem 0.55rem;
        border-radius: 999px;
        font-size: 0.78rem;
        font-weight: 600;
        background-color: #DBEAFE;
        color: #1D4ED8;
    }
</style>
""", unsafe_allow_html=True)


if not os.path.exists(DB_PATH):
    from data.generate_synthetic_data import main as init_db
    init_db()


@st.cache_data(ttl=0)
def load_case_meta():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(
        """
        SELECT case_id, category, state, district, channel
        FROM checkins
        WHERE state IS NOT NULL AND district IS NOT NULL
        GROUP BY case_id
        HAVING id = MAX(id)
        """,
        conn
    )
    conn.close()
    return df




head_col1, head_col2 = st.columns([4, 1])

with head_col1:
    st.markdown("""
    <div class="dash-header">
        <h2>🏛️ Victim Case Triage &amp; Risk Dashboard</h2>
        <p>Ministry of Social Justice &amp; Empowerment | SIH26094 Monitoring Pipeline</p>
    </div>
    """, unsafe_allow_html=True)

with head_col2:
    st.write("")
    if st.button("🔄 Refresh Data", type="primary", use_container_width=True):
        st.cache_data.clear()
        st.toast("✅ Dashboard refreshed with live database check-ins!", icon="🔄")
        st.rerun()

st.divider()




st.subheader("🌐 Administrative Hierarchy Filter")
st.caption("Filter the triage dashboard by National overview, State, or District level — mirroring real government monitoring portals.")

case_meta_df = load_case_meta()

filter_col1, filter_col2, filter_col3 = st.columns(3)
with filter_col1:
    admin_level = st.radio(
        "Select Administration Level:",
        options=["🇮🇳 National Overview", "🏢 State Level", "📍 District Level"],
        horizontal=False,
        key="admin_level_radio"
    )
with filter_col2:
    if admin_level == "🏢 State Level":
        states = sorted(case_meta_df["state"].dropna().unique().tolist())
        selected_state = st.selectbox("Select State:", options=states, key="state_select")
    elif admin_level == "📍 District Level":
        states = sorted(case_meta_df["state"].dropna().unique().tolist())
        selected_state = st.selectbox("Select State:", options=states, key="state_select_d")
    else:
        selected_state = None
        st.info("Showing all cases across India.")
with filter_col3:
    if admin_level == "📍 District Level" and selected_state:
        districts = sorted(
            case_meta_df[case_meta_df["state"] == selected_state]["district"]
            .dropna().unique().tolist()
        )
        selected_district = st.selectbox("Select District:", options=districts, key="district_select")
    else:
        selected_district = None

st.divider()




ranked_df = get_all_cases_ranked()

if ranked_df.empty:
    st.warning("⚠️ No victim case data available.")
    st.stop()


ranked_df = ranked_df.merge(case_meta_df, on="case_id", how="left")


if admin_level == "🏢 State Level" and selected_state:
    ranked_df = ranked_df[ranked_df["state"] == selected_state].reset_index(drop=True)
elif admin_level == "📍 District Level" and selected_district:
    ranked_df = ranked_df[ranked_df["district"] == selected_district].reset_index(drop=True)

if ranked_df.empty:
    st.warning("No cases found for the selected region.")
    st.stop()


total_cases = len(ranked_df)
high_cases  = len(ranked_df[ranked_df["classification"] == "High"])
mod_cases   = len(ranked_df[ranked_df["classification"] == "Moderate"])
low_cases   = len(ranked_df[ranked_df["classification"] == "Low"])

m1, m2, m3, m4 = st.columns(4)
m1.metric("📊 Total Tracked Cases",  total_cases)
m2.metric("🔴 High Risk Cases",      high_cases,  delta="Action Required", delta_color="inverse")
m3.metric("🟡 Moderate Risk Cases",  mod_cases)
m4.metric("🟢 Low Risk Cases",       low_cases)

st.subheader("📋 Case Risk Priority Matrix (Sorted Highest → Lowest Risk)")


def fmt_badge(val):
    if val == "High":
        return "🔴 HIGH RISK"
    elif val == "Moderate":
        return "🟡 MODERATE RISK"
    return "🟢 LOW RISK"

display_df = ranked_df[[
    "case_id", "category", "state", "district", "channel",
    "composite_score", "classification"
]].copy()

display_df["Risk Level"] = display_df["classification"].apply(fmt_badge)
display_df.rename(columns={
    "case_id":         "Case ID",
    "category":        "Crime Category",
    "state":           "State",
    "district":        "District",
    "channel":         "Channel",
    "composite_score": "Risk Score (0–100)"
}, inplace=True)

st.dataframe(
    display_df[["Case ID", "Crime Category", "State", "District", "Channel", "Risk Score (0–100)", "Risk Level"]],
    use_container_width=True,
    hide_index=True,
    column_config={
        "Risk Score (0–100)": st.column_config.ProgressColumn(
            "Risk Score (0–100)",
            format="%d / 100",
            min_value=0,
            max_value=100
        ),
        "Risk Level": st.column_config.TextColumn(
            "Risk Level",
            help="High ≥ 60 | Moderate ≥ 35 | Low < 35"
        )
    }
)

st.divider()




st.subheader("🔎 Individual Case Inspection & Explainability Analysis")

case_id_list = ranked_df["case_id"].tolist()
selected_case_id = st.selectbox(
    "Select Case ID to inspect detailed distress trajectory & factor breakdown:",
    case_id_list,
    key="case_inspect_select"
)


case_row = ranked_df[ranked_df["case_id"] == selected_case_id].iloc[0]
case_state    = case_row.get("state",    "N/A")
case_district = case_row.get("district", "N/A")
case_category = case_row.get("category", "N/A")
case_channel  = case_row.get("channel",  "N/A")


info_cols = st.columns(4)
info_cols[0].info(f"📍 **Location**: {case_district}, {case_state}")
info_cols[1].info(f"🏷️ **Category**: {case_category}")
info_cols[2].info(f"📡 **Channel**: {case_channel}")
info_cols[3].info(f"🆔 **Case ID**: {selected_case_id}")

case_scores_df   = score_all_checkins(selected_case_id)
trend_info       = get_trend_for_case(selected_case_id)
risk_explanation = explain_risk(selected_case_id)

factors        = risk_explanation["factors"]
classification = risk_explanation["classification"]
score_val      = risk_explanation["composite_score"]


col_chart_left, col_chart_right = st.columns(2)

with col_chart_left:
    st.markdown("##### 📈 Dynamic Distress Trajectory Across Check-ins")
    fig_line = px.line(
        case_scores_df,
        x="week_number",
        y="dynamic_distress_score",
        markers=True,
        title=f"Distress Over Time ({selected_case_id}) — Trend: {trend_info['classification'].upper()}",
        labels={"week_number": "Check-in Week", "dynamic_distress_score": "Dynamic Distress Score (Max 35)"},
        color_discrete_sequence=["#1E3A8A"]
    )
    fig_line.add_hline(y=20.0, line_dash="dash", line_color="#F59E0B", annotation_text="Elevated Warning (20)")
    fig_line.add_hline(y=28.0, line_dash="dash", line_color="#EF4444", annotation_text="Critical Distress (28)")
    fig_line.update_layout(yaxis_range=[0, 36], margin=dict(l=20, r=20, t=40, b=20))
    st.plotly_chart(fig_line, use_container_width=True)

with col_chart_right:
    st.markdown("##### 📊 Risk Contribution Factor Breakdown")
    factor_labels = {
        "trend_contribution":          "Distress Trend Slope",
        "category_contribution":       "Crime Severity Weight",
        "threat_contribution":         "Threat Language Flag",
        "disengagement_contribution":  "Disengagement Flag"
    }
    bar_df = pd.DataFrame({
        "Factor": [factor_labels[k] for k in factors],
        "Points": list(factors.values())
    })
    fig_bar = px.bar(
        bar_df,
        x="Points",
        y="Factor",
        orientation="h",
        title=f"Explainability Factors — Composite Score: {score_val} / 100",
        color="Points",
        color_continuous_scale="Tealgrn"
    )
    fig_bar.update_layout(xaxis_range=[0, 45], showlegend=False, margin=dict(l=20, r=20, t=40, b=20))
    st.plotly_chart(fig_bar, use_container_width=True)


trend_class     = trend_info["classification"]
threat_text     = "detected in recent check-in text" if factors["threat_contribution"] > 0 else "not detected"
disengage_text  = "victim is disengaged (missed consecutive check-ins)" if factors["disengagement_contribution"] > 0 else "victim is actively responding"
plain_summary   = f"Flagged as **{classification} Risk**: distress trend is {trend_class}, threat-related language {threat_text}, {disengage_text}."

if classification == "High":
    st.error(f"🚨 **Case Rationale**: {plain_summary}")
elif classification == "Moderate":
    st.warning(f"⚠️ **Case Rationale**: {plain_summary}")
else:
    st.success(f"✅ **Case Rationale**: {plain_summary}")

st.divider()




st.subheader("💊 Automated Intervention Recommendations")
st.caption("Generated by the rule-based intervention engine under SC/ST (Prevention of Atrocities) Act, 1989.")

interventions = generate_interventions(selected_case_id)

for intv in interventions:
    urgency   = intv["urgency"]
    border_c  = URGENCY_COLOR.get(urgency, "#6B7280")
    bg_map    = {"CRITICAL": "#FEF2F2", "HIGH": "#FFF7ED", "MODERATE": "#FFFBEB", "LOW": "#F0FDF4"}
    bg_color  = bg_map.get(urgency, "#F9FAFB")

    st.markdown(f"""
    <div class="intervention-card" style="background-color:{bg_color}; border-left-color:{border_c};">
        <div class="intervention-title" style="color:{border_c};">
            {intv['icon']} {intv['title']}
            &nbsp;&nbsp;<span style="font-size:0.75rem; font-weight:600; color:{border_c}; border:1px solid {border_c}; padding:0.1rem 0.4rem; border-radius:4px;">{urgency}</span>
        </div>
        <div class="intervention-action">{intv['action']}</div>
        <div style="margin-top:0.4rem; font-size:0.8rem; color:#6B7280;">
            Responsible Authority: <strong>{intv['authority']}</strong>
        </div>
    </div>
    """, unsafe_allow_html=True)

st.divider()




st.subheader("🚨 Emergency SOS Authority Dispatcher")

if classification == "High":
    st.error(
        f"**{selected_case_id}** is classified as 🔴 **HIGH RISK** "
        f"(Score: {score_val}/100). Immediate authority notification is recommended."
    )
    if st.button(
        f"🚨 Dispatch Emergency SOS Notice — {selected_case_id}",
        type="primary",
        use_container_width=True
    ):
        notice_text = get_sos_notice(
            selected_case_id,
            case_state,
            case_district,
            case_category
        )
        st.code(notice_text, language="text")
        st.toast(
            f"🚨 Emergency SOS Notice generated for {selected_case_id}! "
            "Notify District Magistrate & SSP immediately.",
            icon="🚨"
        )
        st.download_button(
            label="⬇️ Download SOS Notice as .txt",
            data=notice_text,
            file_name=f"SOS_Notice_{selected_case_id}.txt",
            mime="text/plain",
            use_container_width=True
        )
elif classification == "Moderate":
    st.warning(
        f"**{selected_case_id}** is 🟡 **MODERATE RISK** (Score: {score_val}/100). "
        "Monitor closely. SOS Dispatcher activates only for High Risk cases."
    )
else:
    st.success(
        f"**{selected_case_id}** is 🟢 **LOW RISK** (Score: {score_val}/100). "
        "Continue regular monitoring."
    )
