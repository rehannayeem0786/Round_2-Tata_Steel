"""
Action Agent — Parses natural language to extract and execute actions
such as ordering parts or shutting down equipment.
"""

import json
from datetime import datetime
from langchain.prompts import ChatPromptTemplate
from agents.llm_provider import get_llm, invoke_with_retry
from data.database import insert_action_log
from data.sensor_simulator import broadcast_to_clients
import config
import asyncio

ACTION_PROMPT = """You are an AI Action Agent for a steel plant. Your job is to execute a specific action requested by the user.

Available actions:
1. "order_part": Order a replacement part from the inventory or ERP system.
   Requires: equipment_id (e.g. 'BF-001', 'CCM-001', etc.), part_name, quantity
2. "shutdown_equipment": Send an emergency stop command to equipment.
   Requires: equipment_id (e.g. 'BF-001', 'CCM-001', etc.)
3. "dispatch_technician": Send a maintenance technician to a specific area.
   Requires: equipment_id (e.g. 'BF-001', 'CCM-001', etc.), priority (high/medium/low)

Analyze the user's query and the context to determine the appropriate action to take. 
If the user specifies an action that matches one of the above, return a JSON object with:
- "action": the name of the action (e.g. "order_part")
- "params": a dictionary of the required parameters (e.g. {{"equipment_id": "CCM-001", "part_name": "bearing", "quantity": 1}})
- "reasoning": brief explanation of why this action is taken

If the request is ambiguous or missing required parameters, do NOT execute. Instead, return "action": "none" and ask the user for clarification in the "reasoning".

Respond ONLY with valid JSON.

USER QUERY: {query}
CONTEXT:
{context}
"""

def safe_broadcast(message):
    loop = getattr(config, "LOOP", None)
    if loop and loop.is_running():
        asyncio.run_coroutine_threadsafe(broadcast_to_clients(message), loop)
    else:
        try:
            new_loop = asyncio.new_event_loop()
            new_loop.run_until_complete(broadcast_to_clients(message))
            new_loop.close()
        except Exception as e:
            print(f"[ERR] safe_broadcast failed: {e}")

def _resolve_equipment_id(params):
    eq_id = params.get("equipment_id") or params.get("equipment_name") or params.get("location")
    if not eq_id:
        return "BF-001"
    eq_id = str(eq_id).upper().strip()
    valid_ids = ["BF-001", "BOF-001", "LF-001", "CCM-001", "HRM-001", "CRM-001", "CT-001", "CR-001", "HP-001", "GR-001"]
    if eq_id in valid_ids:
        return eq_id
    
    mapping = {
        "BLAST FURNACE": "BF-001",
        "BF": "BF-001",
        "BOF": "BOF-001",
        "CONVERTER": "BOF-001",
        "LADLE": "LF-001",
        "LF": "LF-001",
        "CASTER": "CCM-001",
        "CCM": "CCM-001",
        "CONTINUOUS CASTER": "CCM-001",
        "HOT ROLLING": "HRM-001",
        "HRM": "HRM-001",
        "HOT MILL": "HRM-001",
        "COLD ROLLING": "CRM-001",
        "CRM": "CRM-001",
        "COLD MILL": "CRM-001",
        "COOLING TOWER": "CT-001",
        "CRANE": "CR-001",
        "HYDRAULIC PRESS": "HP-001",
        "GAS RECOVERY": "GR-001"
    }
    for k, v in mapping.items():
        if k in eq_id:
            return v
    return "BF-001"

def _execute_order_part(params):
    equipment_id = _resolve_equipment_id(params)
    part_name = params.get("part_name", "Unknown Part")
    qty = params.get("quantity", 1)
    details = f"Order {qty}x {part_name} for {equipment_id}"
    
    action_id = insert_action_log(equipment_id, "order_part", details, "pending")
    
    safe_broadcast({
        "type": "action_log",
        "data": {
            "id": action_id,
            "equipment_id": equipment_id,
            "action_type": "order_part",
            "details": details,
            "status": "pending",
            "timestamp": datetime.now().isoformat()
        }
    })
    return f"✅ **PO GENERATED:** Successfully generated pending purchase order for {qty}x {part_name} (Equipment: {equipment_id}). Reference ID: ACT-{action_id:04d}."

def _execute_shutdown_equipment(params):
    equipment_id = _resolve_equipment_id(params)
    details = f"Emergency stop command dispatched to {equipment_id} via SCADA"
    
    action_id = insert_action_log(equipment_id, "shutdown_equipment", details, "pending")
    
    safe_broadcast({
        "type": "action_log",
        "data": {
            "id": action_id,
            "equipment_id": equipment_id,
            "action_type": "shutdown_equipment",
            "details": details,
            "status": "pending",
            "timestamp": datetime.now().isoformat()
        }
    })
    return f"🛑 **EMERGENCY ACTION GENERATED:** Shutdown request queued for {equipment_id}. Reference ID: ACT-{action_id:04d}. Awaiting supervisor/manager approval."

def _execute_dispatch_technician(params):
    equipment_id = _resolve_equipment_id(params)
    priority = params.get("priority", "medium")
    details = f"Dispatch technician to {equipment_id} with {priority} priority"
    
    action_id = insert_action_log(equipment_id, "dispatch_technician", details, "pending")
    
    safe_broadcast({
        "type": "action_log",
        "data": {
            "id": action_id,
            "equipment_id": equipment_id,
            "action_type": "dispatch_technician",
            "details": details,
            "status": "pending",
            "timestamp": datetime.now().isoformat()
        }
    })
    return f"👷 **DISPATCH QUEUED:** Technician ticket created for {equipment_id} ({priority} priority). Reference ID: ACT-{action_id:04d}."

def run_action(query: str, context: str, conversation_history: list) -> str:
    """Determine and execute an action based on the query."""
    llm = get_llm(temperature=0.0)
    if not llm:
        return "⚠️ Action Agent requires an active LLM connection to parse actions safely."

    prompt = ChatPromptTemplate.from_template(ACTION_PROMPT)
    chain = prompt | llm

    try:
        response_text = invoke_with_retry(chain, query=query, context=context)
        cleaned = response_text.replace("```json", "").replace("```", "").strip()
        result = json.loads(cleaned)
        
        action = result.get("action", "none")
        params = result.get("params", {})
        reasoning = result.get("reasoning", "")
        
        if action == "order_part":
            return _execute_order_part(params) + f"\n\n*Reasoning:* {reasoning}"
        elif action == "shutdown_equipment":
            return _execute_shutdown_equipment(params) + f"\n\n*Reasoning:* {reasoning}"
        elif action == "dispatch_technician":
            return _execute_dispatch_technician(params) + f"\n\n*Reasoning:* {reasoning}"
        else:
            return f"❓ **ACTION CANCELLED:** {reasoning}"
            
    except Exception as e:
        print(f"[ERR] Action Agent Error: {e}")
        return "⚠️ Failed to execute action due to a processing error."
