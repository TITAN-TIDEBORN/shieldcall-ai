"""
AI Agent — Powered by Google Gemini (Cloud) and Ollama (Local).
Supports real-time streaming and high-intelligence screening.
"""
import json
import random
import httpx
import asyncio
from datetime import datetime
import google.generativeai as genai
from config import OLLAMA_BASE_URL, OLLAMA_MODEL, OLLAMA_FALLBACK_MODE, GEMINI_API_KEY, GEMINI_MODEL
from services.language import detect_language

# Configure Gemini
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

def _calculate_delay(text: str) -> float:
    """Calculate a realistic delay based on text length (approx 150 WPM)."""
    word_count = len(text.split())
    return max(1.5, (word_count / 2.5) + 0.5)


SCREENER_SYSTEM_PROMPT = """You are a natural-sounding personal AI assistant named "ShieldCall".
You answer phone calls for your owner to find out who's calling and why.

Your goals:
1. Ask for their name and reason for calling.
2. If they are vague, ask a natural follow-up question.
3. If they push for urgency, OTPs, or sound threatening, stay calm and refuse politely.
4. End the conversation after 3-5 turns.

Rules:
- Speak in a natural, conversational tone.
- NEVER sound robotic.
- Speak in the same language the caller uses.
- Do NOT share personal information about your owner.
- The "speak" field MUST ONLY contain the words you want to be spoken. 
- DO NOT include labels like "(SCAM)", "[URGENT]", "Language: ...", or any meta-commentary in the "speak" field.
- Respond with ONLY a valid JSON object:
{
  "speak": "Hello, I'm a personal assistant. Who is calling, please?",
  "extracted": {
    "caller_name": "",
    "organization": "",
    "reason": "",
    "urgency_signals": [],
    "language": "English",
    "conversation_complete": false
  }
}"""

MOCK_TRANSCRIPTS = {
    "low": [
        {"role": "ai", "text": "Hi, this is a personal assistant. How can I help you today?"},
        {"role": "caller", "text": "Uh, hi... this is Suresh from Suresh Plumbing. Just calling to, um, confirm the appointment for tomorrow morning at 10."},
        {"role": "ai", "text": "Got it. Can you just confirm the address and what exactly we're fixing?"},
        {"role": "caller", "text": "Yeah, sure. It's for the kitchen pipe repair at the main house. The work order is WO-2024-1123."},
        {"role": "ai", "text": "Perfect, I've got all the details down. I'll let them know. Anything else you need to add?"},
        {"role": "caller", "text": "No, I think that's it. See you tomorrow!"},
        {"role": "ai", "text": "Alright, thank you!"},
    ],
    "medium": [
        {"role": "ai", "text": "Hello, ShieldCall assistant here. Who am I speaking with?"},
        {"role": "caller", "text": "Hi there! I'm reaching out about an exclusive financial offer we have for you today."},
        {"role": "ai", "text": "I see. Which company are you calling from, and could you briefly explain the offer?"},
        {"role": "caller", "text": "Oh, we're from a top financial firm. We have this amazing investment plan... guaranteed returns in just a few months."},
        {"role": "ai", "text": "Could you provide a company registration number or some verifiable employee ID?"},
        {"role": "caller", "text": "Well, um, I can get that for you later... but the offer actually expires today, so we need to act fast."},
        {"role": "ai", "text": "I understand. I'll pass the message along. We will review it. Goodbye."},
    ],
    "high": [
        {"role": "ai", "text": "Hello, who is calling, please?"},
        {"role": "caller", "text": "Listen, this is an urgent call from the RBI Digital Wallet division! Your KYC is pending and your account is going to be blocked in exactly two hours!"},
        {"role": "ai", "text": "Okay... Can you give me your employee ID and a verifiable RBI helpline number to confirm this?"},
        {"role": "caller", "text": "Look, there is no time for that! You need to read out the OTP sent to your phone right now, or the account is gone!"},
        {"role": "ai", "text": "I'm sorry, but we do not share OTPs over the phone under any circumstances."},
        {"role": "caller", "text": "If you don't tell me the OTP immediately, we will freeze your bank accounts and initiate legal action! You have to act now!"},
        {"role": "ai", "text": "I will be ending this call now. If there's a genuine issue, we will check our official apps. Goodbye."},
    ],
}

async def _call_ollama(messages: list, system: str) -> str:
    """Make a request to Ollama API."""
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [{"role": "system", "content": system}] + messages,
        "stream": False,
        "format": "json"
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json=payload
        )
        response.raise_for_status()
        data = response.json()
        return data["message"]["content"]

async def _call_gemini_stream(messages: list, system: str, ws_callback=None) -> str:
    """Call Google Gemini with streaming support."""
    if not GEMINI_API_KEY: return ""
    
    model = genai.GenerativeModel(GEMINI_MODEL, system_instruction=system)
    
    # Convert history to Gemini format
    history = []
    for m in messages[:-1]:
        history.append({"role": "user" if m["role"] == "user" else "model", "parts": [m["content"]]})
    
    chat = model.start_chat(history=history)
    full_response = ""
    
    response = await chat.send_message_async(messages[-1]["content"], stream=True)
    async for chunk in response:
        text = chunk.text
        full_response += text
        if ws_callback:
            await ws_callback("transcript_chunk", {"text": text, "role": "ai"})
            
    return full_response

async def check_ollama_available() -> bool:
    """Check if Ollama is running."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            return resp.status_code == 200
    except Exception:
        return False

async def run_screening_conversation(caller_profile: dict, ws_callback=None) -> dict:
    """Run the AI screening conversation with preferred Cloud AI or local Ollama."""
    use_gemini = bool(GEMINI_API_KEY)
    ollama_available = await check_ollama_available()
    use_mock = OLLAMA_FALLBACK_MODE and not ollama_available and not use_gemini

    if use_mock:
        return await _run_mock_conversation(caller_profile, ws_callback)
    else:
        return await _run_live_conversation(caller_profile, ws_callback, use_gemini)

async def _run_mock_conversation(caller_profile: dict, ws_callback=None) -> dict:
    """Use pre-scripted mock conversation based on risk hint."""
    risk_hint = caller_profile.get("risk_hint", "low")
    script = MOCK_TRANSCRIPTS.get(risk_hint, MOCK_TRANSCRIPTS["low"])
    customized = []
    for i, turn in enumerate(script):
        text = turn["text"]
        if turn["role"] == "caller" and i == 1:
            if risk_hint == "low":
                text = f"Hi, this is {caller_profile.get('name', 'the caller')} from {caller_profile.get('org') or 'calling personally'}. {caller_profile.get('reason', 'I am calling to speak with you.')}."
            elif risk_hint == "high":
                text = caller_profile.get("reason", text) + ". " + caller_profile.get("script_hint", "")
        
        customized.append({"role": turn["role"], "text": text, "timestamp": datetime.utcnow().isoformat()})
        if ws_callback:
            await ws_callback("transcript_line", customized[-1])
        await asyncio.sleep(_calculate_delay(text))

    lang = caller_profile.get("language", "English")
    return {
        "transcript": customized,
        "extracted": {"caller_name": caller_profile.get("name", "Unknown"), "organization": caller_profile.get("org", ""), "reason": caller_profile.get("reason", ""), "urgency_signals": [], "language": lang, "conversation_complete": True},
        "detected_language": lang,
        "duration_seconds": random.randint(45, 180),
        "used_fallback": True,
    }

async def _run_live_conversation(caller_profile: dict, ws_callback=None, use_gemini=False) -> dict:
    """Run live conversation using either Gemini or Ollama."""
    transcript = []
    conversation_history = []
    extracted = {"caller_name": "", "organization": "", "reason": "", "urgency_signals": [], "language": caller_profile.get("language", "English"), "conversation_complete": False}

    caller_system = f"You are a phone caller: {caller_profile.get('name')}, from {caller_profile.get('org')}. Reason: {caller_profile.get('reason')}. Language: {caller_profile.get('language')}. Respond ONLY in {caller_profile.get('language')}."

    # 1. Opening greeting
    ai_greeting = "Hello, I'm a personal assistant. Who is calling, please?"
    if ws_callback:
        await ws_callback("transcript_line", {"role": "ai", "text": ai_greeting, "timestamp": datetime.utcnow().isoformat()})
    transcript.append({"role": "ai", "text": ai_greeting, "timestamp": datetime.utcnow().isoformat()})
    conversation_history.append({"role": "assistant", "content": ai_greeting})
    await asyncio.sleep(1.0)

    for turn in range(5):
        # 2. Caller Turn
        if use_gemini:
            caller_msg = await _call_gemini_stream(conversation_history, caller_system, None)
        else:
            caller_msg = await _call_ollama(conversation_history, caller_system)
            
        if ws_callback:
            await ws_callback("transcript_line", {"role": "caller", "text": caller_msg, "timestamp": datetime.utcnow().isoformat()})
        transcript.append({"role": "caller", "text": caller_msg, "timestamp": datetime.utcnow().isoformat()})
        conversation_history.append({"role": "user", "content": caller_msg})
        await asyncio.sleep(1.0)

        # 3. AI Assistant Turn with Streaming
        if use_gemini:
            stream_prompt = SCREENER_SYSTEM_PROMPT + "\n\nRespond with ONLY the text you want to speak. NO JSON."
            ai_msg = await _call_gemini_stream(conversation_history, stream_prompt, ws_callback)
            # Post-extract
            try:
                raw_json = await _call_gemini_stream(conversation_history + [{"role": "assistant", "content": ai_msg}], "Extract info in JSON format matching the schema.", None)
                extracted.update(json.loads(raw_json))
            except: pass
        else:
            raw_res = await _call_ollama(conversation_history, SCREENER_SYSTEM_PROMPT)
            try:
                res_data = json.loads(raw_res)
                ai_msg = res_data.get("speak", "I understand.")
                extracted.update(res_data.get("extracted", {}))
            except: ai_msg = raw_res
            if ws_callback:
                await ws_callback("transcript_line", {"role": "ai", "text": ai_msg, "timestamp": datetime.utcnow().isoformat()})

        transcript.append({"role": "ai", "text": ai_msg, "timestamp": datetime.utcnow().isoformat()})
        conversation_history.append({"role": "assistant", "content": ai_msg})
        if extracted.get("conversation_complete"): break
            
    return {"transcript": transcript, "extracted": extracted, "detected_language": extracted.get("language", "English"), "duration_seconds": random.randint(30, 90)}
