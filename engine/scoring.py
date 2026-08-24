import os
import sqlite3
import pandas as pd
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

_analyzer = SentimentIntensityAnalyzer()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "db", "victims.db")

def get_structured_score(row) -> int | None:
    """
    Takes a database row (or dict-like object/pandas Series) with a structured_score field,
    and returns that value as an integer. If structured_score is None or NaN, returns None.
    """
    if isinstance(row, dict):
        val = row.get("structured_score")
    else:
        val = getattr(row, "structured_score", None) if hasattr(row, "structured_score") else row["structured_score"]
        
    if val is None or pd.isna(val) or str(val).strip() == "" or str(val).upper() == "NONE":
        return None
    return int(val)

def get_sentiment_distress(free_text: str | None) -> float:
    """
    Takes a free_text string, runs it through VADER's SentimentIntensityAnalyzer,
    and gets the compound score (-1 to +1). Rescales this linearly:
    distress = (1 - compound) / 2 * 10.
    If free_text is empty or None, returns 0.
    """
    if not free_text or not str(free_text).strip():
        return 0.0
    
    scores = _analyzer.polarity_scores(str(free_text))
    compound = scores.get("compound", 0.0)
    
    distress = ((1.0 - compound) / 2.0) * 10.0
    return round(distress, 2)

def compute_dynamic_distress_score(row) -> float | None:
    """
    Calls get_structured_score(row) and get_sentiment_distress(free_text),
    adds them together, and caps the result at a maximum of 35 using min().
    If get_structured_score returns None (missed check-in), returns None.
    """
    struct_score = get_structured_score(row)
    if struct_score is None:
        return None
    
    if isinstance(row, dict):
        free_text = row.get("free_text", "")
    else:
        free_text = getattr(row, "free_text", "") if hasattr(row, "free_text") else row["free_text"]
        
    sent_distress = get_sentiment_distress(free_text)
    total_score = float(struct_score) + sent_distress
    
    capped_score = min(35.0, total_score)
    return round(capped_score, 2)

def score_all_checkins(case_id: str) -> pd.DataFrame:
    """
    Connects to db/victims.db, selects all rows from checkins table for matching case_id
    ordered by week_number ascending, loads into pandas DataFrame, adds dynamic_distress_score column,
    and returns the DataFrame.
    """
    conn = sqlite3.connect(DB_PATH)
    query = "SELECT * FROM checkins WHERE case_id = ? ORDER BY week_number ASC;"
    df = pd.read_sql_query(query, conn, params=(case_id,))
    conn.close()
    
    df["dynamic_distress_score"] = df.apply(compute_dynamic_distress_score, axis=1)
    return df

if __name__ == "__main__":
    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 1000)
    
    print("--- Scoring All Check-ins for case_id ATR-2026-0001 ---")
    result_df = score_all_checkins("ATR-2026-0001")
    print(result_df)
