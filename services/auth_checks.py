"""
Authentication Checks — 5 parallel checks, no external APIs.
"""
from config import SCAM_KEYWORDS, URGENCY_KEYWORDS, OTP_KEYWORDS, OFFICIAL_NUMBER_PREFIXES


# ── CHECK 1: Contact Verification ─────────────────────────────────────────────

def contact_check(caller_name: str, caller_number: str, contacts: list) -> str:
    """
    Verify caller against saved contacts.
    Returns: 'verified' | 'partial' | 'unverified'
    """
    if not contacts:
        return "unverified"

    normalized = caller_number.replace(" ", "").replace("-", "")
    name_lower = (caller_name or "").lower().strip()

    for contact in contacts:
        c_num = (contact.phone_number or "").replace(" ", "").replace("-", "")
        c_name = (contact.name or "").lower().strip()

        # Exact number match
        if normalized and c_num and (normalized[-9:] == c_num[-9:]):
            if c_name and name_lower and c_name == name_lower:
                return "verified"
            return "partial"

        # Name-only match
        if c_name and name_lower and c_name == name_lower:
            return "partial"

    return "unverified"


# ── CHECK 2: Scam Pattern Detection ────────────────────────────────────────────

def scam_check(transcript_text: str) -> str:
    """
    Check transcript for known scam keywords.
    Returns: 'clean' | 'suspicious' | 'scam'
    """
    text_lower = transcript_text.lower()
    matched = [kw for kw in SCAM_KEYWORDS if kw in text_lower]

    if len(matched) >= 2:
        return "scam"
    elif len(matched) == 1:
        return "suspicious"
    return "clean"


# ── CHECK 3: Spoofing Detection ─────────────────────────────────────────────────

def spoofing_check(caller_number: str, caller_org: str) -> str:
    """
    Heuristic spoofing detection.
    Official orgs use landlines; mobile numbers claiming to be official = suspicious/spoofed.
    Returns: 'genuine' | 'suspicious' | 'spoofed'
    """
    if not caller_org:
        return "genuine"

    official_orgs = [
        "rbi", "trai", "cbi", "sbi", "hdfc", "icici", "income tax",
        "uidai", "police", "electricity board", "tneb", "bescom",
        "customs", "court", "municipality", "government", "ministry",
        "aadhaar", "epf", "provident fund"
    ]

    claims_official = any(org in caller_org.lower() for org in official_orgs)

    if not claims_official:
        return "genuine"

    # Check if the number looks like a mobile (starts with 9, 8, 7, 6)
    digits = caller_number.replace(" ", "").replace("-", "").replace("+91", "").replace("+", "")
    if digits and digits[0] in "6789":
        return "spoofed"  # Official org using mobile = spoofed

    # Check against known official prefixes
    for prefix in OFFICIAL_NUMBER_PREFIXES:
        if caller_number.replace(" ", "").startswith(prefix):
            return "genuine"

    return "suspicious"


# ── CHECK 4: Intent Classification ─────────────────────────────────────────────

INTENT_PATTERNS = {
    "service_appointment": [
        "appointment", "service", "repair", "maintenance", "visit",
        "plumber", "electrician", "engineer", "technician", "inspection",
        "booking", "schedule", "scheduled"
    ],
    "delivery": [
        "delivery", "deliver", "courier", "package", "parcel", "shipment",
        "order", "dispatch", "amazon", "flipkart", "meesho", "swiggy", "zomato"
    ],
    "personal_family": [
        "family", "relative", "cousin", "brother", "sister", "mother", "father",
        "uncle", "aunt", "friend", "personal", "invitation", "function", "wedding",
        "festival", "pongal", "diwali", "eid"
    ],
    "sales_telemarketing": [
        "offer", "discount", "scheme", "insurance", "loan", "credit",
        "investment", "plan", "policy", "subscription", "free", "deal",
        "recharge", "cashback"
    ],
    "official_government": [
        "government", "ministry", "department", "municipal", "tax", "notice",
        "officer", "authority", "official", "certificate", "compliance",
        "survey", "census", "election"
    ],
    "financial": [
        "bank", "account", "transaction", "statement", "loan", "emi",
        "credit card", "debit", "balance", "kyc", "upi", "payment", "fund"
    ],
    "medical": [
        "doctor", "hospital", "clinic", "appointment", "prescription",
        "medicine", "health", "patient", "test", "report", "lab", "nursing"
    ],
    "scam_suspected": [
        "otp", "pin", "password", "arrest", "warrant", "disconnection",
        "blocked", "frozen", "drug", "parcel", "customs", "clearance",
        "rbi", "trai", "uidai", "aadhaar deactivate", "digital arrest",
        "bail", "penalty", "fine immediately"
    ],
}


def intent_classify(reason_text: str, transcript_text: str) -> dict:
    """
    Classify call intent using keyword matching.
    Returns: {"label": str, "confidence": float}
    """
    combined = (reason_text + " " + transcript_text).lower()
    scores = {}

    for intent, keywords in INTENT_PATTERNS.items():
        matched = sum(1 for kw in keywords if kw in combined)
        if matched > 0:
            scores[intent] = matched / len(keywords)

    if not scores:
        return {"label": "unknown", "confidence": 0.0}

    best = max(scores, key=scores.get)
    confidence = min(1.0, scores[best] * 10)  # Scale up

    return {"label": best, "confidence": round(confidence, 2)}


# ── CHECK 5: Urgency Analysis ────────────────────────────────────────────────────

def urgency_check(transcript_text: str) -> dict:
    """
    Score urgency 0–10. Flag if >= 7.
    Returns: {"urgency_score": int, "flagged_phrases": [str], "flagged": bool}
    """
    text_lower = transcript_text.lower()
    flagged = [kw for kw in URGENCY_KEYWORDS if kw.lower() in text_lower]
    otp = [kw for kw in OTP_KEYWORDS if kw.lower() in text_lower]

    score = min(10, len(flagged) * 2 + len(otp) * 3)

    return {
        "urgency_score": score,
        "flagged_phrases": flagged + otp,
        "flagged": score >= 7
    }


# ── Run All Checks ────────────────────────────────────────────────────────────────

def run_all_checks(
    caller_name: str,
    caller_number: str,
    caller_org: str,
    transcript: list,
    contacts: list
) -> dict:
    """
    Run all 5 checks and return a combined result dict.
    """
    transcript_text = " ".join(t.get("text", "") for t in transcript)
    caller_text = " ".join(
        t.get("text", "") for t in transcript if t.get("role") == "caller"
    )

    contact_result = contact_check(caller_name, caller_number, contacts)
    scam_result = scam_check(transcript_text)
    spoofing_result = spoofing_check(caller_number, caller_org)
    intent_result = intent_classify(caller_org or "", transcript_text)
    urgency_result = urgency_check(caller_text)

    return {
        "check_contact": contact_result,
        "check_scam": scam_result,
        "check_spoofing": spoofing_result,
        "intent_label": intent_result["label"],
        "intent_confidence": intent_result["confidence"],
        "check_urgency_score": urgency_result["urgency_score"],
        "urgency_flagged": urgency_result["flagged"],
        "urgency_phrases": urgency_result["flagged_phrases"],
    }
