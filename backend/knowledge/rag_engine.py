"""
RAG Engine — Retrieval-Augmented Generation engine that combines
vector search results with structured database context for
comprehensive maintenance knowledge retrieval.
"""

from knowledge.vector_store import search, search_all_collections, get_collection_stats
from data.database import (
    get_equipment_by_id, get_all_equipment,
    get_latest_sensor_readings, get_maintenance_logs,
    get_anomaly_readings, get_alerts
)
from config import RAG_TOP_K, RAG_SCORE_THRESHOLD


def retrieve_context(query: str, equipment_id: str = None, n_results: int = None) -> dict:
    """
    Retrieve comprehensive context for a query by combining:
    1. Semantic search across knowledge collections
    2. Relevant equipment data from the database
    3. Recent sensor readings and alerts
    
    Args:
        query: User's natural language query
        equipment_id: Optional equipment ID for focused retrieval
        n_results: Number of knowledge results to retrieve
        
    Returns:
        dict with 'knowledge_context', 'equipment_context', 'sensor_context', 'alert_context'
    """
    if n_results is None:
        n_results = RAG_TOP_K
    
    # 1. Semantic search across knowledge base
    knowledge_results = search_all_collections(query, n_results=n_results)
    
    # Filter by relevance threshold
    knowledge_context = []
    for result in knowledge_results:
        if result["distance"] <= (1 - RAG_SCORE_THRESHOLD):  # cosine distance
            knowledge_context.append({
                "text": result["document"],
                "source": result["metadata"].get("source_file", "unknown"),
                "category": result["metadata"].get("category", "unknown"),
                "collection": result.get("collection", "unknown"),
                "relevance": round(1 - result["distance"], 3),
            })
    
    # 2. Equipment context from database
    equipment_context = None
    if equipment_id:
        equipment_context = get_equipment_by_id(equipment_id)
    else:
        # Try to identify equipment from query
        equipment_list = get_all_equipment()
        for eq in equipment_list:
            name_lower = eq["name"].lower()
            query_lower = query.lower()
            if any(word in query_lower for word in name_lower.split()):
                equipment_id = eq["id"]
                equipment_context = eq
                break
    
    # 3. Sensor context
    sensor_context = []
    if equipment_id:
        readings = get_latest_sensor_readings(equipment_id, limit=20)
        sensor_context = readings
    
    # 4. Alert context
    alert_context = []
    if equipment_id:
        alerts = get_alerts(acknowledged=False)
        alert_context = [a for a in alerts if a["equipment_id"] == equipment_id]
    else:
        alert_context = get_alerts(acknowledged=False, limit=10)
    
    # 5. Maintenance history
    maintenance_context = []
    if equipment_id:
        maintenance_context = get_maintenance_logs(equipment_id, limit=10)
    
    return {
        "knowledge_context": knowledge_context,
        "equipment_context": equipment_context,
        "sensor_context": sensor_context,
        "alert_context": alert_context,
        "maintenance_context": maintenance_context,
        "detected_equipment_id": equipment_id,
    }


def format_context_for_llm(context: dict) -> str:
    """
    Format the retrieved context into a structured text block
    suitable for inclusion in an LLM prompt.
    """
    sections = []
    
    # Knowledge base context
    if context["knowledge_context"]:
        sections.append("═══ RELEVANT KNOWLEDGE BASE DOCUMENTS ═══")
        for i, doc in enumerate(context["knowledge_context"], 1):
            sections.append(f"\n--- Document {i} (Source: {doc['source']}, Category: {doc['category']}, Relevance: {doc['relevance']}) ---")
            sections.append(doc["text"])
    
    # Equipment context
    if context["equipment_context"]:
        eq = context["equipment_context"]
        sections.append("\n═══ EQUIPMENT INFORMATION ═══")
        sections.append(f"ID: {eq['id']}")
        sections.append(f"Name: {eq['name']}")
        sections.append(f"Type: {eq['type']}")
        sections.append(f"Zone: {eq['zone']}")
        sections.append(f"Status: {eq['status']}")
        sections.append(f"Criticality: {eq['criticality']}")
        sections.append(f"Last Maintenance: {eq.get('last_maintenance', 'N/A')}")
        sections.append(f"Description: {eq.get('description', 'N/A')}")
        if eq.get('specifications'):
            sections.append(f"Specifications: {eq['specifications']}")
    
    # Sensor context
    if context["sensor_context"]:
        sections.append("\n═══ RECENT SENSOR READINGS ═══")
        # Group by metric
        metrics = {}
        for reading in context["sensor_context"]:
            metric = reading["metric"]
            if metric not in metrics:
                metrics[metric] = []
            metrics[metric].append(reading)
        
        for metric, readings in metrics.items():
            latest = readings[0]
            values = [r["value"] for r in readings[:10]]
            avg_val = sum(values) / len(values)
            
            ew_status = "YES" if latest.get('early_warning', 0) else "NO"
            rul = latest.get('rul_hours', 999.0)
            rul_str = f"{rul} hrs" if rul < 900 else "Stable"
            
            sections.append(f"\n{metric}: Latest={latest['value']} {latest['unit']}, Avg(last 10)={round(avg_val, 2)} {latest['unit']}, Anomaly={bool(latest['is_anomaly'])}, EarlyWarning={ew_status}, Estimated RUL={rul_str}")
    
    # Alert context
    if context["alert_context"]:
        sections.append("\n═══ ACTIVE ALERTS ═══")
        for alert in context["alert_context"]:
            sections.append(f"\n[{alert['severity'].upper()}] {alert['title']}")
            sections.append(f"  {alert['message']}")
            sections.append(f"  Time: {alert['timestamp']}")
    
    # Maintenance history
    if context["maintenance_context"]:
        sections.append("\n═══ RECENT MAINTENANCE HISTORY ═══")
        for log in context["maintenance_context"][:5]:
            sections.append(f"\nDate: {log['date']} | Type: {log['type']}")
            sections.append(f"  Description: {log['description']}")
            if log.get('outcome'):
                sections.append(f"  Outcome: {log['outcome']}")
            if log.get('parts_replaced'):
                sections.append(f"  Parts: {log['parts_replaced']}")
    
    result = "\n".join(sections)
    # Escape curly braces to prevent LangChain from treating them as template variables
    result = result.replace("{", "{{").replace("}", "}}")
    return result


def get_knowledge_stats() -> dict:
    """Get statistics about the knowledge base."""
    return get_collection_stats()
