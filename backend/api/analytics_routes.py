"""
Analytics API routes — OEE metrics, cost impact analysis,
sensor trend data, predictive maintenance timeline, and
plant-wide business intelligence for Tata Steel.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from data.database import (
    get_all_equipment, get_equipment_by_id,
    get_latest_sensor_readings, get_sensor_readings_by_metric,
    get_maintenance_logs, get_alerts, get_dashboard_stats,
    get_sensor_trend_data, get_oee_metrics, get_cost_summary,
    get_predictive_timeline
)
from agents.cost_agent import get_equipment_cost_profile, run_cost_analysis

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/oee")
async def oee_metrics():
    """Get Overall Equipment Effectiveness metrics for all equipment."""
    equipment = get_all_equipment()
    oee_data = []

    for eq in equipment:
        metrics = get_oee_metrics(eq["id"])
        cost_profile = get_equipment_cost_profile(eq["id"])
        oee_data.append({
            "equipment_id": eq["id"],
            "equipment_name": eq["name"],
            "equipment_type": eq["type"],
            "status": eq["status"],
            "criticality": eq["criticality"],
            "oee": metrics,
            "cost_profile": cost_profile,
        })

    # Plant-wide OEE summary
    plant_oee = get_oee_metrics(None)

    return {
        "success": True,
        "data": {
            "plant_oee": plant_oee,
            "equipment_oee": oee_data,
        }
    }


@router.get("/oee/{equipment_id}")
async def equipment_oee(equipment_id: str):
    """Get OEE metrics for a specific equipment."""
    equipment = get_equipment_by_id(equipment_id)
    if not equipment:
        raise HTTPException(status_code=404, detail="Equipment not found")

    metrics = get_oee_metrics(equipment_id)
    cost_profile = get_equipment_cost_profile(equipment_id)

    return {
        "success": True,
        "data": {
            "equipment": equipment,
            "oee": metrics,
            "cost_profile": cost_profile,
        }
    }


@router.get("/cost-summary")
async def cost_summary():
    """Get plant-wide cost impact summary for Tata Steel dashboard."""
    summary = get_cost_summary()
    return {"success": True, "data": summary}


@router.get("/cost/{equipment_id}")
async def equipment_cost(equipment_id: str):
    """Get detailed cost profile for a specific equipment."""
    equipment = get_equipment_by_id(equipment_id)
    if not equipment:
        raise HTTPException(status_code=404, detail="Equipment not found")

    cost_profile = get_equipment_cost_profile(equipment_id)
    alerts = get_alerts(acknowledged=False)
    equipment_alerts = [a for a in alerts if a["equipment_id"] == equipment_id]

    return {
        "success": True,
        "data": {
            "equipment": equipment,
            "cost_profile": cost_profile,
            "active_alerts": equipment_alerts,
        }
    }


@router.get("/sensor-trends/{equipment_id}")
async def sensor_trends(
    equipment_id: str,
    metric: Optional[str] = None,
    hours: int = Query(default=24, le=168)
):
    """Get sensor trend data for charting, with threshold lines."""
    equipment = get_equipment_by_id(equipment_id)
    if not equipment:
        raise HTTPException(status_code=404, detail="Equipment not found")

    trend_data = get_sensor_trend_data(equipment_id, metric, hours)

    return {
        "success": True,
        "data": {
            "equipment_id": equipment_id,
            "equipment_name": equipment["name"],
            "trends": trend_data,
        }
    }


@router.get("/predictive-timeline")
async def predictive_timeline():
    """Get predictive maintenance timeline for all equipment."""
    timeline = get_predictive_timeline()
    return {"success": True, "data": timeline}


@router.get("/predictive-timeline/{equipment_id}")
async def equipment_predictive_timeline(equipment_id: str):
    """Get predictive maintenance timeline for a specific equipment."""
    equipment = get_equipment_by_id(equipment_id)
    if not equipment:
        raise HTTPException(status_code=404, detail="Equipment not found")

    timeline = get_predictive_timeline(equipment_id)
    return {"success": True, "data": timeline}


@router.post("/cost-analysis")
async def cost_analysis_query(query: str, equipment_id: Optional[str] = None):
    """Run AI-powered cost impact analysis on a query."""
    from knowledge.rag_engine import retrieve_context, format_context_for_llm

    context_data = retrieve_context(query, equipment_id)
    formatted_context = format_context_for_llm(context_data)

    # Add cost profile context if equipment detected
    if equipment_id:
        cost_profile = get_equipment_cost_profile(equipment_id)
        if cost_profile:
            formatted_context += f"\n\n═══ COST PROFILE DATA ═══\n"
            formatted_context += f"Equipment: {cost_profile['equipment_name']}\n"
            formatted_context += f"Downtime Cost/hr: ₹{cost_profile['downtime_cost_per_hr']:,}\n"
            formatted_context += f"Production Rate: {cost_profile['production_rate_tonnes_hr']} tonnes/hr\n"
            formatted_context += f"Steel Price: ₹{cost_profile['steel_price_per_tonne']:,}/tonne\n"
            formatted_context += f"Preventive ROI: {cost_profile['typical_preventive_roi']}\n"

    import asyncio
    result = await asyncio.to_thread(run_cost_analysis, query, formatted_context)

    return {
        "success": True,
        "data": {
            "analysis": result,
            "equipment_id": equipment_id,
        }
    }


@router.get("/anomaly-detection")
async def anomaly_detection_all():
    """ML-based anomaly detection across all equipment (IsolationForest + robust statistics)."""
    import asyncio
    from ml.anomaly_detector import detect_equipment_anomalies

    equipment = get_all_equipment()

    def _scan():
        results = []
        for eq in equipment:
            report = detect_equipment_anomalies(eq["id"])
            report["equipment_name"] = eq["name"]
            report["equipment_type"] = eq["type"]
            report["status"] = eq["status"]
            report["criticality"] = eq["criticality"]
            results.append(report)
        results.sort(key=lambda r: r["overall_anomaly_score"], reverse=True)
        return results

    data = await asyncio.to_thread(_scan)
    return {"success": True, "data": data}


@router.get("/anomaly-detection/{equipment_id}")
async def anomaly_detection_equipment(equipment_id: str):
    """ML-based anomaly detection for a single equipment with per-metric scores."""
    import asyncio
    from ml.anomaly_detector import detect_equipment_anomalies

    equipment = get_equipment_by_id(equipment_id)
    if not equipment:
        raise HTTPException(status_code=404, detail="Equipment not found")

    report = await asyncio.to_thread(detect_equipment_anomalies, equipment_id)
    report["equipment_name"] = equipment["name"]
    report["equipment_type"] = equipment["type"]
    report["status"] = equipment["status"]
    return {"success": True, "data": report}