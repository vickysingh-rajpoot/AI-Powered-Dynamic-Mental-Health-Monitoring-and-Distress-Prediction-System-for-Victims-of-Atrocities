"""
engine/interventions.py
-----------------------
Rule-based Automated Intervention Recommender Engine.
Maps computed risk factors to specific government-mandated welfare
actions under the SC/ST (Prevention of Atrocities) Act, 1989.
"""

import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from engine.risk import explain_risk

# ---------------------------------------------------------------------------
# Intervention Rule Definitions
# ---------------------------------------------------------------------------

INTERVENTIONS = {
    "witness_protection": {
        "icon": "🛡️",
        "title": "Immediate Witness Protection & Relocation",
        "action": (
            "Initiate Witness Protection Order under SC/ST POA Act Sec 15A. "
            "Alert District Magistrate (DM) and Superintendent of Police (SSP) "
            "for emergency safehouse relocation within 24 hours."
        ),
        "authority": "District Magistrate + SSP",
        "urgency": "CRITICAL"
    },
    "psychiatric_care": {
        "icon": "🧠",
        "title": "Urgent Psychiatric Trauma Care",
        "action": (
            "Dispatch District Trauma Counsellor within 48 hours. "
            "Refer to Government Hospital Psychiatry Department for clinical assessment. "
            "Initiate weekly tele-counselling sessions via NHAA (14566)."
        ),
        "authority": "Chief Medical Officer (CMO)",
        "urgency": "HIGH"
    },
    "field_visit": {
        "icon": "📞",
        "title": "NHAA (14566) Field Welfare Officer Home Visit",
        "action": (
            "Victim has missed 2+ consecutive check-ins. "
            "Dispatch District Welfare Officer for immediate home visit "
            "to assess safety, well-being, and forced silence risks."
        ),
        "authority": "District Welfare Officer",
        "urgency": "HIGH"
    },
    "legal_aid": {
        "icon": "⚖️",
        "title": "DLSA Legal Aid & Expedited Financial Compensation",
        "action": (
            "Assign District Legal Services Authority (DLSA) advocate for immediate "
            "case follow-up. File for expedited relief fund disbursement under "
            "SC/ST POA Act Schedule Relief Norms. Prioritise court hearing schedule."
        ),
        "authority": "District Legal Services Authority (DLSA)",
        "urgency": "MODERATE"
    },
    "counselling": {
        "icon": "💬",
        "title": "Scheduled Counselling & Psychosocial Support",
        "action": (
            "Schedule bi-weekly counselling sessions with trained psychosocial support "
            "worker. Enroll victim in peer support group under State Victim Assistance Fund. "
            "Enable monthly NHAA (14566) welfare call check-in."
        ),
        "authority": "District Counsellor",
        "urgency": "MODERATE"
    },
    "monitor_only": {
        "icon": "👁️",
        "title": "Continue Monitoring — Next Check-in in 7 Days",
        "action": (
            "Current distress level is stable and within acceptable threshold. "
            "Continue weekly automated check-in monitoring. "
            "Re-evaluate if distress trend changes in next check-in cycle."
        ),
        "authority": "Automated System",
        "urgency": "LOW"
    }
}

URGENCY_COLOR = {
    "CRITICAL": "#DC2626",   # red
    "HIGH":     "#EA580C",   # orange
    "MODERATE": "#D97706",   # amber
    "LOW":      "#16A34A"    # green
}


def generate_interventions(case_id: str) -> list[dict]:
    """
    Calls explain_risk(case_id) and maps each flagged factor to one or more
    specific intervention recommendations. Returns an ordered list of
    intervention dicts (most urgent first).
    """
    risk_data = explain_risk(case_id)
    factors   = risk_data["factors"]
    score     = risk_data["composite_score"]

    selected = []

    # Rule 1: Threat keyword detected → Witness Protection (highest priority)
    if factors["threat_contribution"] > 0:
        selected.append(INTERVENTIONS["witness_protection"])

    # Rule 2: Disengaged (missed 2+ check-ins) → Field Home Visit
    if factors["disengagement_contribution"] > 0:
        selected.append(INTERVENTIONS["field_visit"])

    # Rule 3: Worsening trend → Psychiatric Care
    if factors["trend_contribution"] >= 40:
        selected.append(INTERVENTIONS["psychiatric_care"])

    # Rule 4: High category severity (weight >= 4) → Legal Aid
    if factors["category_contribution"] >= 20:
        selected.append(INTERVENTIONS["legal_aid"])

    # Rule 5: Moderate risk but no other triggers → Counselling
    if score >= 35 and not selected:
        selected.append(INTERVENTIONS["counselling"])

    # Rule 6: Low risk → Monitor only
    if score < 35:
        selected.append(INTERVENTIONS["monitor_only"])

    return selected


def get_sos_notice(case_id: str, state: str, district: str, category: str) -> str:
    """
    Generates a formatted Emergency SOS Notice for the District Magistrate
    and SSP, given the risk data for the case.
    """
    risk_data = explain_risk(case_id)
    score     = risk_data["composite_score"]
    factors   = risk_data["factors"]

    threat_flag     = "YES ⚠️" if factors["threat_contribution"] > 0 else "No"
    disengage_flag  = "YES ⚠️" if factors["disengagement_contribution"] > 0 else "No"
    trend_class     = "WORSENING 🔴" if factors["trend_contribution"] >= 40 else (
                      "STABLE 🟡"   if factors["trend_contribution"] > 0   else "IMPROVING 🟢")

    notice = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚨 EMERGENCY SOS NOTICE — CONFIDENTIAL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Issued By   : NHAA AI Monitoring System (SIH26094)
Date        : {__import__('datetime').datetime.now().strftime('%d %B %Y, %H:%M IST')}

CASE DETAILS
────────────
Case ID     : {case_id}
Category    : {category}
Location    : {district}, {state}

RISK ASSESSMENT
────────────────
Composite Risk Score  : {score} / 100  ({'🔴 HIGH RISK' if score >= 60 else '🟡 MODERATE' if score >= 35 else '🟢 LOW'})
Distress Trend        : {trend_class}
Threat Keywords Found : {threat_flag}
Disengagement Flag    : {disengage_flag}

RECOMMENDED IMMEDIATE ACTIONS
───────────────────────────────
1. Issue Witness Protection Order under SC/ST POA Act Sec 15A
2. Notify District Magistrate ({district}) for emergency intervention
3. Deploy SSP rapid response team for victim safety assessment
4. Initiate emergency safehouse relocation if physical threat confirmed

AUTHORITY ESCALATION
─────────────────────
Primary   : District Magistrate, {district}
Secondary : Superintendent of Police (SSP), {district}
Tertiary  : State Welfare Commissioner, {state}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
This notice is system-generated and confidential.
For NHAA helpline: 14566
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    return notice.strip()
