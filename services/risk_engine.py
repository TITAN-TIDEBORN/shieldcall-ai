"""
Risk Engine — computes risk score 0-100 for a screened call.
No external APIs. Pure heuristic + keyword analysis.
"""
from config import (
    SCAM_KEYWORDS, URGENCY_KEYWORDS, OTP_KEYWORDS, PAYMENT_KEYWORDS,
    OFFICIAL_NUMBER_PREFIXES
)


SCAM_PATTERN_SIGNALS = {
    "rbi digital wallet": "Caller mentioned 'RBI Digital Wallet' — classic scam phrase",
    "trai disconnection": "Caller mentioned 'TRAI disconnection' — telecom scam pattern",
    "kyc verification": "Caller requested KYC verification — common fraud tactic",
    "courier with drugs": "Caller mentioned courier with drugs — courier scam pattern",
    "arrest warrant": "Caller mentioned arrest warrant — extortion/fear scam",
    "cbi officer": "Caller claims to be CBI officer — authority impersonation",
    "income tax notice": "Caller mentioned income tax notice — tax scam",
    "aadhaar deactivate": "Caller threatened Aadhaar deactivation — identity scam",
    "uidai": "Caller mentioned UIDAI — Aadhaar phishing pattern",
    "electricity cut": "Caller threatened electricity disconnection — utility scam",
    "customs clearance": "Caller mentioned customs clearance — courier extortion",
    "digital arrest": "Caller mentioned 'digital arrest' — police impersonation scam",
    "money laundering": "Caller mentioned money laundering charges — fear scam",
    "drug parcel": "Caller mentioned drug parcel — courier scam variant",
    "narcotics": "Caller mentioned narcotics — fear/extortion scam",
    "press 1 to speak": "Automated scam IVR pattern detected",
    "press 9": "Automated scam IVR pattern detected",
    "stay on the line or you will be arrested": "Extreme fear tactic — scam call",
    "your account will be frozen": "Bank account threat — phishing pattern",
}


def compute_risk_score(
    transcript: list,
    extracted: dict,
    caller_profile: dict,
    contacts: list = None
) -> dict:
    """
    Compute a risk score (0–100) for a screened call.

    Args:
        transcript: List of {role, text, timestamp} dicts
        extracted: Dict of extracted caller info from AI agent
        caller_profile: The caller profile dict from simulator
        contacts: List of Contact objects from DB

    Returns:
        {"score": int, "level": str, "signals": [str]}
    """
    score = 10  # Base score
    signals = []
    contacts = contacts or []

    # Combine all text for analysis
    all_text = " ".join(
        turn.get("text", "") for turn in transcript
        if turn.get("role") == "caller"
    ).lower()

    full_text = " ".join(
        turn.get("text", "") for turn in transcript
    ).lower()

    caller_name = extracted.get("caller_name", "") or caller_profile.get("name", "")
    caller_number = caller_profile.get("number", "")
    caller_org = extracted.get("organization", "") or caller_profile.get("org", "") or ""

    # ── NEGATIVE SIGNALS (increase risk) ─────────────────────────────────────

    # Urgency / pressure language
    urgency_found = [kw for kw in URGENCY_KEYWORDS if kw.lower() in full_text]
    if urgency_found:
        score += 15
        signals.append(f"Urgency language detected: {', '.join(urgency_found[:3])}")

    # OTP / password requests
    otp_found = [kw for kw in OTP_KEYWORDS if kw.lower() in all_text]
    if otp_found:
        score += 30
        signals.append(f"Sensitive data requested: {', '.join(otp_found[:3])}")

    # Payment requests
    payment_found = [kw for kw in PAYMENT_KEYWORDS if kw.lower() in all_text]
    if payment_found:
        score += 25
        signals.append(f"Payment/transfer requested: {', '.join(payment_found[:3])}")

    # Known scam patterns
    for pattern, signal_msg in SCAM_PATTERN_SIGNALS.items():
        if pattern in full_text:
            score += 35
            signals.append(signal_msg)
            break  # Only count once to cap the penalty

    # Caller cannot provide verifiable identity
    if not extracted.get("caller_name") and not caller_profile.get("name", "").lower().startswith("unknown") is False:
        score += 20
        signals.append("Caller could not provide verifiable identity")

    # Claims official role but cannot provide employee ID
    official_orgs = ["rbi", "trai", "cbi", "sbi", "hdfc", "income tax", "uidai",
                     "police", "electricity board", "tneb", "customs", "court"]
    claims_official = any(org in caller_org.lower() for org in official_orgs)
    if claims_official:
        score += 20
        signals.append(f"Claims official/government role: '{caller_org}'")

    # Number not in contacts
    contact_numbers = [c.phone_number.replace(" ", "").replace("-", "") for c in contacts]
    normalized_caller = caller_number.replace(" ", "").replace("-", "")
    in_contacts = any(normalized_caller.endswith(cn[-7:]) for cn in contact_numbers if len(cn) >= 7)

    if not in_contacts:
        score += 10
        signals.append("Caller number not found in saved contacts")

    # Spoofing heuristic: claims official org but uses mobile number
    if claims_official and caller_number.startswith("+91 9"):
        score += 25
        signals.append("Official org claimed but caller uses mobile number — potential spoofing")

    # ── POSITIVE SIGNALS (decrease risk) ─────────────────────────────────────

    # In saved contacts
    contact_names = [c.name.lower() for c in contacts]
    if in_contacts or (caller_name.lower() in contact_names):
        score -= 30
        signals.append("✓ Caller matched saved contact")

    # Verifiable reference mentioned
    reference_keywords = ["order id", "order number", "appointment", "booking", "reference",
                          "invoice", "case number", "job id", "ticket"]
    if any(kw in full_text for kw in reference_keywords):
        score -= 15
        signals.append("✓ Caller provided verifiable reference number")

    # Calm tone — no pressure
    if not urgency_found and not otp_found and not payment_found:
        score -= 10
        signals.append("✓ Calm, non-pressuring tone detected")

    # Known legitimate caller profile
    if caller_profile.get("risk_hint") == "low":
        score -= 15
        signals.append("✓ Caller profile matches low-risk pattern")

    # Clamp to 0–100
    score = max(0, min(100, score))

    # Determine level
    if score < 40:
        level = "low"
    elif score < 70:
        level = "medium"
    else:
        level = "high"

    return {
        "score": score,
        "level": level,
        "signals": list(dict.fromkeys(signals))  # deduplicate
    }
