"""
Reporting Agent — Generates structured maintenance reports,
decision summaries, and abnormal alert reports.
"""

from langchain.prompts import ChatPromptTemplate
from agents.llm_provider import get_llm, invoke_with_retry
from data.database import get_all_equipment, get_alerts, get_maintenance_logs, get_dashboard_stats


REPORTING_SYSTEM_PROMPT = """You are an expert maintenance reporting agent for a steel manufacturing plant. Your role is to:

1. **Structured Reports**: Generate comprehensive maintenance reports in clear, professional format
2. **Decision Summaries**: Create concise summaries for engineers and supervisors
3. **Abnormal Alert Reports**: Summarize and contextualize active alerts
4. **Trend Analysis**: Identify patterns and trends in maintenance data

IMPORTANT RULES:
- Use professional, clear language suitable for engineering management
- Include specific data points, dates, and measurements
- Organize information hierarchically (most critical first)
- Provide actionable conclusions and recommendations
- Use tables and structured formats where appropriate
- Include both quantitative metrics and qualitative assessments

OUTPUT FORMAT:
Use professional report structure with headers, bullet points, and tables as appropriate.
Always include:
- Report date and scope
- Executive summary
- Detailed findings
- Recommendations
- Appendix data references
"""


def run_report(query: str, context: str, conversation_history: list = None) -> str:
    """
    Generate a maintenance report.
    
    Args:
        query: User's report request
        context: Formatted context from RAG engine
        conversation_history: Previous messages for context
        
    Returns:
        Formatted report text
    """
    llm = get_llm(temperature=0.2)
    
    # Gather additional plant-wide data for reports
    stats = get_dashboard_stats()
    all_equipment = get_all_equipment()
    active_alerts = get_alerts(acknowledged=False)
    recent_maintenance = get_maintenance_logs(limit=20)
    
    plant_summary = f"""
PLANT-WIDE STATUS:
- Total Equipment: {stats['total_equipment']}
- Operational: {stats['operational']} | Warning: {stats['warning']} | Critical: {stats['critical']} | Offline: {stats['offline']}
- Uptime: {stats['uptime_percentage']}%
- Active Alerts: {stats['active_alerts']} (Critical: {stats['critical_alerts']})
- Maintenance Actions (Last 7 Days): {stats['recent_maintenance']}

EQUIPMENT STATUS DETAILS:
"""
    for eq in all_equipment:
        plant_summary += f"- {eq['name']} ({eq['id']}): Status={eq['status']}, Criticality={eq['criticality']}\n"
    
    plant_summary += f"\nACTIVE ALERTS ({len(active_alerts)}):\n"
    for alert in active_alerts[:10]:
        plant_summary += f"- [{alert['severity'].upper()}] {alert.get('equipment_name', alert['equipment_id'])}: {alert['title']}\n"
    
    plant_summary += f"\nRECENT MAINTENANCE ({len(recent_maintenance)} records):\n"
    for log in recent_maintenance[:10]:
        plant_summary += f"- {log['date']}: {log.get('equipment_name', log['equipment_id'])} -- {log['type']} -- {log['description'][:100]}\n"
    
    if not llm:
        return _fallback_report(query, plant_summary, context)
    
    messages = [("system", REPORTING_SYSTEM_PROMPT)]
    
    if conversation_history:
        for msg in conversation_history[-4:]:
            role = "human" if msg["role"] == "user" else "ai"
            messages.append((role, msg["content"]))
    
    user_message = f"""**REPORT REQUEST**: {query}

**PLANT-WIDE DATA**:
{plant_summary}

**ADDITIONAL CONTEXT FROM KNOWLEDGE BASE**:
{context}

Generate a comprehensive, professionally formatted maintenance report addressing the request above. Include specific data, metrics, and actionable recommendations."""
    
    messages.append(("human", user_message))
    
    prompt = ChatPromptTemplate.from_messages(messages)
    chain = prompt | llm
    
    try:
        return invoke_with_retry(chain)
    except Exception as e:
        print(f"[ERR] Reporting agent error: {e}")
        return _fallback_report(query, plant_summary, context)


def _fallback_report(query: str, plant_summary: str, context: str) -> str:
    """Fallback report when LLM is unavailable."""
    return f"""# Maintenance Status Report

**Generated**: Auto-generated (AI reasoning unavailable)
**Request**: {query}

## Plant Overview
{plant_summary}

## Knowledge Base Context
{context[:300]}...

## ⚠️ Note
Configure OPENROUTER_API_KEY for AI-generated comprehensive reports with analysis and recommendations.
"""
