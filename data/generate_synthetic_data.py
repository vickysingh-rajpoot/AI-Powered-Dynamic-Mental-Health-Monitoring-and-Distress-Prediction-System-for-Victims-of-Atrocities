import os
import sqlite3
import csv
import random
from datetime import datetime, timedelta

# Set fixed random seed for reproducibility
random.seed(42)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_DIR = os.path.join(BASE_DIR, "db")
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DB_DIR, "victims.db")
CSV_PATH = os.path.join(DATA_DIR, "synthetic_checkins.csv")

CREATE_TABLE_SQL = """
CREATE TABLE checkins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id TEXT,
    category TEXT,
    category_weight INTEGER,
    channel TEXT,
    language TEXT,
    state TEXT,
    district TEXT,
    week_number INTEGER,
    checkin_date TEXT,
    structured_score INTEGER,
    free_text TEXT,
    responded INTEGER,
    trajectory_type TEXT
);
"""

PROFILES = [
    {
        "case_id": "ATR-2026-0001",
        "category": "Rape/Gang-rape Victim",
        "category_weight": 5,
        "channel": "Chatbot",
        "language": "Hindi",
        "state": "Maharashtra",
        "district": "Pune",
        "trajectory_type": "worsening"
    },
    {
        "case_id": "ATR-2026-0002",
        "category": "Threatened Witness",
        "category_weight": 4,
        "channel": "SMS",
        "language": "English",
        "state": "Uttar Pradesh",
        "district": "Lucknow",
        "trajectory_type": "sudden_threat"
    },
    {
        "case_id": "ATR-2026-0003",
        "category": "Caste-based Violence - Family",
        "category_weight": 4,
        "channel": "IVRS",
        "language": "Marathi",
        "state": "Maharashtra",
        "district": "Nagpur",
        "trajectory_type": "improving"
    },
    {
        "case_id": "ATR-2026-0004",
        "category": "Murder/Grievous Hurt Victim Family",
        "category_weight": 5,
        "channel": "Chatbot",
        "language": "Hindi",
        "state": "Bihar",
        "district": "Patna",
        "trajectory_type": "steady_high_risk"
    },
    {
        "case_id": "ATR-2026-0005",
        "category": "Rape/Gang-rape Victim",
        "category_weight": 5,
        "channel": "Chatbot",
        "language": "Bengali",
        "state": "West Bengal",
        "district": "Kolkata",
        "trajectory_type": "disengaging"
    },
    {
        "case_id": "ATR-2026-0006",
        "category": "Caste-based Violence - Family",
        "category_weight": 4,
        "channel": "IVRS",
        "language": "Tamil",
        "state": "Tamil Nadu",
        "district": "Salem",
        "trajectory_type": "fluctuating_stable"
    },
    {
        "case_id": "ATR-2026-0007",
        "category": "Threatened Witness",
        "category_weight": 4,
        "channel": "SMS",
        "language": "Hindi",
        "state": "Uttar Pradesh",
        "district": "Varanasi",
        "trajectory_type": "worsening"
    },
    {
        "case_id": "ATR-2026-0008",
        "category": "Arson Victim",
        "category_weight": 3,
        "channel": "Chatbot",
        "language": "Gujarati",
        "state": "Gujarat",
        "district": "Ahmedabad",
        "trajectory_type": "improving"
    },
    {
        "case_id": "ATR-2026-0009",
        "category": "Murder/Grievous Hurt Victim Family",
        "category_weight": 5,
        "channel": "IVRS",
        "language": "Telugu",
        "state": "Telangana",
        "district": "Hyderabad",
        "trajectory_type": "disengaging"
    },
    {
        "case_id": "ATR-2026-0010",
        "category": "Caste-based Violence - Family",
        "category_weight": 4,
        "channel": "SMS",
        "language": "Kannada",
        "state": "Karnataka",
        "district": "Bengaluru",
        "trajectory_type": "fluctuating_stable"
    }
]

NEUTRAL_TEXTS = [
    "Feeling okay and manageable this week.",
    "Attended regular routine, everything felt baseline normal.",
    "Doing relatively well, resting at home today.",
    "No major issues this week, feeling calm."
]

MILD_STRESS_TEXTS = [
    "Anxious about the court date and having trouble sleeping.",
    "Feeling mild stress regarding investigation updates.",
    "A bit nervous about upcoming legal procedures.",
    "Trouble concentrating today due to stress about the case."
]

HIGH_STRESS_TEXTS = [
    "Neighbors becoming distant, struggling with money and expenses.",
    "Feeling socially isolated and constant financial worry.",
    "Struggling to manage household expenses and coping with ongoing trial stress.",
    "Hard to manage daily routine, feeling isolated from community support."
]

SEVERE_DISTRESS_TEXTS = [
    "Not feeling safe at all, feeling completely hopeless.",
    "Extreme anxiety every night, feeling vulnerable and overwhelmed.",
    "Severe trauma symptoms, feeling unsafe in my environment.",
    "Helpless and fearful about the future, unable to leave room."
]

def get_free_text(score: int, case_id: str, week: int, trajectory: str) -> str:
    if case_id == "ATR-2026-0002" and week == 6:
        return "I am terrified, someone followed me home from the market yesterday."
    if case_id == "ATR-2026-0002" and week == 7:
        return "I don't feel safe, they warned us to withdraw the case immediately."

    if trajectory == "steady_high_risk" and week == 4:
        return "I've been getting strange calls at night, feeling hopeless and unsafe."

    if score is None:
        return ""
    
    if score < 10:
        return random.choice(NEUTRAL_TEXTS)
    elif score <= 15:
        return random.choice(MILD_STRESS_TEXTS)
    elif score <= 21:
        return random.choice(HIGH_STRESS_TEXTS)
    else:
        return random.choice(SEVERE_DISTRESS_TEXTS)

def generate_weekly_scores(trajectory: str) -> list[tuple[int | None, int]]:
    res = []
    if trajectory == "worsening":
        current = random.randint(6, 9)
        for w in range(1, 8):
            res.append((min(27, current), 1))
            current += random.randint(2, 4)
            
    elif trajectory == "improving":
        current = random.randint(16, 20)
        for w in range(1, 8):
            res.append((max(2, current), 1))
            current -= random.randint(1, 3)
            
    elif trajectory == "fluctuating_stable":
        for w in range(1, 8):
            score = random.randint(9, 13)
            res.append((score, 1))
            
    elif trajectory == "sudden_threat":
        for w in range(1, 6):
            score = random.randint(7, 10)
            res.append((score, 1))
        res.append((random.randint(21, 23), 1))
        res.append((random.randint(24, 27), 1))
        
    elif trajectory == "steady_high_risk":
        for w in range(1, 8):
            score = random.randint(20, 24)
            res.append((score, 1))
            
    elif trajectory == "disengaging":
        current = random.randint(8, 11)
        for w in range(1, 6):
            res.append((current, 1))
            current += random.randint(2, 3)
        res.append((None, 0))
        res.append((None, 0))

    return res

def main():
    os.makedirs(DB_DIR, exist_ok=True)
    os.makedirs(DATA_DIR, exist_ok=True)
    
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(CREATE_TABLE_SQL)
    
    today = datetime.now()
    records = []
    
    for prof in PROFILES:
        case_id = prof["case_id"]
        category = prof["category"]
        cat_weight = prof["category_weight"]
        channel = prof["channel"]
        language = prof["language"]
        state = prof["state"]
        district = prof["district"]
        trajectory = prof["trajectory_type"]
        
        scores_info = generate_weekly_scores(trajectory)
        
        for week in range(1, 8):
            weeks_ago = 7 - week
            checkin_date = (today - timedelta(weeks=weeks_ago)).strftime("%Y-%m-%d")
            struct_score, responded = scores_info[week - 1]
            
            if responded == 0:
                free_text = ""
            else:
                free_text = get_free_text(struct_score, case_id, week, trajectory)
                
            records.append({
                "case_id": case_id,
                "category": category,
                "category_weight": cat_weight,
                "channel": channel,
                "language": language,
                "state": state,
                "district": district,
                "week_number": week,
                "checkin_date": checkin_date,
                "structured_score": struct_score,
                "free_text": free_text,
                "responded": responded,
                "trajectory_type": trajectory
            })
            
    insert_sql = """
    INSERT INTO checkins (
        case_id, category, category_weight, channel, language, state, district,
        week_number, checkin_date, structured_score, free_text,
        responded, trajectory_type
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """
    db_rows = [
        (
            r["case_id"], r["category"], r["category_weight"], r["channel"], r["language"],
            r["state"], r["district"], r["week_number"], r["checkin_date"], r["structured_score"],
            r["free_text"], r["responded"], r["trajectory_type"]
        )
        for r in records
    ]
    cursor.executemany(insert_sql, db_rows)
    conn.commit()
    conn.close()
    
    csv_headers = [
        "id", "case_id", "category", "category_weight", "channel", "language", "state", "district",
        "week_number", "checkin_date", "structured_score", "free_text",
        "responded", "trajectory_type"
    ]
    with open(CSV_PATH, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(csv_headers)
        for idx, r in enumerate(records, start=1):
            writer.writerow([
                idx, r["case_id"], r["category"], r["category_weight"], r["channel"], r["language"],
                r["state"], r["district"], r["week_number"], r["checkin_date"],
                r["structured_score"] if r["structured_score"] is not None else "",
                r["free_text"], r["responded"], r["trajectory_type"]
            ])
            
    print(f"Total synthetic check-in records created: {len(records)} with State & District metadata.")

if __name__ == "__main__":
    main()
