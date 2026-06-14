"""
Diagnostic Agent — Performs fault diagnosis, root cause analysis,
and remaining useful life (RUL) prediction using LLM reasoning
augmented with retrieved knowledge context.
"""

from langchain.prompts import ChatPromptTemplate
from agents.llm_provider import get_llm, invoke_with_retry


DIAGNOSTIC_SYSTEM_PROMPT = """You are an expert industrial maintenance diagnostic agent specializing in steel manufacturing equipment. Your role is to:

1. **Fault Diagnosis**: Identify the most probable fault or failure based on symptoms, sensor data, and historical context.
2. **Root Cause Analysis (RCA)**: Determine the root cause using a systematic approach (5-Why, Fishbone methodology).
3. **Remaining Useful Life (RUL)**: Report the calculated Estimated RUL provided in the sensor context, and explain what factors are driving that estimate based on degradation trends.
4. **Early Warning**: Highlight if the statistical EarlyWarning flag is YES, and explain what anomaly signature triggered it.

IMPORTANT RULES:
- Base your analysis on the provided context (sensor data, maintenance history, knowledge base documents)
- Be specific — reference actual values, thresholds, and historical incidents
- Provide confidence levels for your diagnoses (High/Medium/Low)
- Always explain your reasoning chain (make it traceable)
- If data is insufficient, say so and recommend what additional data is needed
- Use technical terminology appropriate for maintenance engineers

OUTPUT FORMAT:
Structure your response with clear sections:
## 🔍 Fault Diagnosis
## 🔗 Root Cause Analysis  
## ⏱️ Remaining Useful Life Estimate
## ⚠️ Early Warnings
## 📊 Confidence Assessment
"""


def run_diagnosis(query: str, context: str, conversation_history: list = None, image_data: str = None) -> str:
    """
    Run diagnostic analysis on a maintenance query.
    
    Args:
        query: User's diagnostic question
        context: Formatted context from RAG engine
        conversation_history: Previous messages for multi-turn context
        image_data: Base64 image string for vision
        
    Returns:
        Diagnostic analysis text
    """
    # Build the user message text with context
    text_content = f"""**QUERY**: {query}

**RETRIEVED CONTEXT**:
{context}

Please provide a thorough diagnostic analysis based on the above context and query. Be specific, reference actual data values, and provide actionable insights."""

    if image_data:
        from config import API_PROVIDER
        model_override = None
        if API_PROVIDER == "nvidia":
            model_override = "meta/llama-3.2-90b-vision-instruct"
        elif API_PROVIDER == "openrouter":
            model_override = "meta-llama/llama-3.2-90b-vision-instruct"
            
        llm_vision = get_llm(model=model_override)
        if llm_vision:
            messages = [("system", DIAGNOSTIC_SYSTEM_PROMPT)]
            
            # Add conversation history for multi-turn context
            if conversation_history:
                for msg in conversation_history[-6:]:  # Last 3 turns
                    role = "human" if msg["role"] == "user" else "ai"
                    messages.append((role, msg["content"]))
            
            # LangChain vision message format
            messages.append(("human", [
                {"type": "text", "text": text_content},
                {"type": "image_url", "image_url": {"url": image_data}}
            ]))
            
            try:
                prompt = ChatPromptTemplate.from_messages(messages)
                chain = prompt | llm_vision
                return invoke_with_retry(chain)
            except Exception as vision_err:
                print(f"[WARN] Vision diagnosis failed, falling back to text-only: {vision_err}")
                # Fall through to text-only diagnostics
                
    # Text-only diagnostics
    llm = get_llm()
    if not llm:
        return _fallback_diagnosis(query, context)
        
    messages = [("system", DIAGNOSTIC_SYSTEM_PROMPT)]
    
    # Add conversation history for multi-turn context
    if conversation_history:
        for msg in conversation_history[-6:]:  # Last 3 turns
            role = "human" if msg["role"] == "user" else "ai"
            messages.append((role, msg["content"]))
            
    messages.append(("human", text_content))
    
    prompt = ChatPromptTemplate.from_messages(messages)
    chain = prompt | llm
    
    try:
        return invoke_with_retry(chain)
    except Exception as e:
        print(f"[ERR] Diagnostic agent error: {e}")
        return _fallback_diagnosis(query, context)


def _fallback_diagnosis(query: str, context: str) -> str:
    """Fallback diagnosis when LLM is unavailable."""
    return f"""## 🔍 Fault Diagnosis
Based on the available data and context, here is a preliminary analysis:

**Query**: {query}

**Analysis**: The system has retrieved relevant context from the knowledge base and sensor data. However, the AI reasoning engine is currently unavailable (API key not configured).

**Available Context Summary**:
{context[:500]}...

## ⚠️ Recommendation
- Configure the OPENROUTER_API_KEY environment variable for full AI-powered diagnostics
- Review the sensor data trends manually
- Consult the relevant equipment manual sections identified above
- Check maintenance history for similar past incidents

## 📊 Confidence Assessment
Confidence: **Low** (AI reasoning unavailable, showing retrieved context only)
"""
