import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "db", "victims.db")

def check_disengagement(case_id: str) -> dict:
    """
    Connects to db/victims.db, selects all rows from checkins for case_id ordered by week_number descending.
    Looks at the 2 most recent rows only. Returns dict with exact keys:
    - case_id
    - disengaged (True if both of 2 most recent check-ins have responded == 0 and total check-ins >= 2)
    - missed_weeks (list of week_number values across ALL check-ins where responded == 0)
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()


    query_all = "SELECT week_number, responded FROM checkins WHERE case_id = ? ORDER BY week_number DESC;"
    cursor.execute(query_all, (case_id,))
    rows = cursor.fetchall()
    conn.close()



    missed_weeks = sorted([r[0] for r in rows if r[1] == 0])


    if len(rows) < 2:
        is_disengaged = False
    else:
        most_recent_two = rows[:2]
        is_disengaged = all(r[1] == 0 for r in most_recent_two)

    return {
        "case_id": case_id,
        "disengaged": is_disengaged,
        "missed_weeks": missed_weeks
    }

if __name__ == "__main__":
    test_cases = ['ATR-2026-0005', 'ATR-2026-0009', 'ATR-2026-0001']

    print("--- Disengagement Detection Verification ---")
    for cid in test_cases:
        res = check_disengagement(cid)
        print(f"\nCase ID: {res['case_id']}")
        print(f"  Disengaged: {res['disengaged']}")
        print(f"  Missed Weeks: {res['missed_weeks']}")
