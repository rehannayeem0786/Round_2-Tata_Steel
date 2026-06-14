"""
Logbook Agent — Automatically generates structured digital logbook entries
when an alert is resolved or maintenance is completed.
"""
import json
from langchain.prompts import ChatPromptTemplate
from agents.llm_provider import get_llm, invoke_with_retry
from data.database import insert_maintenance_log, get_equipment_by_id

LOGBOOK_PROMPT = """You are an AI Maintenance Logbook Agent.
Your job is to generate a structured maintenance log entry based on an alert that has just been resolved.

ALERT DETAILS:
Title: {alert_title}
Message: {alert_message}
Severity: {alert_severity}
Equipment: {equipment_name} (ID: {equipment_id})

Generate a highly professional, concise maintenance log entry summarizing the likely issue and resolution.
Since you don't know the exact human action taken, assume a standard preventative/corrective action was taken by the "AI Automation System" or standard shift engineer.

Respond ONLY with a valid JSON object matching this schema:
{{
    "log_type": "Corrective" or "Preventive" or "Inspection",
    "description": "Brief description of the fault and action taken (max 2 sentences)",
    "outcome": "Resolved / Equipment operational",
    "duration_hours": 1.5 (estimate a reasonable number of hours),
    "parts_replaced": "None" or a realistic guess if the alert implies a broken part
}}
"""

def generate_logbook_entry(alert: dict) -> bool:
    """
    Generate and save a logbook entry for a resolved alert.
    """
    equipment = get_equipment_by_id(alert["equipment_id"])
    if not equipment:
        return False

    llm = get_llm(temperature=0.2)
    if not llm:
        # Fallback log creation
        insert_maintenance_log(
            equipment_id=alert["equipment_id"],
            log_type="Corrective",
            description=f"Auto-resolved alert: {alert['title']}. {alert['message']}",
            outcome="Resolved",
            performed_by="System (Auto)",
            duration_hours=0.5,
            parts_replaced="None"
        )
        return True

    prompt = ChatPromptTemplate.from_template(LOGBOOK_PROMPT)
    chain = prompt | llm

    try:
        response_text = invoke_with_retry(chain, 
            alert_title=alert["title"],
            alert_message=alert["message"],
            alert_severity=alert["severity"],
            equipment_name=equipment["name"],
            equipment_id=equipment["id"]
        )
        
        # Parse JSON
        cleaned = response_text.replace("```json", "").replace("```", "").strip()
        result = json.loads(cleaned)
        
        insert_maintenance_log(
            equipment_id=alert["equipment_id"],
            log_type=result.get("log_type", "Corrective"),
            description=result.get("description", f"Resolved alert: {alert['title']}"),
            outcome=result.get("outcome", "Resolved"),
            performed_by="AI Logbook Agent",
            duration_hours=float(result.get("duration_hours", 1.0)),
            parts_replaced=result.get("parts_replaced", "None")
        )
        print(f"[LOGBOOK] Auto-generated log entry for alert {alert['id']}")
        return True
        
    except Exception as e:
        print(f"[ERR] Logbook agent error: {e}")
        # Fallback
        insert_maintenance_log(
            equipment_id=alert["equipment_id"],
            log_type="Corrective",
            description=f"Auto-resolved alert: {alert['title']}",
            outcome="Resolved",
            performed_by="System (Fallback)",
            duration_hours=1.0,
            parts_replaced="None"
        )
        return False
