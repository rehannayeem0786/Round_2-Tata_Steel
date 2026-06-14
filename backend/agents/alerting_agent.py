"""
Alerting Agent — Analyzes sensor data for anomalies, generates
context-aware alerts, and determines alert severity and recommended actions.
"""

from langchain.prompts import ChatPromptTemplate
from agents.llm_provider import get_llm, invoke_with_retry
from data.database import get_anomaly_readings, get_alerts


ALERTING_SYSTEM_PROMPT = """You are an expert alerting and anomaly detection agent for a steel manufacturing plant. Your role is to:

1. **Analyze Anomalies**: Evaluate sensor anomalies and determine if they represent genuine equipment issues
2. **Contextualize Alerts**: Provide context for why an alert was triggered and what it means
3. **Severity Assessment**: Determine the appropriate severity level based on potential consequences
4. **Recommended Response**: Suggest immediate actions for each alert

Keep responses concise and action-oriented. Maintenance engineers need quick, clear guidance.

OUTPUT FORMAT:
For each alert or anomaly:
## 🚨 Alert Analysis
- **Severity**: Critical/High/Medium/Low
- **Equipment**: Name and ID
- **Issue**: Brief description
- **Impact**: What could happen if not addressed
- **Recommended Action**: Specific next steps
- **Timeline**: How urgently this needs attention
"""


def analyze_alerts(query: str, context: str, conversation_history: list = None) -> str:
    """
    Analyze alerts and anomalies.
    
    Args:
        query: User's alert-related question
        context: Formatted context from RAG engine
        conversation_history: Previous messages
        
    Returns:
        Alert analysis text
    """
    llm = get_llm(temperature=0.2)
    
    # Gather current anomaly and alert data
    anomalies = get_anomaly_readings(limit=20)
    active_alerts = get_alerts(acknowledged=False)
    
    alert_data = "\nCURRENT ACTIVE ALERTS:\n"
    for alert in active_alerts:
        alert_data += f"- [{alert['severity']}] {alert.get('equipment_name', alert['equipment_id'])}: {alert['title']} -- {alert['message']}\n"
    
    alert_data += f"\nRECENT ANOMALY READINGS ({len(anomalies)}):\n"
    for anomaly in anomalies[:10]:
        alert_data += f"- {anomaly.get('equipment_name', anomaly['equipment_id'])}: {anomaly['metric']}={anomaly['value']} {anomaly['unit']} at {anomaly['timestamp']}\n"
    
    if not llm:
        return f"""## 🚨 Alert Summary
{alert_data}

**Note**: Configure OPENROUTER_API_KEY for AI-powered alert analysis.
"""
    
    messages = [("system", ALERTING_SYSTEM_PROMPT)]
    
    if conversation_history:
        for msg in conversation_history[-4:]:
            role = "human" if msg["role"] == "user" else "ai"
            messages.append((role, msg["content"]))
    
    user_message = f"""**QUERY**: {query}

**CURRENT ALERT AND ANOMALY DATA**:
{alert_data}

**ADDITIONAL CONTEXT**:
{context}

Analyze the current alerts and anomalies. Provide severity assessment, potential impact, and recommended actions for each significant finding."""
    
    messages.append(("human", user_message))
    
    prompt = ChatPromptTemplate.from_messages(messages)
    chain = prompt | llm
    
    try:
        return invoke_with_retry(chain)
    except Exception as e:
        print(f"[ERR] Alerting agent error: {e}")
        return f"## 🚨 Alert Data\n{alert_data}\n\n⚠️ AI analysis unavailable: {str(e)}"
