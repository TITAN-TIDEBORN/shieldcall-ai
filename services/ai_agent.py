"""
AI Agent — Ollama-powered screening conversation with fallback mock mode.
"""
import json
import random
import httpx
import asyncio
from datetime import datetime
from config import OLLAMA_BASE_URL, OLLAMA_MODEL, OLLAMA_FALLBACK_MODE
from services.language import detect_language

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


async def check_ollama_available() -> bool:
    """Check if Ollama is running."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            return resp.status_code == 200
    except Exception:
        return False


async def run_screening_conversation(
    caller_profile: dict,
    ws_callback=None
) -> dict:
    """
    Run the full AI screening conversation.
    
    Args:
        caller_profile: Dict with name, org, reason, language, risk_hint, script_hint
        ws_callback: Async function to stream events (optional)
    
    Returns:
        {
            "transcript": [...],
            "extracted": {...},
            "detected_language": str,
            "duration_seconds": int
        }
    """
    ollama_available = await check_ollama_available()
    use_mock = OLLAMA_FALLBACK_MODE and not ollama_available

    if use_mock:
        return await _run_mock_conversation(caller_profile, ws_callback)
    else:
        return await _run_ollama_conversation(caller_profile, ws_callback)


async def _run_mock_conversation(caller_profile: dict, ws_callback=None) -> dict:
    """Use pre-scripted mock conversation based on risk hint."""
    risk_hint = caller_profile.get("risk_hint", "low")
    script = MOCK_TRANSCRIPTS.get(risk_hint, MOCK_TRANSCRIPTS["low"])

    # Customize the mock transcript with the actual profile data
    customized = []
    for i, turn in enumerate(script):
        text = turn["text"]
        # Replace generic references with profile-specific data
        if turn["role"] == "caller" and i == 1:
            if risk_hint == "low":
                text = (
                    f"Hi, this is {caller_profile.get('name', 'the caller')} "
                    f"from {caller_profile.get('org') or 'calling personally'}. "
                    f"{caller_profile.get('reason', 'I am calling to speak with you.')}."
                )
            elif risk_hint == "high":
                text = caller_profile.get("reason", text) + ". " + caller_profile.get("script_hint", "")

        customized.append({
            "role": turn["role"],
            "text": text,
            "timestamp": datetime.utcnow().isoformat()
        })

        # Stream each line with a realistic delay
        if ws_callback:
            await ws_callback("transcript_line", {
                "role": turn["role"],
                "text": text,
                "timestamp": datetime.utcnow().isoformat()
            })
        await asyncio.sleep(_calculate_delay(text))

    lang = caller_profile.get("language", "English")
    full_text = " ".join(t["text"] for t in customized if t["role"] == "caller")

    return {
        "transcript": customized,
        "extracted": {
            "caller_name": caller_profile.get("name", "Unknown"),
            "organization": caller_profile.get("org", ""),
            "reason": caller_profile.get("reason", ""),
            "urgency_signals": [],
            "language": lang,
            "conversation_complete": True,
        },
        "detected_language": lang,
        "duration_seconds": random.randint(45, 180),
        "used_fallback": True,
    }


async def _run_ollama_conversation(caller_profile: dict, ws_callback=None) -> dict:
    """Run live Ollama-powered screening conversation."""
    transcript = []
    conversation_history = []
    max_turns = 5
    extracted = {
        "caller_name": "",
        "organization": "",
        "reason": "",
        "urgency_signals": [],
        "language": caller_profile.get("language", "English"),
        "conversation_complete": False,
    }

    caller_system = f"""You are playing the role of a phone caller with this profile:
Name: {caller_profile.get('name', 'Unknown')}
Organization: {caller_profile.get('org', 'N/A')}
Reason for calling: {caller_profile.get('reason', 'General inquiry')}
Language: {caller_profile.get('language', 'English')}
Behavior hints: {caller_profile.get('script_hint', 'Be natural and direct')}

Simulate being this caller responding to a call screening assistant.
Respond naturally as this person would. Keep each response to 1-3 sentences.
Respond ONLY in {caller_profile.get('language', 'English')}. DO NOT use any other language.
DO NOT include any metadata or analysis in your response. Just the spoken words.
If the screener asks questions you wouldn't know, deflect naturally."""

    # Opening greeting from screener
    screener_opening = "Hi there, I'm a personal assistant handling calls right now. May I know who's calling?"
    transcript.append({
        "role": "ai", "text": screener_opening,
        "timestamp": datetime.utcnow().isoformat()
    })
    conversation_history.append({"role": "assistant", "content": screener_opening})
    if ws_callback:
        await ws_callback("transcript_line", transcript[-1])
        await asyncio.sleep(_calculate_delay(screener_opening))

    for turn in range(max_turns):
        await asyncio.sleep(random.uniform(1.0, 2.0))

        # Generate caller response
        caller_prompt = conversation_history + [
            {"role": "user", "content": "Respond as the caller to the last message."}
        ]
        try:
            caller_raw = await _call_ollama(
                [{"role": "user", "content": f"Respond as the caller: {conversation_history[-1]['content']}"}],
                caller_system
            )
            caller_text = caller_raw.strip().strip('"')
        except Exception:
            caller_text = caller_profile.get("reason", "I'm calling for some assistance.")

        transcript.append({
            "role": "caller", "text": caller_text,
            "timestamp": datetime.utcnow().isoformat()
        })
        conversation_history.append({"role": "user", "content": caller_text})
        if ws_callback:
            await ws_callback("transcript_line", transcript[-1])

        # Detect language from first caller utterance
        if turn == 0:
            detected_lang = detect_language(caller_text)
            if detected_lang != "English":
                extracted["language"] = detected_lang
            if ws_callback:
                await ws_callback("language_detected", {"language": extracted["language"]})

        await asyncio.sleep(_calculate_delay(caller_text))

        # Generate screener response
        try:
            screener_raw = await _call_ollama(conversation_history, SCREENER_SYSTEM_PROMPT)
            screener_data = json.loads(screener_raw)
            screener_text = screener_data.get("speak", "Thank you. Is there anything else?")
            new_extracted = screener_data.get("extracted", {})
            # Merge extracted data
            for k, v in new_extracted.items():
                if v and not extracted.get(k):
                    extracted[k] = v
            if new_extracted.get("conversation_complete"):
                transcript.append({
                    "role": "ai", "text": screener_text,
                    "timestamp": datetime.utcnow().isoformat()
                })
                if ws_callback:
                    await ws_callback("transcript_line", transcript[-1])
                break
        except Exception:
            screener_text = "Thank you for the information. I'll pass this to the owner."
            extracted["conversation_complete"] = True

        transcript.append({
            "role": "ai", "text": screener_text,
            "timestamp": datetime.utcnow().isoformat()
        })
        conversation_history.append({"role": "assistant", "content": screener_text})
        if ws_callback:
            await ws_callback("transcript_line", transcript[-1])

        if extracted.get("conversation_complete"):
            await asyncio.sleep(_calculate_delay(screener_text))
            break
        
        await asyncio.sleep(_calculate_delay(screener_text))

    # Fill in from profile if AI didn't extract
    if not extracted.get("caller_name"):
        extracted["caller_name"] = caller_profile.get("name", "Unknown")
    if not extracted.get("organization"):
        extracted["organization"] = caller_profile.get("org", "")
    if not extracted.get("reason"):
        extracted["reason"] = caller_profile.get("reason", "")

    return {
        "transcript": transcript,
        "extracted": extracted,
        "detected_language": extracted.get("language", "English"),
        "duration_seconds": len(transcript) * random.randint(15, 30),
        "used_fallback": False,
    }
