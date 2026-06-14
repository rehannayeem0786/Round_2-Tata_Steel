"""
Risk Assessment Agent — Classifies risk levels, assesses urgency,
and prioritizes maintenance actions based on multiple factors.
"""

from langchain.prompts import ChatPromptTemplate
from agents.llm_provider import get_llm, invoke_with_retry


RISK_SYSTEM_PROMPT = """You are an expert risk assessment agent for industrial steel plant maintenance. Your role is to:

1. **Risk Classification**: Assign risk levels (Low / Medium / High / Critical) based on current equipment condition
2. **Urgency Assessment**: Determine intervention urgency (Immediate / Urgent / Scheduled / Monitor)
3. **Bottleneck Prioritization**: Assess plant-level impact if this equipment fails
4. **Multi-Factor Priority Scoring**: Score based on:
   - Process criticality (how essential is this equipment to production?)
   - Delay severity (what is the production impact of downtime?)
   - Spares availability (are replacement parts available?)
   - Procurement lead time (how long to get parts if not in stock?)

IMPORTANT RULES:
- Use quantitative data (sensor readings, thresholds) to justify risk levels
- Consider cascading failure risks (what else breaks if this fails?)
- Factor in production schedule impact
- Provide clear, actionable priority rankings
- Reference specific threshold values and how current readings compare

OUTPUT FORMAT:
Structure your response with clear sections:
## 🚦 Risk Classification
## ⏰ Urgency Assessment
## 🏭 Plant Impact Analysis
## 📋 Priority Score Breakdown
## 🎯 Recommended Action Timeline
"""


def run_risk_assessment(query: str, context: str, conversation_history: list = None) -> str:
    """
    Run risk assessment on equipment or maintenance scenario.
    
    Args:
        query: User's risk-related question
        context: Formatted context from RAG engine
        conversation_history: Previous messages for multi-turn context
        
    Returns:
        Risk assessment text
    """
    llm = get_llm(temperature=0.2)
    if not llm:
        return _fallback_risk(query, context)
    
    messages = [("system", RISK_SYSTEM_PROMPT)]
    
    if conversation_history:
        for msg in conversation_history[-6:]:
            role = "human" if msg["role"] == "user" else "ai"
            messages.append((role, msg["content"]))
    
    user_message = f"""**QUERY**: {query}

**RETRIEVED CONTEXT**:
{context}

Provide a comprehensive risk assessment. Be specific about risk levels, urgency, and plant-wide impact. Use the sensor data and maintenance history to justify your assessment."""
    
    messages.append(("human", user_message))
    
    prompt = ChatPromptTemplate.from_messages(messages)
    chain = prompt | llm
    
    try:
        return invoke_with_retry(chain)
    except Exception as e:
        print(f"[ERR] Risk agent error: {e}")
        return _fallback_risk(query, context)


def _fallback_risk(query: str, context: str) -> str:
    """Fallback risk assessment when LLM is unavailable."""
    return f"""## 🚦 Risk Classification
**Status**: AI reasoning unavailable — showing context-based preliminary assessment.

**Query**: {query}

## 📋 Available Data Summary
{context[:500]}...

## ⚠️ Recommendation
- Configure OPENROUTER_API_KEY for full AI-powered risk assessment
- Manually review sensor trends against threshold values
- Consult equipment criticality matrix
- Check spare parts inventory status

## 📊 Confidence: **Low** (AI reasoning unavailable)
"""
