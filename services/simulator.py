"""
Call Simulator Engine — generates realistic fake calls and runs the full pipeline.
Contains all 20 caller profiles.
"""
import json
import random
import asyncio
from datetime import datetime
from database.db import SessionLocal
from database.models import Call, Contact
from services.ai_agent import run_screening_conversation
from services.risk_engine import compute_risk_score
from services.auth_checks import run_all_checks
from services.language import detect_language
from ws.ws_manager import manager

CALLER_PROFILES = [
    # ── LEGITIMATE ───────────────────────────────────────────────────────────
    {
        "id": 1, "name": "Suresh Kumar", "number": "+91 94440 11234",
        "org": "Suresh Plumbing Services", "language": "Tamil",
        "reason": "Confirm plumbing appointment tomorrow 10 AM",
        "risk_hint": "low", "script_hint": "Polite, mentions appointment date clearly, has work order number"
    },
    {
        "id": 2, "name": "Dr. Priya Clinic", "number": "+91 98765 00100",
        "org": "Priya Nursing Home", "language": "English",
        "reason": "Remind about Friday 3 PM appointment, ask about allergies",
        "risk_hint": "low", "script_hint": "Professional, mentions patient name and appointment reference"
    },
    {
        "id": 3, "name": "Amazon Delivery", "number": "+91 1800 300 900",
        "org": "Amazon Logistics", "language": "Hindi",
        "reason": "Package out for delivery, need OTP to hand over",
        "risk_hint": "low", "script_hint": "Reads out order ID, asks for delivery OTP only (legitimate)"
    },
    {
        "id": 4, "name": "Ravi (cousin)", "number": "+91 77001 55443",
        "org": None, "language": "Tamil",
        "reason": "Calling to confirm attending family function Saturday",
        "risk_hint": "low", "script_hint": "Casual, mentions family names, relaxed tone, asks about food arrangements"
    },
    {
        "id": 5, "name": "St. Joseph School", "number": "+91 0431 2345678",
        "org": "St. Joseph Matric School", "language": "English",
        "reason": "Parent-teacher meeting scheduled for next week",
        "risk_hint": "low", "script_hint": "Official school tone, mentions child's name and class"
    },
    {
        "id": 6, "name": "HDFC Bank Official", "number": "+91 1800 202 6161",
        "org": "HDFC Bank", "language": "English",
        "reason": "Credit card statement query follow-up",
        "risk_hint": "low", "script_hint": "Does NOT ask for OTP or PIN, only asks to visit branch"
    },
    {
        "id": 7, "name": "Meena Aunty", "number": "+91 98400 77612",
        "org": None, "language": "Tamil",
        "reason": "Just calling to check in, invite for Pongal celebration",
        "risk_hint": "low", "script_hint": "Very casual, emotional, mentions family events and food"
    },
    {
        "id": 8, "name": "TCS HR Recruiter", "number": "+91 44 6676 9999",
        "org": "Tata Consultancy Services", "language": "English",
        "reason": "Interview scheduled for Monday, calling to confirm attendance",
        "risk_hint": "low", "script_hint": "Mentions job portal application reference number, professional tone"
    },
    # ── SUSPICIOUS ───────────────────────────────────────────────────────────
    {
        "id": 9, "name": "Unknown Sales", "number": "+91 80001 99234",
        "org": "Vague — financial services", "language": "Hindi",
        "reason": "Pushing insurance product, won't name the company",
        "risk_hint": "medium", "script_hint": "Deflects when asked company name, keeps pushing, won't provide employee ID"
    },
    {
        "id": 10, "name": "Survey Caller", "number": "+91 70003 11122",
        "org": "Government survey (unspecified)", "language": "Tamil",
        "reason": "Claiming to do government housing survey, asks for Aadhaar",
        "risk_hint": "medium", "script_hint": "Vague about which department, asks for identity documents"
    },
    {
        "id": 11, "name": "Unknown", "number": "+91 90009 44312",
        "org": None, "language": "English",
        "reason": "Property inquiry, asking if anyone is home regularly",
        "risk_hint": "medium", "script_hint": "Evasive, won't state full reason, asks personal questions about schedule"
    },
    {
        "id": 12, "name": "Reliance Jio Offer", "number": "+91 98998 00123",
        "org": "Claims to be Jio", "language": "Hindi",
        "reason": "Free recharge offer, needs mobile number confirmation",
        "risk_hint": "medium", "script_hint": "Offer sounds too good, asks to confirm personal details, slightly pressuring"
    },
    # ── SCAM ─────────────────────────────────────────────────────────────────
    {
        "id": 13, "name": "Unknown", "number": "+91 99900 00001",
        "org": "Claims: RBI Digital Wallet", "language": "Hindi",
        "reason": "Your digital wallet will be blocked, need OTP to verify KYC",
        "risk_hint": "high",
        "script_hint": "Uses RBI name, urgency, asks for OTP, threatens account blocking. Say: 'Your KYC verification is pending. Share the OTP received on your number immediately or your RBI digital wallet will be blocked within 2 hours.'"
    },
    {
        "id": 14, "name": "Unknown", "number": "+91 88800 12399",
        "org": "Claims: TRAI", "language": "English",
        "reason": "Your mobile number will be disconnected in 2 hours for illegal activity",
        "risk_hint": "high",
        "script_hint": "Legal threat, asks to press 9 to speak to officer. Say: 'This is TRAI calling. Your mobile number has been used for illegal activities. It will be disconnected within 2 hours. Press 9 to speak to our officer.'"
    },
    {
        "id": 15, "name": "Unknown", "number": "+91 70070 55566",
        "org": "Claims: FedEx Courier", "language": "English",
        "reason": "Package detained at customs containing drugs in your name",
        "risk_hint": "high",
        "script_hint": "Classic courier scam, fear tactics. Say: 'We have a parcel in your name at customs. It contains drugs. To avoid arrest, you must pay a clearance fee immediately.'"
    },
    {
        "id": 16, "name": "Unknown", "number": "+91 77007 23344",
        "org": "Claims: TNEB Electricity Board", "language": "Tamil",
        "reason": "Electricity will be disconnected in 2 hours, pay ₹3200 now",
        "risk_hint": "high",
        "script_hint": "Utility scam, urgent payment request. Say: 'TNEB-இல் இருந்து அழைக்கிறோம். உங்கள் மின்சாரம் 2 மணி நேரத்தில் துண்டிக்கப்படும். ₹3200 உடனே செலுத்துங்கள்.'"
    },
    {
        "id": 17, "name": "Unknown", "number": "+91 98001 77123",
        "org": "Claims: CBI/Police", "language": "Hindi",
        "reason": "Arrest warrant issued in your name for money laundering",
        "risk_hint": "high",
        "script_hint": "Fear + authority. Say: 'Main CBI se bol raha hoon. Aapke naam par money laundering ka arrest warrant nikla hai. Abhi line par rahein warna aapko arrest kiya jayega.'"
    },
    {
        "id": 18, "name": "Unknown", "number": "+91 63006 12900",
        "org": "Claims: SBI Bank", "language": "English",
        "reason": "Your account will be frozen, verify by sharing OTP",
        "risk_hint": "high",
        "script_hint": "Phishing. Say: 'This is SBI Bank. Your account has suspicious activity and will be frozen. Please share the OTP sent to your number to verify your identity immediately.'"
    },
    {
        "id": 19, "name": "Unknown", "number": "+91 80808 55100",
        "org": "Claims: Income Tax Dept", "language": "Hindi",
        "reason": "Tax evasion notice, pay penalty online now to avoid arrest",
        "risk_hint": "high",
        "script_hint": "Government impersonation. Say: 'Income tax department se bol raha hoon. Aapke account mein tax evasion paya gaya hai. Abhi penalty pay karein warna arrest warrant issue hoga.'"
    },
    {
        "id": 20, "name": "Unknown", "number": "+91 99199 00234",
        "org": "Claims: Aadhaar UIDAI", "language": "Tamil",
        "reason": "Aadhaar will be deactivated, share OTP to re-verify",
        "risk_hint": "high",
        "script_hint": "Identity scam. Say: 'UIDAI-இல் இருந்து அழைக்கிறோம். உங்கள் Aadhaar deactivate ஆகும். OTP share செய்தால் மட்டுமே re-verify ஆகும்.'"
    },
]


async def simulate_call(profile_id: int = None, ws_callback=None) -> dict:
    """
    Run a complete simulated call through the full screening pipeline.
    
    Args:
        profile_id: Specific caller profile ID (1-20), or None for random
        ws_callback: Async function(event_type, data) for streaming to dashboard
    
    Returns:
        Completed Call dict
    """
    # Pick profile
    if profile_id and 1 <= profile_id <= 20:
        profile = next((p for p in CALLER_PROFILES if p["id"] == profile_id), None)
    else:
        profile = random.choice(CALLER_PROFILES)

    if not profile:
        profile = random.choice(CALLER_PROFILES)

    db = SessionLocal()
    try:
        # Load contacts for checks
        contacts = db.query(Contact).all()

        # ── 1. Announce call start ──────────────────────────────────────────
        if ws_callback:
            await ws_callback("call_started", {
                "caller_number": profile["number"],
                "caller_name": profile["name"],
                "language": profile["language"],
                "profile_id": profile["id"],
            })

        # ── 2. Create initial DB record ─────────────────────────────────────
        call = Call(
            caller_number=profile["number"],
            caller_name=profile["name"],
            caller_org=profile.get("org"),
            detected_language=profile["language"],
            action_taken="pending",
            is_simulated=1,
        )
        db.add(call)
        db.commit()
        db.refresh(call)

        # ── 3. Run AI screening conversation ───────────────────────────────
        conversation_result = await run_screening_conversation(
            caller_profile=profile,
            ws_callback=ws_callback
        )

        transcript = conversation_result["transcript"]
        extracted = conversation_result["extracted"]
        detected_lang = conversation_result["detected_language"]

        if ws_callback:
            await ws_callback("language_detected", {"language": detected_lang})

        # ── 4. Run all auth checks ─────────────────────────────────────────
        if ws_callback:
            await ws_callback("check_update", {"check_name": "contact", "status": "checking"})
            await ws_callback("check_update", {"check_name": "scam", "status": "checking"})
            await ws_callback("check_update", {"check_name": "spoofing", "status": "checking"})
            await ws_callback("check_update", {"check_name": "urgency", "status": "checking"})

        await asyncio.sleep(1.0)

        checks = run_all_checks(
            caller_name=extracted.get("caller_name", profile["name"]),
            caller_number=profile["number"],
            caller_org=extracted.get("organization", profile.get("org", "")),
            transcript=transcript,
            contacts=contacts,
        )

        # Stream check results one by one
        await asyncio.sleep(0.5)
        if ws_callback:
            await ws_callback("check_update", {"check_name": "contact", "status": checks["check_contact"]})
        await asyncio.sleep(0.5)
        if ws_callback:
            await ws_callback("check_update", {"check_name": "scam", "status": checks["check_scam"]})
        await asyncio.sleep(0.5)
        if ws_callback:
            await ws_callback("check_update", {"check_name": "spoofing", "status": checks["check_spoofing"]})
        await asyncio.sleep(0.5)
        if ws_callback:
            urgency_status = "flagged" if checks["urgency_flagged"] else "clear"
            await ws_callback("check_update", {"check_name": "urgency", "status": urgency_status})

        # ── 5. Compute risk score ─────────────────────────────────────────
        risk_result = compute_risk_score(
            transcript=transcript,
            extracted=extracted,
            caller_profile=profile,
            contacts=contacts,
        )

        if ws_callback:
            await ws_callback("risk_update", {
                "score": risk_result["score"],
                "level": risk_result["level"],
                "signals": risk_result["signals"],
            })

        # ── 6. Forwarding decision ────────────────────────────────────────
        from config import RISK_THRESHOLD
        score = risk_result["score"]

        if score < RISK_THRESHOLD:
            action = "forwarded"
            decision_reason = f"Risk score {score} is below threshold {RISK_THRESHOLD}. Call forwarded."
        elif score >= 70:
            action = "blocked"
            decision_reason = f"High risk score {score}. Call blocked automatically."
        else:
            action = "timeout_blocked"
            decision_reason = f"Medium risk {score}. No user response — defaulted to blocked."

        await asyncio.sleep(0.5)
        if ws_callback:
            await ws_callback("decision", {
                "action": action,
                "reason": decision_reason,
                "score": score,
            })

        # ── 7. Build reason summary ───────────────────────────────────────
        reason_summary = (
            f"{extracted.get('caller_name', profile['name'])} from "
            f"{extracted.get('organization', 'unknown')} is calling regarding: "
            f"{extracted.get('reason', profile['reason'])}."
        )

        # ── 8. Update DB record ───────────────────────────────────────────
        call.caller_name = extracted.get("caller_name", profile["name"])
        call.caller_org = extracted.get("organization", profile.get("org"))
        call.detected_language = detected_lang
        call.reason_summary = reason_summary
        call.full_transcript = json.dumps(transcript)
        call.intent_label = checks["intent_label"]
        call.intent_confidence = checks["intent_confidence"]
        call.risk_score = risk_result["score"]
        call.risk_level = risk_result["level"]
        call.risk_signals = json.dumps(risk_result["signals"])
        call.check_contact = checks["check_contact"]
        call.check_scam = checks["check_scam"]
        call.check_spoofing = checks["check_spoofing"]
        call.check_urgency_score = checks["check_urgency_score"]
        call.action_taken = action
        call.call_duration_seconds = conversation_result.get("duration_seconds", 60)
        db.commit()
        db.refresh(call)

        call_dict = call.to_dict()

        if ws_callback:
            await ws_callback("call_complete", {
                "call_id": call.id,
                "summary": reason_summary,
                "action": action,
            })

        return call_dict

    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()


def get_all_profiles() -> list:
    """Return all caller profiles for the settings dropdown."""
    return [
        {"id": p["id"], "name": p["name"], "org": p.get("org"), "risk_hint": p["risk_hint"]}
        for p in CALLER_PROFILES
    ]
