"""
seed_data.py — Populate the database with realistic sample call history.
Run once: python seed_data.py
"""
import json
import random
from datetime import datetime, timedelta
from database.db import init_db, SessionLocal
from database.models import Call, Contact, Blocklist

init_db()
db = SessionLocal()

SAMPLE_CALLS = [
    # Low risk - Forwarded
    {"caller_number": "+91 94440 11234", "caller_name": "Suresh Kumar", "caller_org": "Suresh Plumbing Services", "detected_language": "Tamil", "reason_summary": "Suresh Kumar from Suresh Plumbing Services called to confirm the plumbing appointment scheduled for tomorrow at 10 AM. He provided the work order number WO-2024-1123.", "intent_label": "service_appointment", "intent_confidence": 0.92, "risk_score": 8, "risk_level": "low", "risk_signals": ["✓ Caller provided verifiable reference number", "✓ Calm, non-pressuring tone detected", "✓ Caller profile matches low-risk pattern"], "check_contact": "partial", "check_scam": "clean", "check_spoofing": "genuine", "check_urgency_score": 0, "action_taken": "forwarded", "call_duration_seconds": 87},
    {"caller_number": "+91 98765 00100", "caller_name": "Dr. Priya Clinic", "caller_org": "Priya Nursing Home", "detected_language": "English", "reason_summary": "Dr. Priya Clinic called to remind about the Friday 3 PM appointment and to ask about any known allergies before the consultation.", "intent_label": "medical", "intent_confidence": 0.95, "risk_score": 12, "risk_level": "low", "risk_signals": ["✓ Caller provided verifiable reference number", "✓ Calm, non-pressuring tone detected"], "check_contact": "unverified", "check_scam": "clean", "check_spoofing": "genuine", "check_urgency_score": 0, "action_taken": "forwarded", "call_duration_seconds": 65},
    {"caller_number": "+91 77001 55443", "caller_name": "Ravi (cousin)", "caller_org": None, "detected_language": "Tamil", "reason_summary": "Ravi called to confirm attendance at the family function this Saturday and discuss food arrangements for the event.", "intent_label": "personal_family", "intent_confidence": 0.98, "risk_score": 5, "risk_level": "low", "risk_signals": ["✓ Caller matched saved contact", "✓ Calm, non-pressuring tone detected", "✓ Caller profile matches low-risk pattern"], "check_contact": "verified", "check_scam": "clean", "check_spoofing": "genuine", "check_urgency_score": 0, "action_taken": "forwarded", "call_duration_seconds": 142},
    {"caller_number": "+91 44 6676 9999", "caller_name": "TCS HR Recruiter", "caller_org": "Tata Consultancy Services", "detected_language": "English", "reason_summary": "TCS HR called to confirm Monday interview attendance and provided application reference number TCS-2024-HR-8812.", "intent_label": "official_government", "intent_confidence": 0.78, "risk_score": 15, "risk_level": "low", "risk_signals": ["✓ Caller provided verifiable reference number", "✓ Calm, non-pressuring tone detected", "Caller number not found in saved contacts"], "check_contact": "unverified", "check_scam": "clean", "check_spoofing": "genuine", "check_urgency_score": 1, "action_taken": "forwarded", "call_duration_seconds": 98},
    {"caller_number": "+91 0431 2345678", "caller_name": "St. Joseph School", "caller_org": "St. Joseph Matric School", "detected_language": "English", "reason_summary": "St. Joseph School called regarding the parent-teacher meeting scheduled for next Tuesday at 4 PM.", "intent_label": "service_appointment", "intent_confidence": 0.85, "risk_score": 10, "risk_level": "low", "risk_signals": ["✓ Calm, non-pressuring tone detected"], "check_contact": "unverified", "check_scam": "clean", "check_spoofing": "genuine", "check_urgency_score": 0, "action_taken": "forwarded", "call_duration_seconds": 55},
    {"caller_number": "+91 1800 202 6161", "caller_name": "HDFC Bank Official", "caller_org": "HDFC Bank", "detected_language": "English", "reason_summary": "HDFC Bank called to follow up on a credit card statement query and requested a branch visit — did not ask for OTP or PIN.", "intent_label": "financial", "intent_confidence": 0.80, "risk_score": 22, "risk_level": "low", "risk_signals": ["Claims official/government role: 'HDFC Bank'", "✓ Caller provided verifiable reference number"], "check_contact": "unverified", "check_scam": "clean", "check_spoofing": "genuine", "check_urgency_score": 0, "action_taken": "forwarded", "call_duration_seconds": 78},
    {"caller_number": "+91 98400 77612", "caller_name": "Meena Aunty", "caller_org": None, "detected_language": "Tamil", "reason_summary": "Meena Aunty called to check in and invite to the Pongal celebration at her home next week.", "intent_label": "personal_family", "intent_confidence": 0.96, "risk_score": 5, "risk_level": "low", "risk_signals": ["✓ Caller matched saved contact", "✓ Calm, non-pressuring tone detected"], "check_contact": "verified", "check_scam": "clean", "check_spoofing": "genuine", "check_urgency_score": 0, "action_taken": "forwarded", "call_duration_seconds": 210},
    {"caller_number": "+91 1800 300 900", "caller_name": "Amazon Delivery", "caller_org": "Amazon Logistics", "detected_language": "Hindi", "reason_summary": "Amazon Logistics called to inform about a package delivery and requested a delivery OTP — this is a standard legitimate delivery process.", "intent_label": "delivery", "intent_confidence": 0.94, "risk_score": 18, "risk_level": "low", "risk_signals": ["Sensitive data requested: otp", "✓ Caller provided verifiable reference number", "✓ Caller profile matches low-risk pattern"], "check_contact": "unverified", "check_scam": "clean", "check_spoofing": "genuine", "check_urgency_score": 1, "action_taken": "forwarded", "call_duration_seconds": 45},
    # Medium risk
    {"caller_number": "+91 80001 99234", "caller_name": "Unknown Sales", "caller_org": "Vague financial services", "detected_language": "Hindi", "reason_summary": "An unknown caller pushed a financial services offer without naming the company. Deflected when asked for company registration details.", "intent_label": "sales_telemarketing", "intent_confidence": 0.72, "risk_score": 48, "risk_level": "medium", "risk_signals": ["Caller could not provide verifiable identity", "Caller number not found in saved contacts", "Urgency language detected: last chance"], "check_contact": "unverified", "check_scam": "suspicious", "check_spoofing": "suspicious", "check_urgency_score": 5, "action_taken": "blocked", "call_duration_seconds": 120},
    {"caller_number": "+91 70003 11122", "caller_name": "Survey Caller", "caller_org": "Government survey (unspecified)", "detected_language": "Tamil", "reason_summary": "Caller claimed to conduct a government housing survey but could not name the specific department and asked for Aadhaar details.", "intent_label": "official_government", "intent_confidence": 0.55, "risk_score": 55, "risk_level": "medium", "risk_signals": ["Caller could not provide verifiable identity", "Claims official/government role", "Caller number not found in saved contacts"], "check_contact": "unverified", "check_scam": "suspicious", "check_spoofing": "suspicious", "check_urgency_score": 3, "action_taken": "timeout_blocked", "call_duration_seconds": 95},
    {"caller_number": "+91 98998 00123", "caller_name": "Unknown", "caller_org": "Claims to be Jio", "detected_language": "Hindi", "reason_summary": "Caller claimed to offer a free Jio recharge but asked to confirm personal details. Offer appeared too good to be genuine.", "intent_label": "sales_telemarketing", "intent_confidence": 0.68, "risk_score": 45, "risk_level": "medium", "risk_signals": ["Caller number not found in saved contacts", "Urgency language detected: limited time offer"], "check_contact": "unverified", "check_scam": "suspicious", "check_spoofing": "suspicious", "check_urgency_score": 4, "action_taken": "blocked", "call_duration_seconds": 75},
    # High risk - Blocked
    {"caller_number": "+91 99900 00001", "caller_name": "Unknown", "caller_org": "Claims: RBI Digital Wallet", "detected_language": "Hindi", "reason_summary": "Caller claimed to be from RBI and demanded an OTP to prevent account blocking — this is a known KYC verification scam.", "intent_label": "scam_suspected", "intent_confidence": 0.99, "risk_score": 95, "risk_level": "high", "risk_signals": ["Caller mentioned 'RBI Digital Wallet' — classic scam phrase", "Caller mentioned 'KYC verification' — common fraud tactic", "Sensitive data requested: otp", "Urgency language detected: immediately, 2 hours", "Official org claimed but caller uses mobile number — potential spoofing", "Payment/transfer requested"], "check_contact": "unverified", "check_scam": "scam", "check_spoofing": "spoofed", "check_urgency_score": 10, "action_taken": "blocked", "call_duration_seconds": 183},
    {"caller_number": "+91 88800 12399", "caller_name": "Unknown", "caller_org": "Claims: TRAI", "detected_language": "English", "reason_summary": "Caller claimed TRAI would disconnect the number in 2 hours due to illegal activity — a known TRAI disconnection scam. Used automated IVR tactics.", "intent_label": "scam_suspected", "intent_confidence": 0.99, "risk_score": 92, "risk_level": "high", "risk_signals": ["Caller mentioned 'TRAI disconnection' — telecom scam pattern", "Urgency language detected: 2 hours, immediately", "Official org claimed but caller uses mobile number — potential spoofing", "Automated scam IVR pattern detected: press 9"], "check_contact": "unverified", "check_scam": "scam", "check_spoofing": "spoofed", "check_urgency_score": 9, "action_taken": "blocked", "call_duration_seconds": 145},
    {"caller_number": "+91 70070 55566", "caller_name": "Unknown", "caller_org": "Claims: FedEx Courier", "detected_language": "English", "reason_summary": "Caller claimed a FedEx parcel in the owner's name contained drugs at customs and demanded a clearance fee — classic courier extortion scam.", "intent_label": "scam_suspected", "intent_confidence": 0.98, "risk_score": 98, "risk_level": "high", "risk_signals": ["Caller mentioned courier with drugs — courier scam pattern", "Caller mentioned customs clearance — courier extortion", "Payment/transfer requested", "Urgency language detected: immediately"], "check_contact": "unverified", "check_scam": "scam", "check_spoofing": "spoofed", "check_urgency_score": 10, "action_taken": "blocked", "call_duration_seconds": 167},
    {"caller_number": "+91 77007 23344", "caller_name": "Unknown", "caller_org": "Claims: TNEB Electricity Board", "detected_language": "Tamil", "reason_summary": "Caller claimed to be from TNEB and threatened electricity disconnection in 2 hours unless ₹3200 was paid immediately.", "intent_label": "scam_suspected", "intent_confidence": 0.97, "risk_score": 90, "risk_level": "high", "risk_signals": ["Caller mentioned electricity cut — utility scam", "Payment/transfer requested", "Urgency language detected: உடனே, 2 hours", "Official org claimed but caller uses mobile number — potential spoofing"], "check_contact": "unverified", "check_scam": "scam", "check_spoofing": "spoofed", "check_urgency_score": 9, "action_taken": "blocked", "call_duration_seconds": 122},
    {"caller_number": "+91 98001 77123", "caller_name": "Unknown", "caller_org": "Claims: CBI/Police", "detected_language": "Hindi", "reason_summary": "Caller impersonated a CBI officer, claimed an arrest warrant was issued for money laundering, and asked the owner to stay on the line.", "intent_label": "scam_suspected", "intent_confidence": 0.99, "risk_score": 100, "risk_level": "high", "risk_signals": ["Caller mentioned arrest warrant — extortion/fear scam", "Caller mentioned money laundering charges — fear scam", "Caller claims to be CBI officer — authority impersonation", "Urgency language detected: abhi, or else", "Official org claimed but caller uses mobile number — potential spoofing"], "check_contact": "unverified", "check_scam": "scam", "check_spoofing": "spoofed", "check_urgency_score": 10, "action_taken": "blocked", "call_duration_seconds": 201},
    {"caller_number": "+91 63006 12900", "caller_name": "Unknown", "caller_org": "Claims: SBI Bank", "detected_language": "English", "reason_summary": "Caller claimed to be from SBI and requested an OTP to unfreeze an account — classic bank phishing script.", "intent_label": "scam_suspected", "intent_confidence": 0.99, "risk_score": 93, "risk_level": "high", "risk_signals": ["Sensitive data requested: otp, account number", "Urgency language detected: immediately", "Official org claimed but caller uses mobile number — potential spoofing", "Caller mentioned 'your account will be frozen'"], "check_contact": "unverified", "check_scam": "scam", "check_spoofing": "spoofed", "check_urgency_score": 10, "action_taken": "blocked", "call_duration_seconds": 156},
    {"caller_number": "+91 80808 55100", "caller_name": "Unknown", "caller_org": "Claims: Income Tax Dept", "detected_language": "Hindi", "reason_summary": "Caller claimed income tax evasion was detected and demanded immediate online payment to avoid an arrest warrant.", "intent_label": "scam_suspected", "intent_confidence": 0.98, "risk_score": 97, "risk_level": "high", "risk_signals": ["Caller mentioned income tax notice — tax scam", "Caller mentioned arrest warrant — extortion/fear scam", "Payment/transfer requested", "Urgency language detected: abhi, turant"], "check_contact": "unverified", "check_scam": "scam", "check_spoofing": "spoofed", "check_urgency_score": 10, "action_taken": "blocked", "call_duration_seconds": 189},
    {"caller_number": "+91 99199 00234", "caller_name": "Unknown", "caller_org": "Claims: Aadhaar UIDAI", "detected_language": "Tamil", "reason_summary": "Caller claimed to be from UIDAI and threatened Aadhaar deactivation unless an OTP was shared immediately.", "intent_label": "scam_suspected", "intent_confidence": 0.99, "risk_score": 96, "risk_level": "high", "risk_signals": ["Caller mentioned Aadhaar deactivation — identity scam", "Caller mentioned UIDAI — Aadhaar phishing pattern", "Sensitive data requested: otp", "Official org claimed but caller uses mobile number — potential spoofing"], "check_contact": "unverified", "check_scam": "scam", "check_spoofing": "spoofed", "check_urgency_score": 10, "action_taken": "blocked", "call_duration_seconds": 138},
    # More variety
    {"caller_number": "+91 90009 44312", "caller_name": "Unknown", "caller_org": None, "detected_language": "English", "reason_summary": "Caller asked personal questions about whether anyone was home regularly. Appeared to be gathering information for suspicious purposes.", "intent_label": "unknown", "intent_confidence": 0.40, "risk_score": 42, "risk_level": "medium", "risk_signals": ["Caller could not provide verifiable identity", "Caller number not found in saved contacts"], "check_contact": "unverified", "check_scam": "suspicious", "check_spoofing": "suspicious", "check_urgency_score": 2, "action_taken": "blocked", "call_duration_seconds": 68},
    {"caller_number": "+91 94440 11234", "caller_name": "Suresh Kumar", "caller_org": "Suresh Plumbing Services", "detected_language": "Tamil", "reason_summary": "Follow-up call from Suresh Plumbing regarding completion of the previous job and request for feedback.", "intent_label": "service_appointment", "intent_confidence": 0.88, "risk_score": 5, "risk_level": "low", "risk_signals": ["✓ Calm, non-pressuring tone detected", "✓ Caller profile matches low-risk pattern"], "check_contact": "partial", "check_scam": "clean", "check_spoofing": "genuine", "check_urgency_score": 0, "action_taken": "forwarded", "call_duration_seconds": 62},
    {"caller_number": "+91 77001 55443", "caller_name": "Ravi (cousin)", "caller_org": None, "detected_language": "Tamil", "reason_summary": "Ravi called to discuss travel arrangements for the upcoming family trip to Ooty next month.", "intent_label": "personal_family", "intent_confidence": 0.95, "risk_score": 3, "risk_level": "low", "risk_signals": ["✓ Caller matched saved contact", "✓ Calm, non-pressuring tone detected"], "check_contact": "verified", "check_scam": "clean", "check_spoofing": "genuine", "check_urgency_score": 0, "action_taken": "forwarded", "call_duration_seconds": 175},
    {"caller_number": "+91 98765 44100", "caller_name": "Swiggy Delivery", "caller_org": "Swiggy", "detected_language": "Hindi", "reason_summary": "Swiggy delivery partner called to confirm the delivery address for a food order placed 30 minutes ago.", "intent_label": "delivery", "intent_confidence": 0.93, "risk_score": 10, "risk_level": "low", "risk_signals": ["✓ Calm, non-pressuring tone detected", "Caller number not found in saved contacts"], "check_contact": "unverified", "check_scam": "clean", "check_spoofing": "genuine", "check_urgency_score": 0, "action_taken": "forwarded", "call_duration_seconds": 38},
    {"caller_number": "+91 88900 11200", "caller_name": "Max Life Insurance", "caller_org": "Max Life Insurance", "detected_language": "English", "reason_summary": "Insurance agent called to discuss a life insurance renewal due next month. Provided policy number for reference.", "intent_label": "sales_telemarketing", "intent_confidence": 0.75, "risk_score": 35, "risk_level": "low", "risk_signals": ["Caller number not found in saved contacts", "✓ Caller provided verifiable reference number"], "check_contact": "unverified", "check_scam": "clean", "check_spoofing": "genuine", "check_urgency_score": 2, "action_taken": "forwarded", "call_duration_seconds": 112},
]

SAMPLE_CONTACTS = [
    {"name": "Ravi (cousin)", "phone_number": "+91 77001 55443", "organization": None, "notes": "Cousin, Coimbatore"},
    {"name": "Meena Aunty", "phone_number": "+91 98400 77612", "organization": None, "notes": "Mother's sister"},
    {"name": "Dr. Anand", "phone_number": "+91 98765 12345", "organization": "Apollo Hospitals", "notes": "Family doctor"},
    {"name": "Suresh Plumber", "phone_number": "+91 94440 11234", "organization": "Suresh Plumbing", "notes": "Home plumber"},
    {"name": "Karthik (colleague)", "phone_number": "+91 99400 55211", "organization": "Infosys", "notes": "Team member"},
    {"name": "Mom", "phone_number": "+91 98431 00001", "organization": None, "notes": ""},
    {"name": "Dad", "phone_number": "+91 94430 00002", "organization": None, "notes": ""},
    {"name": "Priya (wife)", "phone_number": "+91 97890 33212", "organization": None, "notes": ""},
    {"name": "Kiran Kumar", "phone_number": "+91 81200 44312", "organization": "State Bank of India", "notes": "Bank relationship manager"},
    {"name": "Selva (neighbour)", "phone_number": "+91 90034 11233", "organization": None, "notes": "Flat 4B"},
]

SAMPLE_BLOCKLIST = [
    {"pattern": "+91 99900 00001", "reason": "RBI KYC scam — reported multiple times"},
    {"pattern": "+91 88800 12399", "reason": "TRAI disconnection scam"},
    {"pattern": "+91 70070 55566", "reason": "FedEx courier drug parcel scam"},
    {"pattern": "+91 98001 77123", "reason": "Fake CBI officer scam"},
    {"pattern": "+91 999*", "reason": "Pattern block: scam number range"},
]

# Clear existing data
db.query(Call).delete()
db.query(Contact).delete()
db.query(Blocklist).delete()
db.commit()

# Add contacts
for c in SAMPLE_CONTACTS:
    db.add(Contact(**c))

# Add blocklist
for b in SAMPLE_BLOCKLIST:
    db.add(Blocklist(**b))

# Add calls with realistic timestamps spread over last 14 days
now = datetime.utcnow()
for i, call_data in enumerate(SAMPLE_CALLS):
    days_ago = random.randint(0, 13)
    hours_ago = random.randint(0, 23)
    mins_ago = random.randint(0, 59)
    created = now - timedelta(days=days_ago, hours=hours_ago, minutes=mins_ago)

    transcript = [
        {"role": "ai", "text": "Hello, this is a personal assistant. May I know who is calling and how I can help?", "timestamp": created.isoformat()},
        {"role": "caller", "text": call_data["reason_summary"], "timestamp": (created + timedelta(seconds=10)).isoformat()},
        {"role": "ai", "text": "Thank you. Could you please provide your name and organization?", "timestamp": (created + timedelta(seconds=20)).isoformat()},
        {"role": "caller", "text": f"I'm {call_data['caller_name']} from {call_data['caller_org'] or 'calling personally'}.", "timestamp": (created + timedelta(seconds=35)).isoformat()},
        {"role": "ai", "text": "I've noted your details. I'll pass this information to the owner. Thank you for calling.", "timestamp": (created + timedelta(seconds=50)).isoformat()},
    ]

    call = Call(
        created_at=created,
        caller_number=call_data["caller_number"],
        caller_name=call_data["caller_name"],
        caller_org=call_data.get("caller_org"),
        detected_language=call_data["detected_language"],
        reason_summary=call_data["reason_summary"],
        full_transcript=json.dumps(transcript),
        intent_label=call_data["intent_label"],
        intent_confidence=call_data["intent_confidence"],
        risk_score=call_data["risk_score"],
        risk_level=call_data["risk_level"],
        risk_signals=json.dumps(call_data["risk_signals"]),
        check_contact=call_data["check_contact"],
        check_scam=call_data["check_scam"],
        check_spoofing=call_data["check_spoofing"],
        check_urgency_score=call_data["check_urgency_score"],
        action_taken=call_data["action_taken"],
        call_duration_seconds=call_data["call_duration_seconds"],
        is_simulated=1,
    )
    db.add(call)

db.commit()
db.close()

print("✅ Seed data loaded successfully!")
print(f"   → {len(SAMPLE_CALLS)} sample calls added")
print(f"   → {len(SAMPLE_CONTACTS)} contacts added")
print(f"   → {len(SAMPLE_BLOCKLIST)} blocklist entries added")
print("\nRun: uvicorn main:app --reload")
print("Then open: http://localhost:8000")
