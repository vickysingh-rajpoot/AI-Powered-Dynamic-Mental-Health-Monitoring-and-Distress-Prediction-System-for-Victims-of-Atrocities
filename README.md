# Dynamic Mental Health Monitoring and Distress Prediction

An explainable, local Streamlit prototype for monitoring the changing well-being of victims of atrocities. It combines questionnaire responses, free-text sentiment, distress trends, threat-language detection, case severity, and missed check-ins to help counsellors prioritize cases.

> **Important:** This is a screening-round prototype using synthetic/demo data. It is not a clinical diagnosis, a replacement for a counsellor, or a real emergency-dispatch service. The SOS feature generates a notice on screen; it does not contact police or any authority.

## 1. What the Project Does

The system has two user-facing pages:

1. **Victim Check-in:** Select a demo case, answer four 1-to-5 questions, optionally enter a free-text update, and submit a weekly check-in.
2. **Counsellor Dashboard:** View ranked cases, risk factors, distress charts, geography filters, interventions, and the High Risk SOS notice generator.

The complete flow is:

```text
Victim input
    -> structured questionnaire score
    -> free-text sentiment distress score
    -> dynamic distress score for this check-in
    -> recent-history trend
    -> threat and disengagement checks
    -> composite 0-100 risk score
    -> Low / Moderate / High classification
    -> dashboard ranking, recommendations, and optional SOS notice
```

## 2. Start the Application

### Windows

```cmd
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python data\generate_synthetic_data.py
streamlit run app.py
```

Open `http://localhost:8501`.

The database is created automatically if it does not exist. Running the data generator again deletes and recreates the local SQLite database and CSV with the original demo data.

## 3. Understand the Data

The SQLite table is `checkins`. Each row is one weekly record and contains:

| Field | Meaning |
|---|---|
| `case_id` | Victim/case identifier, such as `ATR-2026-0007` |
| `category` | Crime or case category |
| `category_weight` | Severity value from 1 to 5 |
| `channel` | Chatbot, SMS, or IVRS |
| `language` | Preferred language |
| `state`, `district` | Geographic metadata |
| `week_number` | Sequential check-in number |
| `checkin_date` | Date stored for that check-in |
| `structured_score` | Questionnaire distress score from 0 to 27 |
| `free_text` | Optional victim update |
| `responded` | `1` for response, `0` for missed check-in |
| `trajectory_type` | Synthetic-data label or `live_submission`; risk uses calculated history, not this label |

The generator creates 10 cases and 7 weeks per case. Two synthetic cases miss weeks 6 and 7. Live submissions add new rows to the same case and database.

## 4. Victim Check-in Page

Select a case ID. The page loads its category, channel, language, state, district, and next week number.

### Questionnaire inputs

Each slider accepts integers from 1 to 5:

| Question | Low value | High value | Distress calculation |
|---|---|---|---|
| Anxiety | Very calm | Extremely anxious | `(anxiety - 1) / 4 * 7` |
| Sleep | Terrible/sleepless | Peaceful/restful | `(5 - sleep) / 4 * 6.5` |
| Hopefulness | Very hopeful | Completely hopeless | `(hope - 1) / 4 * 6.5` |
| Mood | Very low/depressed | Good/cheerful | `(5 - mood) / 4 * 7` |

The four values are added and rounded:

```text
structured_score = round(anxiety distress + sleep distress + hope distress + mood distress)
```

The final structured range is **0 to 27**.

### Structured-score examples

| Anxiety | Sleep | Hope | Mood | Structured result |
|---:|---:|---:|---:|---:|
| 1 | 5 | 1 | 5 | 0 |
| 5 | 1 | 5 | 1 | 27 |
| 3 | 3 | 3 | 3 | 14 |
| 5 | 5 | 1 | 5 | 7 |
| 1 | 1 | 1 | 5 | 6 |
| 1 | 5 | 5 | 5 | 6 |
| 1 | 5 | 1 | 1 | 7 |

### Free-text sentiment

VADER analyzes the optional text. Its compound sentiment value ranges from -1 to +1 and is converted to distress from 0 to 10:

```text
sentiment_distress = ((1 - compound_sentiment) / 2) * 10
```

Blank or whitespace-only text produces `0.0`.

The check-in's dynamic score is:

```text
dynamic_distress_score = min(35, structured_score + sentiment_distress)
```

After submission, the page displays the structured score, sentiment distress, and dynamic distress score. The row is inserted into SQLite with `responded = 1`.

## 5. Why One Check-in Usually Does Not Change the Ranking

This is the most important concept for a new user:

> A check-in creates one new distress value, but the case ranking is based on the case's recent history and four risk factors. A single submission may change the slope slightly, but it does not automatically make a case High Risk.

The trend engine uses the **latest six check-in rows**. It needs at least two valid distress scores to calculate a slope. With only one valid score, the slope is `0.0` and the trend is Stable.

With an existing seven-week case, submitting one new check-in replaces the oldest record in the six-record trend window. Therefore, one submission can affect the trend, but several consistently high or low submissions make the direction clear. For a convincing demo, use at least three consecutive high-distress submissions and refresh the dashboard after each one.

The code does not require exactly three or four check-ins. The practical rule is:

```text
1 valid score   -> no meaningful slope; Stable
2 valid scores  -> slope is possible
3+ consistent recent scores -> trend change is easier to observe
up to 6 rows    -> included in the trend calculation
```

## 6. Trend Classification

The engine fits a straight line to the latest six valid dynamic scores. The slope threshold is `0.8`:

```text
slope >  0.8  -> Worsening
slope < -0.8  -> Improving
otherwise     -> Stable
```

Boundary behavior is exact:

| Slope | Result |
|---:|---|
| `0.799` | Stable |
| `0.8` | Stable |
| `0.801` | Worsening |
| `-0.799` | Stable |
| `-0.8` | Stable |
| `-0.801` | Improving |

## 7. Composite Risk Score

The dashboard calculates four contributions:

| Factor | Rule | Points |
|---|---|---:|
| Trend | Worsening | 40 |
| Trend | Stable | 15 |
| Trend | Improving | 0 |
| Category | `category_weight * 5` | 5 to 25 |
| Threat | Keyword in either latest two texts | 20 |
| Disengagement | Both latest rows have `responded = 0` | 15 |

```text
composite_score = trend points + category points + threat points + disengagement points
```

The score is capped at 100.

Classification:

```text
score >= 60 -> High Risk
score >= 35 -> Moderate Risk
score <  35 -> Low Risk
```

### Worked examples

**Low Risk example**

```text
Improving trend = 0
Category weight 3 = 15
No threat = 0
No disengagement = 0
Total = 15 -> Low Risk
```

**Moderate Risk example**

```text
Stable trend = 15
Category weight 5 = 25
No threat = 0
No disengagement = 0
Total = 40 -> Moderate Risk
```

**High Risk example**

```text
Worsening trend = 40
Category weight 4 = 20
Threat detected = 20
No disengagement = 0
Total = 80 -> High Risk
```

## 8. Threat and Disengagement Rules

The latest two free-text records are scanned case-insensitively for these substrings:

```text
threat, threatened, followed, scared, afraid, unsafe,
warned, watched, intimidate, withdraw the case
```

Threat text older than the latest two records is not counted.

Disengagement is true only when the two most recent database rows both have `responded = 0`. The synthetic cases `ATR-2026-0005` and `ATR-2026-0009` demonstrate this behavior.

## 9. Intervention Recommendations

Recommendations are rule-based and can be combined:

| Trigger | Recommendation |
|---|---|
| Threat contribution greater than 0 | Immediate Witness Protection & Relocation |
| Disengagement contribution greater than 0 | Field Welfare Officer Home Visit |
| Worsening trend | Urgent Psychiatric Trauma Care |
| Category contribution at least 20 | DLSA Legal Aid & Financial Compensation |
| Moderate score with no earlier trigger | Scheduled Counselling |
| Low score | Continue Monitoring |

Recommendations appear in priority order. The dashboard displays the title, urgency, action, and responsible authority.

The Counselling rule is implemented, but with normal category weights 1-5 it is rarely reachable because category and stable-trend points already produce a Moderate score only when the category rule also triggers. This is a known prototype behavior.

## 10. Geographic Dashboard Filters

The dashboard supports:

1. **National Overview:** all cases.
2. **State Level:** cases belonging to the selected state.
3. **District Level:** cases belonging to the selected district within the selected state.

The selectors are populated from valid case metadata. Current demo examples:

| Selection | Expected cases |
|---|---:|
| National Overview | 10 |
| Maharashtra | 2 |
| Uttar Pradesh | 2 |
| Maharashtra -> Pune | `ATR-2026-0001` |
| Maharashtra -> Nagpur | `ATR-2026-0003` |
| Uttar Pradesh -> Lucknow | `ATR-2026-0002` |
| Uttar Pradesh -> Varanasi | `ATR-2026-0007` |

The dashboard selects one latest complete metadata row per case, preventing incomplete live submissions from duplicating or hiding a case.

## 11. SOS Feature

The SOS section is visible for every selected case, but the action differs by classification:

- **High Risk:** Dispatch Emergency SOS Notice button appears.
- **Moderate Risk:** warning explains that SOS activates only for High Risk.
- **Low Risk:** regular monitoring message appears.

Clicking the High Risk button generates a formatted notice containing:

- Case ID
- Category
- State and district
- Composite score
- Trend
- Threat flag
- Disengagement flag
- Recommended authority actions

The notice can be downloaded as a text file. It is not sent to an external authority.

## 12. Demo Case Reference

These cases are useful for a presentation because each demonstrates a different behavior:

| Case | Current result | Demonstrates |
|---|---|---|
| `ATR-2026-0007` | High, score 60 | Worsening trend, psychiatric care, SOS |
| `ATR-2026-0005` | Moderate, score 55 | Two missed check-ins, field visit |
| `ATR-2026-0009` | Moderate, score 55 | Another disengaged case |
| `ATR-2026-0003` | Low, score 20 | Improving trend |
| `ATR-2026-0006` | Moderate, score 35 | Stable trend and boundary score |
| `ATR-2026-0008` | Low, score 30 | Low-risk monitoring and Gujarat geography |
| `ATR-2026-0004` | Moderate, score 40 | High distress but stable trend |
| `ATR-2026-0010` | Moderate, score 35 | Exact Moderate boundary |

## 13. Recommended Presentation Walkthrough

### Step 1: Explain the problem

Victims may experience increasing distress, threats, social isolation, or forced silence during long legal and rehabilitation processes. A single score is not enough, so this prototype tracks change over time.

### Step 2: Show a normal check-in

Select `ATR-2026-0008` and enter:

```text
Anxiety: 3
Sleep: 3
Hopefulness: 3
Mood: 3
Free text: Feeling okay and manageable this week.
```

Explain that the page stores the response and immediately shows its three scores.

### Step 3: Show a high-distress check-in

Select a case and enter:

```text
Anxiety: 5
Sleep: 1
Hopefulness: 5
Mood: 1
Free text: I am terrified and unsafe. Someone followed me and warned me to withdraw the case.
```

Explain:

```text
Maximum questionnaire distress = 27
Threat keywords = unsafe, followed, warned, withdraw the case
Dynamic score = questionnaire score + sentiment score, capped at 35
```

Submit this type of response three times on the same case, refreshing the dashboard after each submission. Consistent recent high scores make a worsening trend more likely. Do not promise that exactly three submissions always create High Risk; the regression slope and previous six records determine the result.

### Step 4: Show the dashboard

Point out:

1. Ranked case table.
2. High, Moderate, and Low counts.
3. Geographic metadata.
4. Distress trajectory chart.
5. Risk contribution breakdown.
6. Explainable rationale.

### Step 5: Demonstrate the three risk categories

Select:

- `ATR-2026-0007` for High Risk and SOS.
- `ATR-2026-0006` for Moderate Risk at score 35.
- `ATR-2026-0008` for Low Risk.

### Step 6: Demonstrate disengagement

Select `ATR-2026-0005`. Explain that weeks 6 and 7 have `responded = 0`, adding 15 risk points and triggering a Field Welfare Officer Home Visit recommendation.

### Step 7: Demonstrate geography

Use National Overview, then State Level -> Maharashtra, then District Level -> Maharashtra -> Pune. Show that the displayed case count changes with the selected administrative level.

### Step 8: Demonstrate SOS

Select `ATR-2026-0007`, click the SOS button, and show the generated notice and download button. State clearly that the prototype generates a notice locally and does not dispatch a real emergency response.

## 14. Suggested Presentation Explanation

Use this short explanation:

> “The victim submits a weekly questionnaire and an optional text update. The questionnaire becomes a structured distress score from 0 to 27. VADER converts the text into a sentiment distress score from 0 to 10, and together they form a dynamic score capped at 35. The system then examines the latest six check-ins to calculate whether distress is worsening, stable, or improving. It combines that trend with case severity, recent threat language, and two consecutive missed check-ins to produce a transparent 0-to-100 risk score. The counsellor dashboard ranks cases, filters them by state and district, explains every score, recommends actions, and generates a local SOS notice for High Risk cases.”

## 15. Project Structure

```text
app.py                         Landing page and database initialization
pages/1_Victim_Checkin.py     Victim questionnaire and database insert
pages/2_Counsellor_Dashboard.py Dashboard, charts, filters, interventions, SOS
engine/scoring.py              Structured, VADER, and dynamic distress scores
engine/trend.py                Recent-history slope and trend classification
engine/disengagement.py        Missed-check-in detection
engine/risk.py                 Threat detection and composite risk
engine/interventions.py        Recommendation and SOS notice rules
data/generate_synthetic_data.py Synthetic SQLite and CSV data generator
data/synthetic_checkins.csv    Exported demo records
db/victims.db                  Local SQLite database generated at runtime
requirements.txt               Python dependencies
```

## 16. Current Prototype Limitations

- Synthetic data is used for demonstration.
- The system does not diagnose mental-health conditions.
- There is no login authentication or role-based authorization.
- There is no real external police, hospital, helpline, or emergency API.
- SOS creates text only.
- Threat detection scans only the latest two text records.
- A single check-in does not guarantee a risk-category change.
- Live submissions permanently add rows until the database is regenerated.
- The database is local SQLite and is not configured as a production privacy system.

These are appropriate future enhancements for a production version.
