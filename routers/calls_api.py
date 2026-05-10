"""
Calls API router — GET /api/calls, /api/calls/:id, /api/stats
"""
import json
from datetime import datetime, timedelta
from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from database.db import get_db
from database.models import Call

router = APIRouter(prefix="/api", tags=["calls"])

class ScanTextRequest(BaseModel):
    text: str
    history: Optional[list] = []



@router.get("/calls")
def list_calls(
    page: int = Query(1, ge=1),
    per_page: int = Query(15, ge=1, le=100),
    risk_level: Optional[str] = None,
    language: Optional[str] = None,
    action: Optional[str] = None,
    intent: Optional[str] = None,
    search: Optional[str] = None,
    sort: Optional[str] = "newest",
    db: Session = Depends(get_db),
):
    """Paginated call history with search + filters."""
    query = db.query(Call)

    if risk_level:
        query = query.filter(Call.risk_level == risk_level)
    if language:
        query = query.filter(Call.detected_language == language)
    if action:
        query = query.filter(Call.action_taken == action)
    if intent:
        query = query.filter(Call.intent_label == intent)
    if search:
        search_like = f"%{search}%"
        query = query.filter(
            (Call.caller_name.ilike(search_like)) |
            (Call.caller_number.ilike(search_like)) |
            (Call.caller_org.ilike(search_like))
        )

    if sort == "risk":
        query = query.order_by(desc(Call.risk_score))
    else:
        query = query.order_by(desc(Call.created_at))

    total = query.count()
    calls = query.offset((page - 1) * per_page).limit(per_page).all()

    return {
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page,
        "calls": [c.to_dict() for c in calls],
    }


@router.get("/calls/live")
def get_live_call(db: Session = Depends(get_db)):
    """Get the most recent pending call (for polling fallback)."""
    call = db.query(Call).filter(Call.action_taken == "pending").order_by(desc(Call.created_at)).first()
    return {"call": call.to_dict() if call else None}


@router.get("/calls/{call_id}")
def get_call(call_id: int, db: Session = Depends(get_db)):
    """Get full details of a specific call."""
    call = db.query(Call).filter(Call.id == call_id).first()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    return call.to_dict()


@router.post("/calls/{call_id}/action")
def update_call_action(call_id: int, body: dict, db: Session = Depends(get_db)):
    """Manually update call action (Block Now / Forward Now from dashboard)."""
    call = db.query(Call).filter(Call.id == call_id).first()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    action = body.get("action")
    if action not in ["forwarded", "blocked"]:
        raise HTTPException(status_code=400, detail="Invalid action. Use 'forwarded' or 'blocked'.")
    call.action_taken = action
    db.commit()
    return {"status": "updated", "call_id": call_id, "action": action}

@router.post("/scan-text")
async def scan_text(request: ScanTextRequest):
    """Scan arbitrary text and provide an interactive AI response."""
    from services.auth_checks import scam_check, urgency_check
    from config import SCAM_KEYWORDS, URGENCY_KEYWORDS, OTP_KEYWORDS, PAYMENT_KEYWORDS
    from services.language import detect_language
    from services.ai_agent import check_ollama_available, _call_ollama
    import json
    
    text = request.text
    history = request.history or []
    scam = scam_check(text)
    urgency = urgency_check(text)
    lang = detect_language(text)
    
    score = 0
    signals = []
    text_lower = text.lower()
    
    # 1. Heuristics for the current segment
    for kw in SCAM_KEYWORDS:
        if kw in text_lower:
            score += 35
            signals.append(f"Scam keyword: {kw}")
            break
            
    if urgency["flagged"]:
        score += 20
        signals.append("High urgency tone")

    for kw in OTP_KEYWORDS:
        if kw in text_lower:
            score += 40
            signals.append(f"Sensitive info request: {kw}")
            break
            
    for kw in PAYMENT_KEYWORDS:
        if kw in text_lower:
            score += 30
            signals.append(f"Payment requested: {kw}")
            break
        
    # 2. Interactive AI Response
    ai_reply = ""
    llm_reason = ""
    if await check_ollama_available():
        # System prompt for forensic assistant
        system_prompt = """You are "ShieldCall Personal Assistant". You are an automated AI system screening a call for your owner.
You are speaking DIRECTLY to the caller on the phone.

Goal:
1. Conduct a screening interview with the caller.
2. Find out exactly WHO they are and WHY they are calling.
3. Your tone should be polite but extremely formal and unyielding.

Instructions:
- If this is the start of the call, say: "Hello, I am an AI assistant. May I know who is calling and the purpose of your call?"
- If they give a name, ask for their organization.
- If they mention anything suspicious (OTPs, bank, urgency), ask for their official employee ID and verification details.
- DO NOT speak to the owner (the user). Speak ONLY to the caller.

CRITICAL: You must ALWAYS return a JSON object with this exact structure:
{
  "risk_score": <0-100 integer>,
  "is_scam": <boolean>,
  "analysis": "<internal note about the caller>",
  "reply": "<your direct verbal response to the caller>"
}"""
        try:
            # Prepare messages for Ollama: history + current text
            messages = []
            for h in history:
                role = "assistant" if h["role"] == "ai" else "user"
                messages.append({"role": role, "content": h["text"]})
            messages.append({"role": "user", "content": text})
            
            raw_res = await _call_ollama(messages, system_prompt)
            res = json.loads(raw_res)
            
            llm_score = res.get("risk_score", 0)
            llm_is_scam = res.get("is_scam", False)
            llm_analysis = res.get("analysis", "")
            ai_reply = res.get("reply", "")
            
            score = max(score, llm_score)
            if llm_is_scam:
                scam = "scam"
                if llm_analysis:
                    signals.insert(0, f"AI Analysis: {llm_analysis}")
            elif llm_analysis and llm_score > 30:
                signals.append(f"AI Note: {llm_analysis}")
                
        except Exception:
            pass
            
    # Fallback if AI fails or isn't available
    if not ai_reply:
        assistant_fallbacks = {
            "English": {
                "general": "I'm sorry, I didn't catch that. Could you please state your name and the purpose of your call?",
                "scam": "I am not authorized to provide that information or perform that action. Please state your official credentials."
            },
            "Tamil": {
                "general": "மன்னிக்கவும், எனக்கு அது புரியவில்லை. உங்கள் பெயர் மற்றும் அழைப்பின் நோக்கத்தை மீண்டும் கூற முடியுமா?",
                "scam": "அந்தத் தகவலை வழங்க எனக்கு அனுமதி இல்லை. உங்கள் அதிகாரப்பூர்வ விவரங்களைக் கூறவும்."
            }
        }
        fallback_set = assistant_fallbacks.get(lang, assistant_fallbacks["English"])
        ai_reply = fallback_set["scam"] if score >= 50 else fallback_set["general"]
    
    score = min(100, score)
    level = "low" if score < 40 else "medium" if score < 70 else "high"
    if score >= 40 and scam != "scam":
        scam = "flagged"
        
    return {
        "text": text,
        "scam_status": scam,
        "urgency_score": urgency["urgency_score"],
        "risk_score": score,
        "risk_level": level,
        "signals": signals[:4],
        "ai_reply": ai_reply,
        "detected_language": lang
    }



@router.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    """Analytics stats for the dashboard."""
    total = db.query(Call).count()
    forwarded = db.query(Call).filter(Call.action_taken == "forwarded").count()
    blocked = db.query(Call).filter(
        Call.action_taken.in_(["blocked", "timeout_blocked"])
    ).count()
    block_rate = round((blocked / total * 100) if total > 0 else 0, 1)

    avg_risk_result = db.query(func.avg(Call.risk_score)).scalar()
    avg_risk = round(avg_risk_result or 0, 1)

    # Intent breakdown
    intent_rows = (
        db.query(Call.intent_label, func.count(Call.id).label("count"))
        .group_by(Call.intent_label)
        .all()
    )
    intent_breakdown = {row.intent_label: row.count for row in intent_rows}

    # Language breakdown
    lang_rows = (
        db.query(Call.detected_language, func.count(Call.id).label("count"))
        .group_by(Call.detected_language)
        .all()
    )
    language_breakdown = {row.detected_language: row.count for row in lang_rows}

    # Daily volume — last 14 days
    daily_volume = []
    for i in range(13, -1, -1):
        day = datetime.utcnow().date() - timedelta(days=i)
        day_start = datetime.combine(day, datetime.min.time())
        day_end = datetime.combine(day, datetime.max.time())
        day_total = db.query(Call).filter(
            Call.created_at >= day_start, Call.created_at <= day_end
        ).count()
        day_forwarded = db.query(Call).filter(
            Call.created_at >= day_start, Call.created_at <= day_end,
            Call.action_taken == "forwarded"
        ).count()
        day_blocked = db.query(Call).filter(
            Call.created_at >= day_start, Call.created_at <= day_end,
            Call.action_taken.in_(["blocked", "timeout_blocked"])
        ).count()
        daily_volume.append({
            "date": day.strftime("%b %d"),
            "total": day_total,
            "forwarded": day_forwarded,
            "blocked": day_blocked,
        })

    # Top blocked numbers
    top_blocked_rows = (
        db.query(Call.caller_number, func.count(Call.id).label("count"))
        .filter(Call.action_taken.in_(["blocked", "timeout_blocked"]))
        .group_by(Call.caller_number)
        .order_by(desc("count"))
        .limit(10)
        .all()
    )
    top_blocked = [{"number": row.caller_number, "count": row.count} for row in top_blocked_rows]

    # Risk signal frequency — parse JSON fields
    all_signals_raw = db.query(Call.risk_signals).filter(Call.risk_signals.isnot(None)).all()
    signal_counts = {}
    for row in all_signals_raw:
        try:
            signals = json.loads(row.risk_signals or "[]")
            for sig in signals:
                short = sig[:60]
                signal_counts[short] = signal_counts.get(short, 0) + 1
        except Exception:
            pass
    top_signals = sorted(signal_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    top_signals = [{"signal": s, "count": c} for s, c in top_signals]

    return {
        "total": total,
        "forwarded": forwarded,
        "blocked": blocked,
        "block_rate": block_rate,
        "avg_risk_score": avg_risk,
        "intent_breakdown": intent_breakdown,
        "language_breakdown": language_breakdown,
        "daily_volume": daily_volume,
        "top_blocked_numbers": top_blocked,
        "top_risk_signals": top_signals,
    }
