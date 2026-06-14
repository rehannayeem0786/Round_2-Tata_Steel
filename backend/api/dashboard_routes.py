"""
Dashboard API routes — Equipment data, sensor readings, metrics,
and plant-wide statistics for the dashboard view.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from pydantic import BaseModel
from data.database import (
    get_all_equipment, get_equipment_by_id,
    get_latest_sensor_readings, get_sensor_readings_by_metric,
    get_maintenance_logs, get_dashboard_stats,
    get_action_logs, update_action_status,
    get_equipment_health_score
)

class ActionStatusUpdate(BaseModel):
    status: str

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/stats")
async def dashboard_stats():
    """Get aggregated dashboard statistics."""
    stats = get_dashboard_stats()
    return {"success": True, "data": stats}


@router.get("/equipment")
async def list_equipment():
    """Get all equipment with current status and health scores."""
    equipment = get_all_equipment()
    # Attach health score to each equipment
    for eq in equipment:
        try:
            eq["health"] = get_equipment_health_score(eq["id"])
        except Exception:
            eq["health"] = {"score": 50, "grade": "C", "label": "Fair", "factors": {}}
    return {"success": True, "data": equipment}


@router.get("/equipment/{equipment_id}")
async def get_equipment(equipment_id: str):
    """Get detailed information for a specific equipment."""
    equipment = get_equipment_by_id(equipment_id)
    if not equipment:
        raise HTTPException(status_code=404, detail="Equipment not found")
    
    # Include latest sensor readings
    sensors = get_latest_sensor_readings(equipment_id, limit=50)
    
    # Include maintenance history
    maintenance = get_maintenance_logs(equipment_id, limit=10)
    
    # Include health score
    health = get_equipment_health_score(equipment_id)
    
    return {
        "success": True,
        "data": {
            "equipment": equipment,
            "sensors": sensors,
            "maintenance": maintenance,
            "health": health,
        }
    }


@router.get("/equipment/{equipment_id}/sensors")
async def get_equipment_sensors(
    equipment_id: str,
    metric: Optional[str] = None,
    limit: int = Query(default=100, le=500)
):
    """Get sensor readings for an equipment."""
    if metric:
        readings = get_sensor_readings_by_metric(equipment_id, metric, limit)
    else:
        readings = get_latest_sensor_readings(equipment_id, limit)
    
    return {"success": True, "data": readings}


@router.get("/maintenance")
async def list_maintenance_logs(
    equipment_id: Optional[str] = None,
    limit: int = Query(default=50, le=200)
):
    """Get maintenance logs, optionally filtered by equipment."""
    logs = get_maintenance_logs(equipment_id, limit)
    return {"success": True, "data": logs}


@router.get("/actions")
async def list_actions(
    equipment_id: Optional[str] = None,
    limit: int = Query(default=50, le=200)
):
    """Get recent action logs."""
    actions = get_action_logs(equipment_id, limit)
    return {"success": True, "data": actions}


@router.post("/actions/{action_id}/status")
async def change_action_status(action_id: int, payload: ActionStatusUpdate):
    """Update action status (e.g. approve/reject PO, execute SCADA shutdown)."""
    update_action_status(action_id, payload.status)
    
    # Broadcast action update to websocket clients
    from agents.action_agent import safe_broadcast
    from data.database import get_connection
    try:
        conn = get_connection()
        action = conn.execute("SELECT al.*, e.name as equipment_name FROM action_logs al JOIN equipment e ON al.equipment_id = e.id WHERE al.id = ?", (action_id,)).fetchone()
        conn.close()
        if action:
            act_dict = dict(action)
            safe_broadcast({
                "type": "action_log_update",
                "data": act_dict
            })
    except Exception as e:
        print(f"[ERR] Failed to broadcast status update: {e}")
        
    return {"success": True, "message": f"Action status updated to {payload.status}"}

