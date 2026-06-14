"""
Agent Orchestrator — Routes user queries to the appropriate agents
using intent classification and manages the multi-agent workflow.
Uses a state-machine approach for deterministic routing with LLM-based
intent classification.
"""

import re
import uuid
import time
from datetime import datetime

from knowledge.rag_engine import retrieve_context, format_context_for_llm
from agents.diagnostic_agent import run_diagnosis
from agents.risk_agent import run_risk_assessment
from agents.recommendation_agent import run_recommendation
from agents.reporting_agent import run_report
from agents.alerting_agent import analyze_alerts
from agents.feedback_agent import get_feedback_context
from agents.cost_agent import run_cost_analysis
from data.database import (
    create_conversation, get_conversation,
    update_conversation_messages, get_all_equipment
)


import json
from langchain.prompts import ChatPromptTemplate
from agents.llm_provider import get_llm, invoke_with_retry

# ─── LLM Intent Classification ──────────────────────────────────────────────

INTENT_CLASSIFICATION_PROMPT = """You are an AI orchestrator for an Intelligent Maintenance Wizard in a steel plant.
Your job is to classify the user's intent into exactly ONE of the following categories:

1. "diagnostic": The user is asking about a fault, identifying a problem, root cause analysis, or remaining useful life (RUL). Example: "Why is the continuous caster vibrating?"
2. "risk": The user is asking about risk levels, urgency, or safety consequences. Example: "How dangerous is this fault?"
3. "recommendation": The user is asking for steps to fix a problem, maintenance procedures, or spare parts. Example: "How do I replace the bearing?"
4. "report": The user is asking for a summary, status report, or overview of the plant/equipment. Example: "Generate a weekly maintenance report."
5. "alert": The user is asking about current active alerts or alarms. Example: "Show me all critical alerts."
6. "cost": The user is asking about cost impact, financial analysis, downtime cost, ROI, business impact, or production loss. Example: "What is the cost impact of this failure?", "Calculate the ROI of preventive maintenance."
7. "action": The user is commanding the AI to perform a physical or systematic action, such as ordering a part, shutting down a machine, or dispatching a technician. Example: "Order a replacement bearing", "Shut down the continuous caster immediately."
8. "general": Greetings, listing all equipment, or asking what you can do. Example: "Hello", "Show all equipment".

Respond ONLY with a valid JSON object containing a single key "intent", whose value is one of the 8 strings above. No other text.

USER QUERY: {query}
"""

def classify_intent(query: str) -> str:
    """
    Classify the user's query intent using an LLM.
    Returns one of: diagnostic, risk, recommendation, report, alert, general
    """
    llm = get_llm(temperature=0.0) # Low temperature for classification
    if not llm:
        # Fallback to a simple heuristic if LLM fails
        query_lower = query.lower()
        if any(w in query_lower for w in ["cost", "financial", "roi", "downtime cost", "business impact", "production loss", "money", "rupee", "₹", "savings", "investment"]): return "cost"
        if any(w in query_lower for w in ["order", "purchase", "shut down", "shutdown", "stop", "dispatch", "send technician"]): return "action"
        if any(w in query_lower for w in ["risk", "dangerous", "urgent"]): return "risk"
        if any(w in query_lower for w in ["fix", "how to", "replace", "repair"]): return "recommendation"
        if any(w in query_lower for w in ["report", "summary"]): return "report"
        if any(w in query_lower for w in ["alert", "alarm"]): return "alert"
        if any(w in query_lower for w in ["hello", "hi", "help", "list"]): return "general"
        return "diagnostic"

    prompt = ChatPromptTemplate.from_template(INTENT_CLASSIFICATION_PROMPT)
    chain = prompt | llm
    
    try:
        response_text = invoke_with_retry(chain, query=query)
        # Parse JSON
        try:
            # Clean up potential markdown formatting like ```json
            cleaned = response_text.replace("```json", "").replace("```", "").strip()
            result = json.loads(cleaned)
            intent = result.get("intent", "diagnostic").lower()
            valid_intents = ["diagnostic", "risk", "recommendation", "report", "alert", "cost", "action", "general"]
            if intent in valid_intents:
                return intent
        except json.JSONDecodeError:
            pass
    except Exception as e:
        print(f"[ERR] Intent classification error: {e}")
        
    return "diagnostic" # Default fallback


def detect_equipment(query: str) -> str:
    """Try to detect which equipment the user is asking about."""
    query_lower = query.lower()
    equipment_list = get_all_equipment()
    
    for eq in equipment_list:
        # Check equipment ID
        if eq["id"].lower() in query_lower:
            return eq["id"]
        
        # Check equipment name keywords
        name_words = eq["name"].lower().split()
        if any(word in query_lower for word in name_words if len(word) > 3):
            return eq["id"]
        
        # Check equipment type
        type_words = eq["type"].lower().split()
        if any(word in query_lower for word in type_words if len(word) > 3):
            return eq["id"]
    
    return None


# ─── Main Orchestration ─────────────────────────────────────────────────────

# ─── Role-Specific Context Instructions ──────────────────────────────────────

ROLE_INSTRUCTIONS = {
    "engineer": """[ROLE CONTEXT: FIELD ENGINEER]
You are responding to a Field Engineer who works hands-on with equipment on the plant floor.
ADAPT YOUR RESPONSE STYLE:
- Focus on practical, step-by-step procedures they can execute immediately
- Include specific safety precautions (LOTO, PPE, temperature limits)
- List exact spare parts with specifications (bearing型号, grease type, bolt sizes)
- Provide clear "DO THIS NOW" vs "SCHEDULE LATER" separation
- Use technical terminology freely (they understand it)
- Include tool requirements and estimated duration for each step
- Reference specific SOP document numbers when available
""",
    "supervisor": """[ROLE CONTEXT: SHIFT SUPERVISOR]
You are responding to a Shift Supervisor who manages the operations team and makes real-time decisions.
ADAPT YOUR RESPONSE STYLE:
- Focus on operational decisions: which equipment to prioritize, which to defer
- Provide team coordination guidance (who to assign, how many people needed)
- Include production impact: how this affects the shift's production targets
- Give clear priority rankings (do this first, this second, this can wait)
- Summarize key action items in a checklist format
- Include escalation criteria: when to call the plant manager
- Balance safety urgency with production continuity
""",
    "manager": """[ROLE CONTEXT: PLANT MANAGER]
You are responding to a Plant Manager who oversees the entire plant and makes strategic decisions.
ADAPT YOUR RESPONSE STYLE:
- Focus on business impact: downtime cost in ₹, production loss in tonnes, ROI of actions
- Provide strategic-level summaries (not step-by-step procedures)
- Include KPI impact: how this affects OEE, uptime percentage, safety metrics
- Compare preventive vs reactive cost implications
- Give investment recommendations with payback periods
- Highlight cascading plant-wide effects and inter-equipment dependencies
- Include compliance and regulatory considerations
- Present data in executive summary format with key metrics
""",
}


def process_query(query: str, conversation_id: str = None, user_role: str = "engineer", image_data: str = None) -> dict:
    """
    Main orchestration function. Routes the query through the appropriate
    agent pipeline and returns a structured response with execution trace.
    
    Args:
        query: User's natural language query
        conversation_id: Optional existing conversation ID
        user_role: The role of the user (e.g. 'engineer', 'supervisor', 'manager')
        image_data: Base64 image string for vision capabilities
        
    Returns:
        dict with response, intent, agents_used, execution_trace, conversation_id
    """
    pipeline_start = time.time()
    execution_trace = []
    
    # 1. Create or retrieve conversation
    if not conversation_id:
        conversation_id = str(uuid.uuid4())
        create_conversation(conversation_id, title=query[:100])
    
    conversation = get_conversation(conversation_id)
    if not conversation:
        create_conversation(conversation_id, title=query[:100])
        conversation = {"messages": []}
    
    conversation_history = conversation.get("messages", [])
    
    # 2. Classify intent (with timing)
    t0 = time.time()
    intent = classify_intent(query)
    execution_trace.append({
        "step": 1,
        "agent": "Intent Classifier",
        "action": f"Classified as '{intent}'",
        "result": intent,
        "time_ms": round((time.time() - t0) * 1000),
        "status": "done"
    })
    
    # 3. Detect equipment (with timing)
    t0 = time.time()
    equipment_id = detect_equipment(query)
    execution_trace.append({
        "step": 2,
        "agent": "Equipment Detector",
        "action": f"Detected: {equipment_id or 'Plant-wide query'}",
        "result": equipment_id or "none",
        "time_ms": round((time.time() - t0) * 1000),
        "status": "done"
    })
    
    # 4. Retrieve context via RAG (with timing)
    t0 = time.time()
    context_data = retrieve_context(query, equipment_id)
    kb_count = len(context_data.get("knowledge_context", []))
    sensor_count = len(context_data.get("sensor_context", []))
    execution_trace.append({
        "step": 3,
        "agent": "RAG Engine",
        "action": f"Retrieved {kb_count} docs + {sensor_count} sensor readings",
        "result": f"{kb_count} knowledge, {sensor_count} sensors",
        "time_ms": round((time.time() - t0) * 1000),
        "status": "done"
    })
    
    # Add role-specific instructions to context
    role_instruction = ROLE_INSTRUCTIONS.get(user_role, ROLE_INSTRUCTIONS["engineer"])
    formatted_context = role_instruction + "\n" + format_context_for_llm(context_data)

    # Inject ML anomaly-detection findings so agent reasoning is explainable
    # and traceable to the predictive model (not just thresholds).
    detected_eq = context_data.get("detected_equipment_id")
    if detected_eq:
        try:
            from ml.anomaly_detector import format_anomaly_context
            ml_ctx = format_anomaly_context(detected_eq)
            if ml_ctx:
                formatted_context += "\n" + ml_ctx.replace("{", "{{").replace("}", "}}")
        except Exception as e:
            print(f"[WARN] ML anomaly context unavailable (non-fatal): {e}")
    
    # Add feedback context for improvement
    feedback_context = get_feedback_context()
    if feedback_context:
        formatted_context += f"\n\n{feedback_context}"
    
    # 5. Route to appropriate agent(s) and pass state between them
    agents_used = []
    response_parts = []
    step_num = 4
    
    def _run_agent_with_trace(agent_name, agent_fn, *args, **kwargs):
        nonlocal step_num
        t_start = time.time()
        execution_trace.append({
            "step": step_num,
            "agent": agent_name,
            "action": "Processing...",
            "result": "",
            "time_ms": 0,
            "status": "running"
        })
        trace_idx = len(execution_trace) - 1
        
        result = agent_fn(*args, **kwargs)
        elapsed = round((time.time() - t_start) * 1000)
        
        # Extract a brief summary (first meaningful line)
        summary = ""
        for line in result.split("\n"):
            clean = line.strip().strip("#").strip("*").strip()
            if clean and len(clean) > 10 and not clean.startswith("---"):
                summary = clean[:80]
                break
        
        execution_trace[trace_idx].update({
            "action": summary or f"{agent_name} completed",
            "result": summary[:60] if summary else "Analysis complete",
            "time_ms": elapsed,
            "status": "done"
        })
        step_num += 1
        agents_used.append(agent_name)
        response_parts.append(result)
        return result
    
    if intent == "diagnostic":
        diag_response = _run_agent_with_trace("Diagnostic Agent", run_diagnosis, query, formatted_context, conversation_history, image_data=image_data)
        risk_context = formatted_context + f"\n\n[PREVIOUS AGENT OUTPUT - DIAGNOSIS]:\n{diag_response}"
        risk_response = _run_agent_with_trace("Risk Agent", run_risk_assessment, query, risk_context, conversation_history)
        rec_context = risk_context + f"\n\n[PREVIOUS AGENT OUTPUT - RISK]:\n{risk_response}"
        _run_agent_with_trace("Recommendation Agent", run_recommendation, query, rec_context, conversation_history)
    
    elif intent == "risk":
        risk_response = _run_agent_with_trace("Risk Agent", run_risk_assessment, query, formatted_context, conversation_history)
        rec_context = formatted_context + f"\n\n[PREVIOUS AGENT OUTPUT - RISK]:\n{risk_response}"
        _run_agent_with_trace("Recommendation Agent", run_recommendation, query, rec_context, conversation_history)
    
    elif intent == "recommendation":
        _run_agent_with_trace("Recommendation Agent", run_recommendation, query, formatted_context, conversation_history)
    
    elif intent == "report":
        _run_agent_with_trace("Reporting Agent", run_report, query, formatted_context, conversation_history)
    
    elif intent == "alert":
        alert_response = _run_agent_with_trace("Alerting Agent", analyze_alerts, query, formatted_context, conversation_history)
        rec_context = formatted_context + f"\n\n[PREVIOUS AGENT OUTPUT - ALERT ANALYSIS]:\n{alert_response}"
        _run_agent_with_trace("Recommendation Agent", run_recommendation, "How do I fix the alerts?", rec_context, conversation_history)
        
    elif intent == "action":
        from agents.action_agent import run_action
        _run_agent_with_trace("Action Agent", run_action, query, formatted_context, conversation_history)
    
    elif intent == "cost":
        cost_response = _run_agent_with_trace("Cost Impact Agent", run_cost_analysis, query, formatted_context, conversation_history)
        rec_context = formatted_context + f"\n\n[PREVIOUS AGENT OUTPUT - COST ANALYSIS]:\n{cost_response}"
        _run_agent_with_trace("Recommendation Agent", run_recommendation, "What maintenance actions should we take based on this cost analysis?", rec_context, conversation_history)
    
    else:  # general
        t0 = time.time()
        general_response = _handle_general_query(query, formatted_context, context_data)
        execution_trace.append({
            "step": step_num,
            "agent": "General Assistant",
            "action": "Generated response",
            "result": "Response ready",
            "time_ms": round((time.time() - t0) * 1000),
            "status": "done"
        })
        agents_used.append("General Assistant")
        response_parts.append(general_response)
    
    # 6. Combine response
    full_response = "\n\n---\n\n".join(response_parts)
    total_time = round((time.time() - pipeline_start) * 1000)
    
    # 6b. Auto-log AI diagnostic interactions to the digital logbook
    if intent in ("diagnostic", "risk", "action") and equipment_id:
        try:
            from data.database import insert_maintenance_log
            # Brief summary from the first meaningful line of the response
            summary = ""
            for line in full_response.split("\n"):
                clean = line.strip().strip("#").strip("*").strip()
                if clean and len(clean) > 15 and not clean.startswith("---"):
                    summary = clean[:140]
                    break
            insert_maintenance_log(
                equipment_id=equipment_id,
                log_type="AI Diagnostic",
                description=f"AI {intent} analysis for query: '{query[:80]}'. {summary}",
                outcome="Advisory issued — review recommended actions",
                performed_by="AI Maintenance Wizard",
                duration_hours=round(total_time / 3600000, 4),
                parts_replaced="None",
            )
        except Exception as e:
            print(f"[WARN] Auto-logbook entry failed (non-fatal): {e}")
    
    # 7. Update conversation history
    conversation_history.append({
        "role": "user",
        "content": query,
        "timestamp": datetime.now().isoformat()
    })
    conversation_history.append({
        "role": "assistant",
        "content": full_response,
        "intent": intent,
        "agents": agents_used,
        "equipment_id": equipment_id,
        "timestamp": datetime.now().isoformat()
    })
    update_conversation_messages(conversation_id, conversation_history)
    
    return {
        "response": full_response,
        "intent": intent,
        "agents_used": agents_used,
        "equipment_id": context_data.get("detected_equipment_id"),
        "conversation_id": conversation_id,
        "sources": [
            {"source": doc["source"], "category": doc["category"], "relevance": doc["relevance"]}
            for doc in context_data.get("knowledge_context", [])[:3]
        ],
        "message_index": len(conversation_history) - 1,
        "execution_trace": execution_trace,
        "total_time_ms": total_time,
    }


def _handle_general_query(query: str, context: str, context_data: dict) -> str:
    """Handle general/informational queries."""
    query_lower = query.lower()
    
    # List equipment
    if any(w in query_lower for w in ["list", "show", "display", "all equipment", "all machine"]):
        equipment = get_all_equipment()
        response = "## 🏭 Steel Plant Equipment Overview\n\n"
        response += "| ID | Name | Type | Zone | Status | Criticality |\n"
        response += "|---|---|---|---|---|---|\n"
        for eq in equipment:
            status_emoji = {"operational": "🟢", "warning": "🟡", "critical": "🔴", "offline": "⚫"}.get(eq["status"], "⚪")
            response += f"| {eq['id']} | {eq['name']} | {eq['type']} | {eq['zone']} | {status_emoji} {eq['status']} | {eq['criticality']} |\n"
        return response
    
    # Greeting
    if any(w in query_lower for w in ["hello", "hi", "hey", "good morning", "good afternoon"]):
        return """## 👋 Welcome to the Intelligent Maintenance Wizard!

I'm your AI-powered maintenance decision support system for Tata Steel's plant. I can help you with:

- **🔍 Diagnostics**: Fault diagnosis, root cause analysis, RUL prediction
- **🚦 Risk Assessment**: Risk classification, urgency, and priority analysis
- **🔧 Recommendations**: Step-by-step maintenance plans and spare parts
- **📊 Reports**: Structured maintenance reports and summaries
- **🚨 Alerts**: Real-time anomaly detection and alert analysis
- **💰 Cost Impact**: Downtime cost analysis, ROI calculations, business impact scoring
- **📚 Knowledge**: Search equipment manuals, SOPs, and maintenance records

**Try asking me:**
- "What's wrong with the blast furnace?"
- "What's the risk level for the continuous caster?"
- "How do I replace the bearing on the rolling mill?"
- "Generate a maintenance status report"
- "Show me all active alerts"
- "What is the cost impact of the caster failure?"
- "Calculate the ROI of preventive maintenance for the blast furnace"
"""
    
    # Help
    if any(w in query_lower for w in ["help", "what can you", "how do you"]):
        return """## 🤖 How I Can Help

I'm a multi-agent AI system with specialized agents for different maintenance tasks at Tata Steel:

### Available Agents:
1. **Diagnostic Agent** — Analyzes symptoms, identifies faults, performs root cause analysis
2. **Risk Agent** — Classifies risk levels, assesses urgency, prioritizes actions
3. **Recommendation Agent** — Generates step-by-step maintenance plans
4. **Reporting Agent** — Creates structured maintenance reports
5. **Alerting Agent** — Analyzes active alerts and anomalies
6. **Cost Impact Agent** — Quantifies downtime costs, ROI analysis, business impact (₹)
7. **Feedback Agent** — Learns from your corrections to improve over time

### Tips:
- Be specific about which equipment you're asking about
- Include any symptoms or sensor readings you've observed
- Ask about cost impact to get Tata Steel-specific financial analysis
- I can maintain context across multiple messages in a conversation
- Use the 👍/👎 buttons to help me improve my responses
"""
    
    # Default: try to provide relevant context
    if context_data.get("knowledge_context"):
        return f"""## 📋 Information Retrieved

Based on your query, here's what I found in the knowledge base:

{context[:800]}

*For more specific analysis, try asking a diagnostic, risk, or recommendation question.*
"""
    
    return "I understand your query. Could you provide more details about what you'd like to know? I can help with diagnostics, risk assessment, maintenance recommendations, reports, and alert analysis."
