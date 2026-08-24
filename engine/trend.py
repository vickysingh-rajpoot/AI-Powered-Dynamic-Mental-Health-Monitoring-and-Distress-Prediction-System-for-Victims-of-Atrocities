import os
import sys
import numpy as np


sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.scoring import score_all_checkins


TREND_THRESHOLD = 0.8

def compute_trend_slope(scores: list) -> float:
    """
    Takes a list of dynamic_distress_score values (some entries may be None for missed check-ins).
    Filters out None values, keeps track of original week positions, and fits a degree 1 line
    using numpy.polyfit. Returns the slope value.
    If fewer than 2 valid scores remain, returns 0.0.
    """
    valid_pairs = [(i, float(s)) for i, s in enumerate(scores) if s is not None]

    if len(valid_pairs) < 2:
        return 0.0

    x = np.array([pair[0] for pair in valid_pairs], dtype=float)
    y = np.array([pair[1] for pair in valid_pairs], dtype=float)

    slope, _ = np.polyfit(x, y, 1)
    return float(slope)

def classify_trend(slope: float, threshold: float = TREND_THRESHOLD) -> str:
    """
    Returns 'worsening' if slope > threshold,
    returns 'improving' if slope < -threshold,
    otherwise returns 'stable'.
    """
    if slope > threshold:
        return 'worsening'
    elif slope < -threshold:
        return 'improving'
    else:
        return 'stable'

def get_trend_for_case(case_id: str) -> dict:
    """
    Imports and calls score_all_checkins(case_id) from engine/scoring.py,
    takes the dynamic_distress_score column, uses only the last 6 entries,
    calls compute_trend_slope on those values, calls classify_trend on the slope,
    and returns a dictionary with exact keys: case_id, slope, classification, scores_used.
    """
    df = score_all_checkins(case_id)
    if df.empty:
        raise ValueError(f"No check-in records found for case_id '{case_id}'")

    all_scores = df["dynamic_distress_score"].tolist()


    scores_used = all_scores[-6:] if len(all_scores) >= 6 else all_scores

    slope = compute_trend_slope(scores_used)
    classification = classify_trend(slope, TREND_THRESHOLD)

    return {
        "case_id": case_id,
        "slope": round(slope, 3),
        "classification": classification,
        "scores_used": scores_used
    }

if __name__ == "__main__":
    test_cases = ['ATR-2026-0001', 'ATR-2026-0003', 'ATR-2026-0006']

    print("--- Trend Analysis Verification ---")
    for cid in test_cases:
        res = get_trend_for_case(cid)
        print(f"\nCase ID: {res['case_id']}")
        print(f"  Scores Used: {res['scores_used']}")
        print(f"  Slope: {res['slope']}")
        print(f"  Classification: {res['classification']}")
