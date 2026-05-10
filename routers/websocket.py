"""
WebSocket router — /ws/live endpoint for real-time dashboard streaming.
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from ws.ws_manager import manager

router = APIRouter()


@router.websocket("/ws/live")
async def websocket_live(websocket: WebSocket):
    """
    WebSocket endpoint for live call screening stream.
    The dashboard connects here and receives events:
      call_started | transcript_line | language_detected |
      check_update | risk_update | decision | call_complete
    """
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive; listen for client messages (e.g., action commands)
            data = await websocket.receive_text()
            # Echo back or handle action messages from dashboard
            # (Block Now / Forward Now actions are handled via REST API)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)
