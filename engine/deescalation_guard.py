import os
import sqlite3
import pandas as pd

from engine import risk
from engine.disengagement import check_disengagement
from engine.scoring import score_all_checkins
from engine.trend import classify_trend, compute_trend_slope, TREND_THRESHOLD


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "db", "victims.db")

PENDING_MESSAGE = (
    "This case showed a sudden change in the latest check-in. Awaiting one more "
    "consecutive check-in in the same direction before updating risk level. "
    "Currently held at the prior, confirmed risk level for safety."
)


def count_consecutive_recent_matching_checkins(
    case_id: str, direction: str, threshold: float = 15
) -> int:
    """Count the newest consecutive scores matching the requested direction."""
    scores = score_all_checkins(case_id)["dynamic_distress_score"].tolist()
    count = 0
    # Scores above 20 indicate elevated distress for the high-direction check.
    high_distress_threshold = 20

    for score in reversed(scores):
        if score is None:
            break
        if direction == "low" and score < threshold:
            count += 1
        elif direction == "high" and score > high_distress_threshold:
            count += 1
        else:
            break

    return count


def _risk_from_history(case_id: str, scores_df: pd.DataFrame) -> dict:
    """Calculate risk using a supplied history while preserving risk.py's rules."""
    scores = scores_df["dynamic_distress_score"].tolist()
    scores_used = scores[-6:] if len(scores) >= 6 else scores
    trend_classification = classify_trend(
        compute_trend_slope(scores_used), TREND_THRESHOLD
    )

    if trend_classification == "worsening":
        trend_contribution = risk.TREND_WORSENING_POINTS
    elif trend_classification == "stable":
        trend_contribution = risk.TREND_STABLE_POINTS
    else:
        trend_contribution = risk.TREND_IMPROVING_POINTS

    latest_rows = scores_df.sort_values("week_number", ascending=False).head(2)
    threat_contribution = 0
    for text in latest_rows["free_text"].tolist():
        if text and any(keyword.lower() in text.lower() for keyword in risk.THREAT_KEYWORDS):
            threat_contribution = risk.THREAT_KEYWORD_POINTS
            break

    recent_responses = latest_rows["responded"].tolist()
    disengagement_contribution = (
        risk.DISENGAGEMENT_POINTS
        if len(recent_responses) >= 2 and all(value == 0 for value in recent_responses)
        else 0
    )

    category_weight = scores_df["category_weight"].iloc[0] if not scores_df.empty else 1
    category_contribution = category_weight * risk.CATEGORY_WEIGHT_MULTIPLIER
    composite_score = min(
        100,
        trend_contribution
        + category_contribution
        + threat_contribution
        + disengagement_contribution,
    )

    if composite_score >= risk.RISK_THRESHOLD_HIGH:
        classification = "High"
    elif composite_score >= risk.RISK_THRESHOLD_MODERATE:
        classification = "Moderate"
    else:
        classification = "Low"

    return {
        "case_id": case_id,
        "composite_score": composite_score,
        "classification": classification,
        "factors": {
            "trend_contribution": trend_contribution,
            "category_contribution": category_contribution,
            "threat_contribution": threat_contribution,
            "disengagement_contribution": disengagement_contribution,
        },
    }


def get_effective_risk(case_id: str) -> dict:
    """Return current risk, holding a sudden unconfirmed classification change."""
    current = risk.compute_composite_risk(case_id)
    current_score_df = score_all_checkins(case_id)

    if len(current_score_df) < 2:
        return {
            **current,
            "classification": "High" if current["composite_score"] >= risk.RISK_THRESHOLD_HIGH
            else "Moderate" if current["composite_score"] >= risk.RISK_THRESHOLD_MODERATE
            else "Low",
            "pending_confirmation": False,
            "pending_direction": None,
            "message": None,
            "factors": {
                "trend_contribution": current["trend_contribution"],
                "category_contribution": current["category_contribution"],
                "threat_contribution": current["threat_contribution"],
                "disengagement_contribution": current["disengagement_contribution"],
            },
        }

    current_classification = (
        "High" if current["composite_score"] >= risk.RISK_THRESHOLD_HIGH
        else "Moderate" if current["composite_score"] >= risk.RISK_THRESHOLD_MODERATE
        else "Low"
    )
    prior = _risk_from_history(case_id, current_score_df.iloc[:-1])

    risk_order = {"Low": 0, "Moderate": 1, "High": 2}
    if current_classification == prior["classification"]:
        return {
            **current,
            "classification": current_classification,
            "pending_confirmation": False,
            "pending_direction": None,
            "message": None,
            "factors": {
                "trend_contribution": current["trend_contribution"],
                "category_contribution": current["category_contribution"],
                "threat_contribution": current["threat_contribution"],
                "disengagement_contribution": current["disengagement_contribution"],
            },
        }

    direction = "improving" if risk_order[current_classification] < risk_order[prior["classification"]] else "worsening"
    matching_count = count_consecutive_recent_matching_checkins(case_id, "low" if direction == "improving" else "high")
    if matching_count < 2:
        return {
            **prior,
            "pending_confirmation": True,
            "pending_direction": direction,
            "message": PENDING_MESSAGE,
        }

    return {
        **current,
        "classification": current_classification,
        "pending_confirmation": False,
        "pending_direction": None,
        "message": None,
        "factors": {
            "trend_contribution": current["trend_contribution"],
            "category_contribution": current["category_contribution"],
            "threat_contribution": current["threat_contribution"],
            "disengagement_contribution": current["disengagement_contribution"],
        },
    }


def get_all_cases_ranked_guarded() -> pd.DataFrame:
    """Build the risk ranking using effective risk for every case."""
    conn = sqlite3.connect(DB_PATH)
    case_ids = pd.read_sql_query(
        "SELECT DISTINCT case_id FROM checkins ORDER BY case_id ASC;", conn
    )["case_id"].tolist()
    conn.close()

    rows = []
    for case_id in case_ids:
        result = get_effective_risk(case_id)
        factors = result["factors"]
        rows.append({
            "case_id": result["case_id"],
            "composite_score": result["composite_score"],
            "classification": result["classification"],
            "trend_contribution": factors["trend_contribution"],
            "category_contribution": factors["category_contribution"],
            "threat_contribution": factors["threat_contribution"],
            "disengagement_contribution": factors["disengagement_contribution"],
            "pending_confirmation": result["pending_confirmation"],
        })

    return pd.DataFrame(rows).sort_values(
        by="composite_score", ascending=False
    ).reset_index(drop=True)


def get_recommended_intervention(classification: str) -> str:
    """Return the dashboard's existing standard intervention wording by risk level."""
    interventions = {
        "High": "Immediate authority notification is recommended.",
        "Moderate": "Monitor closely. SOS Dispatcher activates only for High Risk cases.",
        "Low": "Continue regular monitoring.",
    }
    return interventions.get(classification, "Continue regular monitoring.")


if __name__ == "__main__":
    print("--- Guarded Risk Verification ---")
    print("Guard module loaded successfully.")
