"""
Cost Impact Agent — Quantifies business impact of equipment failures,
calculates downtime costs, production losses, and ROI of maintenance actions.
Critical for demonstrating Tata Steel business value.
"""

from langchain.prompts import ChatPromptTemplate
from agents.llm_provider import get_llm, invoke_with_retry
from data.database import get_equipment_by_id, get_alerts, get_maintenance_logs


COST_SYSTEM_PROMPT = """You are an expert cost impact analysis agent for Tata Steel's industrial maintenance operations. Your role is to:

1. **Downtime Cost Calculation**: Quantify production losses from equipment failures using:
   - Production rate (tonnes/hr) × Downtime hours × Steel price/tonne
   - Labour costs for emergency repairs vs planned maintenance
   - Energy losses from inefficient operations

2. **ROI Analysis**: Calculate return on investment for maintenance actions:
   - Cost of preventive maintenance vs cost of unplanned failure
   - Savings from early detection vs cost of monitoring systems
   - Extended equipment life value vs replacement cost

3. **Business Impact Scoring**: Rank equipment by financial criticality:
   - Revenue impact per hour of downtime
   - Cascading production losses across the plant
   - Safety and compliance cost implications

4. **Tata Steel Context**: Use realistic Tata Steel Jamshedpur plant metrics:
   - Average steel price: ₹52,000/tonne (HRC)
   - Blast furnace production: ~5,000 tonnes/day
   - Caster output: ~250 tonnes/hr per strand
   - Average downtime cost: ₹15-25 lakh/hr for critical equipment
   - Maintenance labour cost: ₹3,500/hr per technician
   - Emergency repair premium: 2.5x planned maintenance cost

IMPORTANT RULES:
- Always provide quantitative financial figures in Indian Rupees (₹)
- Compare preventive vs reactive maintenance costs
- Include cascading/ripple effects on downstream operations
- Factor in safety and environmental compliance costs
- Provide clear ROI percentages and payback periods
- Use Tata Steel-specific production data where available

OUTPUT FORMAT:
Structure your response with clear sections:
## 💰 Downtime Cost Analysis
## 📊 ROI Comparison (Preventive vs Reactive)
## 🏭 Cascading Production Impact
## 📈 Business Impact Score
## 🎯 Investment Recommendation
"""


def run_cost_analysis(query: str, context: str, conversation_history: list = None) -> str:
    """
    Run cost impact analysis on equipment or maintenance scenario.

    Args:
        query: User's cost-related question
        context: Formatted context from RAG engine
        conversation_history: Previous messages for multi-turn context

    Returns:
        Cost impact analysis text
    """
    llm = get_llm(temperature=0.2)
    if not llm:
        return _fallback_cost(query, context)

    messages = [("system", COST_SYSTEM_PROMPT)]

    if conversation_history:
        for msg in conversation_history[-6:]:
            role = "human" if msg["role"] == "user" else "ai"
            messages.append((role, msg["content"]))

    user_message = f"""**QUERY**: {query}

**RETRIEVED CONTEXT**:
{context}

Provide a comprehensive cost impact analysis with specific financial figures in Indian Rupees (₹). Include downtime costs, ROI comparisons, and business impact scoring. Be quantitative and reference Tata Steel production data."""

    messages.append(("human", user_message))

    prompt = ChatPromptTemplate.from_messages(messages)
    chain = prompt | llm

    try:
        return invoke_with_retry(chain)
    except Exception as e:
        print(f"[ERR] Cost agent error: {e}")
        return _fallback_cost(query, context)


def _fallback_cost(query: str, context: str) -> str:
    """Fallback cost analysis when LLM is unavailable."""
    return f"""## 💰 Cost Impact Analysis
**Status**: AI reasoning unavailable — showing preliminary cost estimates.

**Query**: {query}

## 📋 Estimated Tata Steel Cost Benchmarks
- Critical equipment downtime: ₹15-25 lakh/hr
- Blast Furnace shutdown: ₹2.5 crore/day (5,000 tonnes × ₹52,000/tonne)
- Caster strand failure: ₹13 lakh/hr (250 tonnes/hr × ₹52,000/tonne)
- Emergency repair premium: 2.5x planned maintenance cost
- Preventive maintenance ROI: Typically 3:1 to 10:1

## ⚠️ Recommendation
Configure API key for detailed AI-powered cost analysis with specific equipment figures.

## 📊 Confidence: **Low** (AI reasoning unavailable)
"""


def get_equipment_cost_profile(equipment_id: str) -> dict:
    """
    Get cost profile for an equipment based on its type and criticality.
    Returns estimated production rate, downtime cost, and maintenance cost ratios.
    """
    equipment = get_equipment_by_id(equipment_id)
    if not equipment:
        return {}

    # Tata Steel production cost benchmarks by equipment type
    COST_PROFILES = {
        "Blast Furnace": {
            "production_rate_tonnes_hr": 208,  # 5000/24
            "steel_price_per_tonne": 52000,
            "downtime_cost_per_hr": 10816000,  # ~1.08 crore/hr
            "planned_maintenance_cost_per_hr": 35000,
            "emergency_maintenance_multiplier": 2.5,
            "typical_preventive_roi": "8:1",
        },
        "Basic Oxygen Furnace": {
            "production_rate_tonnes_hr": 150,
            "steel_price_per_tonne": 52000,
            "downtime_cost_per_hr": 7800000,
            "planned_maintenance_cost_per_hr": 28000,
            "emergency_maintenance_multiplier": 2.5,
            "typical_preventive_roi": "6:1",
        },
        "Continuous Casting Machine": {
            "production_rate_tonnes_hr": 250,
            "steel_price_per_tonne": 52000,
            "downtime_cost_per_hr": 13000000,
            "planned_maintenance_cost_per_hr": 32000,
            "emergency_maintenance_multiplier": 2.8,
            "typical_preventive_roi": "10:1",
        },
        "Rolling Mill": {
            "production_rate_tonnes_hr": 180,
            "steel_price_per_tonne": 52000,
            "downtime_cost_per_hr": 9360000,
            "planned_maintenance_cost_per_hr": 25000,
            "emergency_maintenance_multiplier": 2.2,
            "typical_preventive_roi": "5:1",
        },
        "Ladle Furnace": {
            "production_rate_tonnes_hr": 120,
            "steel_price_per_tonne": 52000,
            "downtime_cost_per_hr": 6240000,
            "planned_maintenance_cost_per_hr": 22000,
            "emergency_maintenance_multiplier": 2.3,
            "typical_preventive_roi": "4:1",
        },
        "Cooling System": {
            "production_rate_tonnes_hr": 0,  # Indirect impact
            "steel_price_per_tonne": 52000,
            "downtime_cost_per_hr": 500000,  # Indirect cascading
            "planned_maintenance_cost_per_hr": 15000,
            "emergency_maintenance_multiplier": 2.0,
            "typical_preventive_roi": "3:1",
        },
        "Hydraulic Press": {
            "production_rate_tonnes_hr": 40,
            "steel_price_per_tonne": 52000,
            "downtime_cost_per_hr": 2080000,
            "planned_maintenance_cost_per_hr": 18000,
            "emergency_maintenance_multiplier": 2.0,
            "typical_preventive_roi": "4:1",
        },
        "Crane System": {
            "production_rate_tonnes_hr": 0,  # Indirect - blocks other equipment
            "steel_price_per_tonne": 52000,
            "downtime_cost_per_hr": 3000000,  # Blocks melt shop
            "planned_maintenance_cost_per_hr": 20000,
            "emergency_maintenance_multiplier": 2.5,
            "typical_preventive_roi": "5:1",
        },
        "Gas Recovery": {
            "production_rate_tonnes_hr": 0,  # Energy savings
            "steel_price_per_tonne": 52000,
            "downtime_cost_per_hr": 800000,  # Energy loss + environmental
            "planned_maintenance_cost_per_hr": 12000,
            "emergency_maintenance_multiplier": 1.8,
            "typical_preventive_roi": "3:1",
        },
    }

    profile = COST_PROFILES.get(equipment["type"], {
        "production_rate_tonnes_hr": 100,
        "steel_price_per_tonne": 52000,
        "downtime_cost_per_hr": 5200000,
        "planned_maintenance_cost_per_hr": 25000,
        "emergency_maintenance_multiplier": 2.0,
        "typical_preventive_roi": "4:1",
    })

    # Add equipment-specific data
    profile["equipment_id"] = equipment_id
    profile["equipment_name"] = equipment["name"]
    profile["equipment_type"] = equipment["type"]
    profile["criticality"] = equipment["criticality"]
    profile["status"] = equipment["status"]

    # Get recent maintenance cost data
    recent_logs = get_maintenance_logs(equipment_id, limit=5)
    total_maintenance_hours = sum(log.get("duration_hours", 0) or 0 for log in recent_logs)
    profile["recent_maintenance_hours"] = total_maintenance_hours
    profile["estimated_annual_maintenance_cost"] = int(total_maintenance_hours * profile["planned_maintenance_cost_per_hr"] * 12)

    # Calculate annual downtime risk
    if equipment["status"] in ("warning", "critical"):
        profile["annual_downtime_risk"] = int(profile["downtime_cost_per_hr"] * 48)  # Assume 48hrs risk
    else:
        profile["annual_downtime_risk"] = int(profile["downtime_cost_per_hr"] * 8)  # Assume 8hrs minor

    return profile