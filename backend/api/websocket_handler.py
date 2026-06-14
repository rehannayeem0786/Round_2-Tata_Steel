"""
WebSocket handler — Manages real-time connections for sensor data
streaming and alert notifications.
"""

from fastapi import WebSocket, WebSocketDisconnect
from data.sensor_simulator import get_connected_clients


async def websocket_endpoint(websocket: WebSocket):
    """Handle WebSocket connections for real-time updates."""
    await websocket.accept()
    clients = get_connected_clients()
    clients.add(websocket)
    print(f"[WS] Client connected (total: {len(clients)})")
    
    try:
        while True:
            # Keep connection alive, listen for client messages
            data = await websocket.receive_text()
            
            # Client can send ping/pong to keep alive
            if data == "ping":
                await websocket.send_text('{"type": "pong"}')
    
    except WebSocketDisconnect:
        clients = get_connected_clients()
        clients.discard(websocket)
        print(f"[WS] Client disconnected (total: {len(clients)})")
    except Exception as e:
        clients = get_connected_clients()
        clients.discard(websocket)
        print(f"[ERR] WebSocket error: {e}")
