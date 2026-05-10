# ShieldCall AI — Setup Guide

## Quick Start (5 minutes)

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. (Optional) Install Ollama for real AI responses
Download from https://ollama.com
Then run: `ollama pull llama3`
If Ollama is not installed, the app works seamlessly with built-in mock responses.

### 3. Seed the database with sample data
```bash
python seed_data.py
```

### 4. Start the server
```bash
uvicorn main:app --reload
```

### 5. Open the dashboard
Open your browser to: http://localhost:8000

### 6. Simulate a call
Click "Simulate Call" in the top right of the dashboard header and watch the live AI screening.

## How it works
This is a 100% free, local portfolio/demo version of ShieldCall AI. It uses a **Call Simulator Engine** to mimic incoming calls.
1. The **Simulator** generates a realistic call (using 1 of 20 detailed profiles like "Fake FedEx Courier" or "Delivery Agent").
2. The **AI Agent** conducts a conversational screening with the caller (powered locally by Ollama, or built-in mock scripts).
3. The **Risk Engine** analyzes the conversation for urgency, scam keywords, and threats to compute a 0-100 score.
4. **Auth Checks** scan for spoofed numbers, verify against known contacts, and classify intent.
5. A **Decision** is reached to Block or Forward the call.
6. The entire process is streamed via **WebSockets** to the live dashboard.

## Folder Structure
- `main.py` — FastAPI application entry point.
- `config.py` — Application configuration and defaults.
- `seed_data.py` — Script to populate the database with realistic past call history.
- `database/` — SQLite setup and SQLAlchemy models (`models.py`, `db.py`).
- `services/`
  - `simulator.py` — Call simulator engine with 20 caller profiles.
  - `ai_agent.py` — AI conversation engine using Ollama.
  - `risk_engine.py` — Heuristic scoring logic.
  - `auth_checks.py` — 5-stage authentication check pipeline.
  - `language.py` — Zero-cost text language detection.
- `routers/` — FastAPI endpoint definitions for calls, settings, websockets, and simulator.
- `ws/` — WebSocket connection manager.
- `static/index.html` — The complete Single Page Application dashboard.
