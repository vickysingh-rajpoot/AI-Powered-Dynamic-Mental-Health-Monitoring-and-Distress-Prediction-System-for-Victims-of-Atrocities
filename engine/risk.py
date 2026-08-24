import os
import sys
import sqlite3
import pandas as pd


sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.trend import get_trend_for_case
from engine.disengagement import check_disengagement

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "db", "victims.db")


THREAT_KEYWORDS = [
    "threat", "threatened", "followed", "scared", "afraid",
    "unsafe", "warned", "watched", "intimidate", "withdraw the case"
]


TREND_WORSENING_POINTS = 40
TREND_STABLE_POINTS = 15
TREND_IMPROVING_POINTS = 0

CATEGORY_WEIGHT_MULTIPLIER = 5

THREAT_KEYWORD_POINTS = 20
DISENGAGEMENT_POINTS = 15

RISK_THRESHOLD_HIGH = 60
RISK_THRESHOLD_MODERATE = 35

def detect_threat_keywords(case_id: str) -> bool:
    """
    Connects to db/victims.db, retrieves the free_text of the 2 most recent check-ins
    for case_id (ordered by week_number descending), and returns True if any keyword from
    THREAT_KEYWORDS appears as a case-insensitive substring in either free_text value.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    query = "SELECT free_text FROM checkins WHERE case_id = ? ORDER BY week_number DESC LIMIT 2;"
    cursor.execute(query, (case_id,))
    rows = cursor.fetchall()
    conn.close()

    for (text,) in rows:
        if text:
            lower_text = text.lower()
            for kw in THREAT_KEYWORDS:
                if kw.lower() in lower_text:
                    return True
    return False

def compute_composite_risk(case_id: str) -> dict:
    """
    Calls get_trend_for_case, check_disengagement, detect_threat_keywords, and retrieves category_weight.
    Calculates trend_contribution, category_contribution, threat_contribution, disengagement_contribution.
    Sums contributions into composite_score, capped at max 100 using min().
    Returns dict with keys: case_id, composite_score, trend_contribution, category_contribution,
    threat_contribution, disengagement_contribution.
    """

    trend_info = get_trend_for_case(case_id)
    classification = trend_info["classification"]
    if classification == "worsening":
        trend_contrib = TREND_WORSENING_POINTS
    elif classification == "stable":
        trend_contrib = TREND_STABLE_POINTS
    else:
        trend_contrib = TREND_IMPROVING_POINTS


    disengage_info = check_disengagement(case_id)
    is_disengaged = disengage_info["disengaged"]
    disengage_contrib = DISENGAGEMENT_POINTS if is_disengaged else 0


    has_threat = detect_threat_keywords(case_id)
    threat_contrib = THREAT_KEYWORD_POINTS if has_threat else 0


    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT category_weight FROM checkins WHERE case_id = ? LIMIT 1;", (case_id,))
    row = cursor.fetchone()
    conn.close()

    category_weight = row[0] if row else 1
    category_contrib = category_weight * CATEGORY_WEIGHT_MULTIPLIER


    raw_score = trend_contrib + category_contrib + threat_contrib + disengage_contrib
    composite_score = min(100, raw_score)

    return {
        "case_id": case_id,
        "composite_score": composite_score,
        "trend_contribution": trend_contrib,
        "category_contribution": category_contrib,
        "threat_contribution": threat_contrib,
        "disengagement_contribution": disengage_contrib
    }

def explain_risk(case_id: str) -> dict:
    """
    Calls compute_composite_risk(case_id), determines classification as 'High' if >= 60,
    'Moderate' if >= 35, otherwise 'Low'. Returns dict with exact factor structure.
    """
    risk_info = compute_composite_risk(case_id)
    score = risk_info["composite_score"]

    if score >= RISK_THRESHOLD_HIGH:
        classification = "High"
    elif score >= RISK_THRESHOLD_MODERATE:
        classification = "Moderate"
    else:
        classification = "Low"

    return {
        "case_id": case_id,
        "composite_score": score,
        "classification": classification,
        "factors": {
            "trend_contribution": risk_info["trend_contribution"],
            "category_contribution": risk_info["category_contribution"],
            "threat_contribution": risk_info["threat_contribution"],
            "disengagement_contribution": risk_info["disengagement_contribution"]
        }
    }

def get_all_cases_ranked() -> pd.DataFrame:
    """
    Retrieves all distinct case_id values from checkins table, calls explain_risk on each,
    collects results into pandas DataFrame with specified columns, and returns sorted by
    composite_score descending.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT case_id FROM checkins ORDER BY case_id ASC;")
    case_ids = [r[0] for r in cursor.fetchall()]
    conn.close()

    rows = []
    for cid in case_ids:
        res = explain_risk(cid)
        factors = res["factors"]
        rows.append({
            "case_id": res["case_id"],
            "composite_score": res["composite_score"],
            "classification": res["classification"],
            "trend_contribution": factors["trend_contribution"],
            "category_contribution": factors["category_contribution"],
            "threat_contribution": factors["threat_contribution"],
            "disengagement_contribution": factors["disengagement_contribution"]
        })

    df = pd.DataFrame(rows)
    df = df.sort_values(by="composite_score", ascending=False).reset_index(drop=True)
    return df

if __name__ == "__main__":
    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 1000)

    print("--- Composite Risk Ranking for All Cases ---")
    ranked_df = get_all_cases_ranked()
    print(ranked_df)
