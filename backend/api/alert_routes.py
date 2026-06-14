"""
Alert API routes — Alert management, acknowledgement, and resolution.
"""

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
from data.database import get_alerts, get_alert_by_id, acknowledge_alert, resolve_alert
from agents.logbook_agent import generate_logbook_entry

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


class AlertActionRequest(BaseModel):
    action: str  # 'acknowledge' or 'resolve'


@router.get("")
async def list_alerts(
    severity: Optional[str] = None,
    acknowledged: Optional[bool] = None,
    limit: int = Query(default=50, le=200)
):
    """Get alerts with optional filtering."""
    alerts = get_alerts(acknowledged=acknowledged, severity=severity, limit=limit)
    return {"success": True, "data": alerts}


@router.get("/active")
async def active_alerts():
    """Get all unresolved alerts."""
    alerts = get_alerts(acknowledged=None, limit=100)
    # Filter to unresolved only
    active = [a for a in alerts if not a.get("resolved")]
    return {"success": True, "data": active}


@router.post("/{alert_id}")
async def update_alert(alert_id: int, request: AlertActionRequest, background_tasks: BackgroundTasks):
    """Acknowledge or resolve an alert."""
    if request.action == "acknowledge":
        acknowledge_alert(alert_id)
        return {"success": True, "message": f"Alert {alert_id} acknowledged"}
    elif request.action == "resolve":
        resolve_alert(alert_id)
        
        # Trigger automatic logbook entry generation in the background
        alert = get_alert_by_id(alert_id)
        if alert:
            background_tasks.add_task(generate_logbook_entry, alert)
            
        return {"success": True, "message": f"Alert {alert_id} resolved. Logbook entry generating."}
    else:
        raise HTTPException(status_code=400, detail="Action must be 'acknowledge' or 'resolve'")
