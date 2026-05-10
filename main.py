"""
FastAPI application entry point for ShieldCall AI.
"""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from database.db import init_db
from routers import websocket, simulator_api, calls_api, settings_api

app = FastAPI(
    title="ShieldCall AI",
    description="AI-powered call screening and authentication system",
    version="1.0.0",
)

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    init_db()

# Mount API routers
app.include_router(websocket.router)
app.include_router(simulator_api.router)
app.include_router(calls_api.router)
app.include_router(settings_api.router)

# Serve static dashboard
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def serve_dashboard():
    return FileResponse("static/index.html")

@app.get("/health")
async def health():
    return {"status": "ok", "service": "ShieldCall AI"}
