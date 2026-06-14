"""
Recommendation Agent — Generates step-by-step maintenance action plans,
spare parts recommendations, and optimized maintenance schedules.
"""

from langchain.prompts import ChatPromptTemplate
from agents.llm_provider import get_llm, invoke_with_retry


RECOMMENDATION_SYSTEM_PROMPT = """You are an expert maintenance recommendation agent for industrial steel plant equipment. Your role is to:

1. **Step-by-Step Maintenance Plans**: Provide detailed, actionable maintenance procedures
2. **Immediate vs Long-term Actions**: Clearly separate what needs to be done NOW vs what can be scheduled
3. **Spare Parts Identification**: List required parts with specifications
4. **Optimized Scheduling**: Recommend optimal timing considering production schedules
5. **Resource Planning**: Estimate personnel, tools, and time requirements

IMPORTANT RULES:
- Provide specific, actionable steps (not vague advice)
- Reference relevant SOPs and procedures from the knowledge base
- Include safety precautions and prerequisites
- Estimate duration and resource requirements for each action
- Consider production impact when recommending maintenance windows
- Explain the rationale behind each recommendation (make it explainable and traceable)
- If relevant historical solutions exist, reference them

OUTPUT FORMAT:
Structure your response with clear sections:
## 🔧 Immediate Actions (Do Now)
## 📅 Scheduled Maintenance Plan
## 🔩 Required Spare Parts & Materials
## ⏱️ Estimated Timeline & Resources
## 🛡️ Safety Precautions
## 📈 Long-term Monitoring Recommendations
"""


def run_recommendation(query: str, context: str, conversation_history: list = None) -> str:
    """
    Generate maintenance recommendations.
    
    Args:
        query: User's maintenance question
        context: Formatted context from RAG engine
        conversation_history: Previous messages for multi-turn context
        
    Returns:
        Maintenance recommendation text
    """
    llm = get_llm()
    if not llm:
        return _fallback_recommendation(query, context)
    
    messages = [("system", RECOMMENDATION_SYSTEM_PROMPT)]
    
    if conversation_history:
        for msg in conversation_history[-6:]:
            role = "human" if msg["role"] == "user" else "ai"
            messages.append((role, msg["content"]))
    
    user_message = f"""**QUERY**: {query}

**RETRIEVED CONTEXT**:
{context}

Provide detailed, step-by-step maintenance recommendations. Be specific about procedures, parts, timing, and safety. Reference relevant SOPs and historical maintenance records from the context."""
    
    messages.append(("human", user_message))
    
    prompt = ChatPromptTemplate.from_messages(messages)
    chain = prompt | llm
    
    try:
        return invoke_with_retry(chain)
    except Exception as e:
        print(f"[ERR] Recommendation agent error: {e}")
        return _fallback_recommendation(query, context)


def _fallback_recommendation(query: str, context: str) -> str:
    """Fallback recommendation when LLM is unavailable."""
    return f"""## 🔧 Maintenance Recommendations
**Status**: AI reasoning unavailable — showing context-based preliminary recommendations.

**Query**: {query}

## 📋 Relevant Context
{context[:500]}...

## ⚠️ General Recommendations
1. Review the relevant equipment manual for standard procedures
2. Check maintenance SOPs for the specific task
3. Verify spare parts availability in inventory
4. Plan maintenance window with production scheduling
5. Ensure LOTO and safety procedures are followed

Configure OPENROUTER_API_KEY for detailed AI-powered recommendations.
"""
