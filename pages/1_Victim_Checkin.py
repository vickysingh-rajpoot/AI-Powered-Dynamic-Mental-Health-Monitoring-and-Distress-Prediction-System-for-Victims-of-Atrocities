import os
import sys
import sqlite3
from datetime import datetime
import streamlit as st


sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.scoring import compute_dynamic_distress_score, get_sentiment_distress

st.set_page_config(
    page_title="Victim Check-in Portal",
    page_icon="📝",
    layout="centered"
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "db", "victims.db")

st.markdown("""
<style>
    .header-box {
        background: linear-gradient(135deg, #1E3A8A 0%, #3B82F6 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        text-align: center;
    }
    .header-box h2 {
        color: white !important;
        margin: 0;
    }
    .header-box p {
        color: #E0F2FE;
        margin-top: 0.4rem;
        margin-bottom: 0;
        font-size: 0.95rem;
    }
    .micro-label {
        font-weight: 600;
        color: #1E293B;
        font-size: 0.95rem;
        margin-bottom: 0.2rem;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="header-box">
    <h2>🤝 Victim Support Check-in Portal</h2>
    <p>Your privacy and safety are fully protected. Please share how you are feeling this week.</p>
</div>
""", unsafe_allow_html=True)

if not os.path.exists(DB_PATH):
    from data.generate_synthetic_data import main as init_db
    init_db()


conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
cursor.execute("SELECT DISTINCT case_id FROM checkins ORDER BY case_id ASC;")
case_rows = cursor.fetchall()
conn.close()

if not case_rows:
    st.warning("⚠️ No active case profiles found in the system.")
    st.stop()

case_list = [r[0] for r in case_rows]
selected_case_id = st.selectbox("🔑 Select Case ID (Simulating Victim Login):", case_list, key="selected_case_id")


conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
cursor.execute("""
        SELECT category, category_weight, channel, language, state, district, week_number
    FROM checkins
        WHERE case_id = ?
            AND state IS NOT NULL
            AND district IS NOT NULL
        ORDER BY week_number DESC, id DESC
        LIMIT 1
""", (selected_case_id,))
meta_row = cursor.fetchone()
conn.close()

if not meta_row or meta_row[0] is None:
    st.error(f"⚠️ Selected Case ID '{selected_case_id}' has no prior check-in records. Unable to locate profile metadata.")
    st.stop()

category, category_weight, channel, language, state, district, max_week = meta_row
next_week = max_week + 1

st.caption(f"**Profile Meta**: Category: `{category}` | Preferred Channel: `{channel}` | Next Expected Check-in: **Week {next_week}**")

st.divider()


with st.container(border=True):
    st.subheader("📋 Weekly Well-being Assessment")
    st.caption("Please rate each question from 1 to 5 based on your experience over the past 7 days.")

    st.markdown('<div class="micro-label">1. How anxious or on-edge have you felt this week?</div>', unsafe_allow_html=True)
    anxiety = st.slider("Anxiety", 1, 5, 3, help="1 = Very calm, 5 = Extremely anxious", label_visibility="collapsed", key=f"anxiety_slider_{selected_case_id}")

    st.markdown('<div class="micro-label">2. How would you rate your sleep quality over recent nights?</div>', unsafe_allow_html=True)
    sleep = st.slider("Sleep", 1, 5, 3, help="1 = Terrible / sleepless, 5 = Peaceful & restful", label_visibility="collapsed", key=f"sleep_slider_{selected_case_id}")

    st.markdown('<div class="micro-label">3. How hopeful do you feel about your case progressing effectively?</div>', unsafe_allow_html=True)
    hope = st.slider("Hopefulness", 1, 5, 3, help="1 = Very hopeful, 5 = Completely hopeless", label_visibility="collapsed", key=f"hope_slider_{selected_case_id}")

    st.markdown('<div class="micro-label">4. How has your overall mood and energy been this week?</div>', unsafe_allow_html=True)
    mood = st.slider("Mood", 1, 5, 3, help="1 = Very low / depressed, 5 = Good / cheerful", label_visibility="collapsed", key=f"mood_slider_{selected_case_id}")

st.markdown('<div class="micro-label" style="margin-top: 1rem;">💬 How have things been since your last check-in?</div>', unsafe_allow_html=True)
free_text = st.text_area(
    "How have things been since your last check-in?",
    placeholder="Feel free to share any updates about your safety, investigation, or support needed...",
    height=120,
    label_visibility="collapsed",
    key=f"free_text_{selected_case_id}"
)

if st.button("💌 Submit Weekly Check-in", type="primary", use_container_width=True):








    distress_anxiety = (anxiety - 1) / 4.0 * 7.0
    distress_sleep = (5 - sleep) / 4.0 * 6.5
    distress_hope = (5-hope) / 4.0 * 6.5
    distress_mood = (5 - mood) / 4.0 * 7.0

    raw_struct = distress_anxiety + distress_sleep + distress_hope + distress_mood
    structured_score = int(round(min(27.0, max(0.0, raw_struct))))

    today_str = datetime.now().strftime("%Y-%m-%d")


    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO checkins (
            case_id, category, category_weight, channel, language, state, district,
            week_number, checkin_date, structured_score, free_text,
            responded, trajectory_type
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, (
        selected_case_id, category, category_weight, channel, language,
        state, district, next_week, today_str, structured_score, free_text, 1, "live_submission"
    ))
    conn.commit()


    new_row_id = cursor.lastrowid
    cursor.execute("SELECT * FROM checkins WHERE id = ?;", (new_row_id,))
    row_data = cursor.fetchone()
    conn.close()

    new_row_dict = {
        "structured_score": row_data[10],
        "free_text": row_data[11]
    }

    computed_score = compute_dynamic_distress_score(new_row_dict)
    sent_score = get_sentiment_distress(free_text)


    st.markdown("""
    <div style="
        background: linear-gradient(135deg, #0F4C2A 0%, #166534 100%);
        color: white;
        padding: 1.2rem 1.6rem;
        border-radius: 10px;
        margin-top: 1rem;
        margin-bottom: 1rem;
    ">
        <div style="font-size: 1.15rem; font-weight: 700; margin-bottom: 0.3rem;">
            ✅ Check-in Submitted Successfully
        </div>
        <div style="font-size: 0.92rem; color: #BBF7D0;">
            Your response has been securely recorded. Your assigned counsellor will review your status.
        </div>
    </div>
    """, unsafe_allow_html=True)


    st.markdown("#### 🔍 Structured Score Breakdown")
    st.markdown(f"""
    - **Anxiety contribution:** ({anxiety} - 1) / 4 * 7.0 = **{distress_anxiety:.1f} points**
    - **Sleep contribution:** (5 - {sleep}) / 4 * 6.5 = **{distress_sleep:.1f} points**
    - **Hope contribution:** (5 - {hope}) / 4 * 6.5 = **{distress_hope:.1f} points**
    - **Mood contribution:** (5 - {mood}) / 4 * 7.0 = **{distress_mood:.1f} points**
    """)

    st.markdown("#### 📊 This Week's Submission Summary")
    col1, col2, col3 = st.columns(3)
    col1.metric(label="Structured Score (0–27)",        value=f"{structured_score} / 27")
    col2.metric(label="Sentiment Distress (0–10)",      value=f"{sent_score:.2f} / 10")
    col3.metric(label="Dynamic Distress Score (0–35)",  value=f"{computed_score:.2f} / 35")

    st.info("ℹ️ The counsellor dashboard will reflect this updated check-in immediately after refresh.")

