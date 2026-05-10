"""
Simulator API router — POST /api/simulate and /api/simulate/auto
"""
import asyncio
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from typing import Optional
from services.simulator import simulate_call, get_all_profiles
from ws.ws_manager import manager

router = APIRouter(prefix="/api", tags=["simulator"])

# Track the active simulation
_active_simulation = {"running": False, "call_id": None}


class SimulateRequest(BaseModel):
    profile_id: Optional[int] = None


class AutoSimulateRequest(BaseModel):
    enabled: bool
    interval_seconds: int = 30


@router.post("/simulate")
async def trigger_simulation(
    request: SimulateRequest,
    background_tasks: BackgroundTasks
):
    """Trigger a single simulated call and stream it to the dashboard."""
    if _active_simulation["running"]:
        raise HTTPException(status_code=409, detail="A simulation is already running. Please wait.")

    _active_simulation["running"] = True
    _active_simulation["call_id"] = None

    async def run():
        try:
            result = await simulate_call(
                profile_id=request.profile_id,
                ws_callback=manager.broadcast
            )
            _active_simulation["call_id"] = result.get("id")
        except Exception as e:
            await manager.broadcast("error", {"message": str(e)})
        finally:
            _active_simulation["running"] = False

    background_tasks.add_task(run)
    return {"status": "started", "message": "Simulation started. Watch the Live tab."}


@router.get("/simulate/status")
async def simulation_status():
    """Get the status of the current simulation."""
    return {
        "running": _active_simulation["running"],
        "call_id": _active_simulation["call_id"],
    }


@router.get("/simulate/profiles")
async def get_profiles():
    """Get all available caller profiles for the simulator."""
    return {"profiles": get_all_profiles()}


@router.get("/ollama/status")
async def ollama_status():
    """Check if Ollama is available."""
    from services.ai_agent import check_ollama_available
    available = await check_ollama_available()
    return {
        "available": available,
        "status": "Connected" if available else "Offline (using fallback mock responses)",
        "model": "llama3" if available else "mock"
    }
