"""
Scenario Routes — Demo scenario triggers for hackathon presentation.
Allows triggering simulated equipment degradation scenarios to demonstrate
proactive failure detection and real-time response.
"""

import asyncio
import random
from datetime import datetime
from fastapi import APIRouter
from pydantic import BaseModel

from data.database import (
    insert_alert, update_equipment_status, get_all_equipment,
    insert_maintenance_log
)
from data.sensor_simulator import broadcast_to_clients, degradation_state
import config

router = APIRouter(prefix="/api/scenarios", tags=["scenarios"])


SCENARIOS = {
    "blast_furnace_overheat": {
        "name": "Blast Furnace Tuyere Overheat",
        "description": "Simulates tuyere zone temperature spike in BF-001, triggering critical alerts and emergency shutdown recommendation.",
        "equipment_id": "BF-001",
        "severity": "critical",
        "alerts": [
            {"severity": "critical", "title": "🔥 Critical Temperature — Blast Furnace #1", "message": "Tuyere zone temperature has exceeded 1,450°C critical threshold. Immediate inspection required. Risk of refractory damage and hot metal breakout."},
            {"severity": "high", "title": "⚠️ Vibration Anomaly — Blast Furnace #1", "message": "Abnormal vibration pattern detected in cooling staves. Possible thermal stress fracture developing."},
        ],
        "status_change": "critical",
    },
    "caster_bearing_seizure": {
        "name": "Continuous Caster Bearing Seizure",
        "description": "Simulates progressive bearing degradation in CCM-001, demonstrating RUL prediction and proactive maintenance.",
        "equipment_id": "CCM-001",
        "severity": "high",
        "alerts": [
            {"severity": "high", "title": "🔩 Bearing Vibration Spike — Continuous Caster", "message": "Segment roller bearing vibration at 12.5 mm/s — exceeds warning threshold of 8.0 mm/s. Bearing degradation accelerating. Estimated RUL: 36 hours."},
            {"severity": "medium", "title": "🌡️ Bearing Temperature Rising — Continuous Caster", "message": "Bearing housing temperature rising at 2.5°C/hr. Current: 78°C (warn: 75°C). Lubrication inspection recommended."},
        ],
        "status_change": "warning",
    },
    "rolling_mill_vibration": {
        "name": "Hot Rolling Mill Vibration Spike",
        "description": "Simulates work roll chock vibration spike in HRM-001, indicating potential bearing failure.",
        "equipment_id": "HRM-001",
        "severity": "high",
        "alerts": [
            {"severity": "high", "title": "📊 Work Roll Vibration Critical — Hot Rolling Mill", "message": "Work roll chock vibration spiked to 15.2 mm/s (critical threshold: 12.0 mm/s). Potential roll bearing cage failure. Production quality may be affected."},
            {"severity": "medium", "title": "⚡ Motor Current Fluctuation — Hot Rolling Mill", "message": "Main drive motor current showing 18% fluctuation above baseline. Possible roll gap irregularity or strip tension anomaly."},
        ],
        "status_change": "warning",
    },
    "cooling_tower_failure": {
        "name": "Cooling Tower Pump Failure",
        "description": "Simulates cooling water flow drop in CT-001, creating cascading risk to Continuous Caster and BOF.",
        "equipment_id": "CT-001",
        "severity": "critical",
        "alerts": [
            {"severity": "critical", "title": "💧 Cooling Water Flow Drop — Cooling Tower #3", "message": "Cooling water flow rate dropped to 45% of nominal. Primary circulation pump P3A showing cavitation signatures. Risk of overheating in CCM-001 and BOF-001."},
            {"severity": "high", "title": "🌡️ Return Water Temperature Rising — Cooling Tower #3", "message": "Cooling water return temperature at 52°C (warn: 48°C). Insufficient heat dissipation. Downstream equipment thermal risk increasing."},
        ],
        "status_change": "critical",
    },
}


class ScenarioRequest(BaseModel):
    scenario_id: str


@router.get("/list")
async def list_scenarios():
    """List all available demo scenarios."""
    scenarios_list = []
    for sid, scenario in SCENARIOS.items():
        scenarios_list.append({
            "id": sid,
            "name": scenario["name"],
            "description": scenario["description"],
            "equipment_id": scenario["equipment_id"],
            "severity": scenario["severity"],
        })
    return {"success": True, "data": scenarios_list}


@router.post("/trigger")
async def trigger_scenario(req: ScenarioRequest):
    """
    Trigger a demo scenario. This will:
    1. Update equipment status
    2. Inject degradation into the sensor simulator
    3. Generate alerts
    4. Broadcast real-time updates
    """
    scenario = SCENARIOS.get(req.scenario_id)
    if not scenario:
        return {"success": False, "error": f"Unknown scenario: {req.scenario_id}"}
    
    eq_id = scenario["equipment_id"]
    
    # 1. Update equipment status
    update_equipment_status(eq_id, scenario["status_change"])
    
    # 2. Inject degradation into sensor simulator state
    for key in list(degradation_state.keys()):
        if key.startswith(eq_id):
            degradation_state[key]["level"] = min(degradation_state[key]["level"] + 0.6, 1.0)
            degradation_state[key]["trend"] = 0.02  # Strong upward trend
    
    # 3. Generate alerts
    alert_ids = []
    for alert_def in scenario["alerts"]:
        alert_id = insert_alert(
            eq_id,
            alert_def["severity"],
            alert_def["title"],
            alert_def["message"]
        )
        alert_ids.append(alert_id)
        
        # Broadcast alert via WebSocket
        loop = getattr(config, "LOOP", None)
        if loop and loop.is_running():
            asyncio.run_coroutine_threadsafe(
                broadcast_to_clients({
                    "type": "alert",
                    "data": {
                        "id": alert_id,
                        "equipment_id": eq_id,
                        "equipment_name": scenario["name"].split(" — ")[0],
                        "severity": alert_def["severity"],
                        "title": alert_def["title"],
                        "message": alert_def["message"],
                        "timestamp": datetime.now().isoformat(),
                        "is_scenario": True,
                    }
                }),
                loop
            )
    
    # 4. Log the scenario trigger as a maintenance event
    insert_maintenance_log(
        eq_id,
        "corrective",
        f"[SCENARIO] {scenario['name']} triggered for demo. {len(scenario['alerts'])} alerts generated.",
        outcome="Pending investigation",
        performed_by="AI Scenario Engine",
    )
    
    return {
        "success": True,
        "data": {
            "scenario": scenario["name"],
            "equipment_id": eq_id,
            "status_change": scenario["status_change"],
            "alerts_generated": len(alert_ids),
            "alert_ids": alert_ids,
            "message": f"🎯 Scenario '{scenario['name']}' triggered! Check Alerts and Dashboard for real-time updates.",
        }
    }


@router.post("/reset")
async def reset_scenarios():
    """Reset all equipment to operational status and clear degradation."""
    equipment_list = get_all_equipment()
    for eq in equipment_list:
        update_equipment_status(eq["id"], "operational")
        # Reset degradation state
        for key in list(degradation_state.keys()):
            if key.startswith(eq["id"]):
                degradation_state[key]["level"] = 0.0
                degradation_state[key]["trend"] = 0.0
    
    return {
        "success": True,
        "data": {"message": "All equipment reset to operational. Degradation state cleared."}
    }
