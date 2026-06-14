"""
Database module — SQLite models and operations for the Maintenance Wizard.
Uses synchronous sqlite3 with row_factory for dict-like access.
"""

import sqlite3
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from config import DB_PATH


def get_connection():
    """Get a synchronous SQLite connection."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_database():
    """Initialize the database schema."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS equipment (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            zone TEXT NOT NULL,
            status TEXT DEFAULT 'operational',
            criticality TEXT DEFAULT 'medium',
            install_date TEXT,
            last_maintenance TEXT,
            description TEXT,
            specifications TEXT
        );

        CREATE TABLE IF NOT EXISTS sensor_readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            equipment_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            metric TEXT NOT NULL,
            value REAL NOT NULL,
            unit TEXT NOT NULL,
            is_anomaly INTEGER DEFAULT 0,
            early_warning INTEGER DEFAULT 0,
            rul_hours REAL DEFAULT 999.0,
            FOREIGN KEY (equipment_id) REFERENCES equipment(id)
        );

        CREATE TABLE IF NOT EXISTS maintenance_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            equipment_id TEXT NOT NULL,
            date TEXT NOT NULL,
            type TEXT NOT NULL,
            description TEXT NOT NULL,
            outcome TEXT,
            performed_by TEXT,
            duration_hours REAL,
            parts_replaced TEXT,
            FOREIGN KEY (equipment_id) REFERENCES equipment(id)
        );

        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            equipment_id TEXT NOT NULL,
            severity TEXT NOT NULL,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            acknowledged INTEGER DEFAULT 0,
            resolved INTEGER DEFAULT 0,
            resolved_at TEXT,
            FOREIGN KEY (equipment_id) REFERENCES equipment(id)
        );

        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            title TEXT,
            messages TEXT DEFAULT '[]'
        );

        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT,
            message_index INTEGER,
            rating TEXT,
            correction TEXT,
            timestamp TEXT NOT NULL,
            applied INTEGER DEFAULT 0,
            FOREIGN KEY (conversation_id) REFERENCES conversations(id)
        );

        CREATE TABLE IF NOT EXISTS action_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            equipment_id TEXT NOT NULL,
            action_type TEXT NOT NULL, -- 'order_part', 'dispatch_technician', 'shutdown_equipment'
            details TEXT NOT NULL,
            status TEXT DEFAULT 'pending', -- 'pending', 'approved', 'executed', 'cancelled'
            timestamp TEXT NOT NULL,
            FOREIGN KEY (equipment_id) REFERENCES equipment(id)
        );

        CREATE INDEX IF NOT EXISTS idx_sensor_equipment ON sensor_readings(equipment_id);
        CREATE INDEX IF NOT EXISTS idx_sensor_timestamp ON sensor_readings(timestamp);
        CREATE INDEX IF NOT EXISTS idx_alerts_equipment ON alerts(equipment_id);
        CREATE INDEX IF NOT EXISTS idx_alerts_severity ON alerts(severity);
        CREATE INDEX IF NOT EXISTS idx_maintenance_equipment ON maintenance_logs(equipment_id);
        CREATE INDEX IF NOT EXISTS idx_actions_equipment ON action_logs(equipment_id);
    """)

    conn.commit()
    conn.close()
    print("[OK] Database initialized successfully")


# ─── Equipment Operations ────────────────────────────────────────────────────

def get_all_equipment():
    """Get all equipment records."""
    conn = get_connection()
    rows = conn.execute("SELECT * FROM equipment ORDER BY criticality DESC, name").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_equipment_by_id(equipment_id: str):
    """Get a specific equipment record."""
    conn = get_connection()
    row = conn.execute("SELECT * FROM equipment WHERE id = ?", (equipment_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def update_equipment_status(equipment_id: str, status: str):
    """Update equipment status."""
    conn = get_connection()
    conn.execute("UPDATE equipment SET status = ? WHERE id = ?", (status, equipment_id))
    conn.commit()
    conn.close()


# ─── Sensor Operations ───────────────────────────────────────────────────────

def insert_sensor_reading(equipment_id: str, metric: str, value: float, unit: str, is_anomaly: bool = False, early_warning: bool = False, rul_hours: float = 999.0):
    """Insert a new sensor reading."""
    conn = get_connection()
    conn.execute(
        "INSERT INTO sensor_readings (equipment_id, timestamp, metric, value, unit, is_anomaly, early_warning, rul_hours) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (equipment_id, datetime.now().isoformat(), metric, value, unit, int(is_anomaly), int(early_warning), float(rul_hours))
    )
    conn.commit()
    conn.close()


def insert_sensor_readings_batch(readings: list):
    """Insert multiple sensor readings in a single transaction."""
    if not readings:
        return
    conn = get_connection()
    now = datetime.now().isoformat()
    conn.executemany(
        "INSERT INTO sensor_readings (equipment_id, timestamp, metric, value, unit, is_anomaly, early_warning, rul_hours) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [(r["equipment_id"], now, r["metric"], r["value"], r["unit"], int(r["is_anomaly"]), int(r["early_warning"]), float(r["rul_hours"])) for r in readings]
    )
    conn.commit()
    conn.close()


def get_latest_sensor_readings(equipment_id: str, limit: int = 50):
    """Get the latest sensor readings for an equipment."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM sensor_readings WHERE equipment_id = ? ORDER BY timestamp DESC LIMIT ?",
        (equipment_id, limit)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_sensor_readings_by_metric(equipment_id: str, metric: str, limit: int = 100):
    """Get readings for a specific metric."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM sensor_readings WHERE equipment_id = ? AND metric = ? ORDER BY timestamp DESC LIMIT ?",
        (equipment_id, metric, limit)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_anomaly_readings(equipment_id: str = None, limit: int = 50):
    """Get anomaly readings, optionally filtered by equipment."""
    conn = get_connection()
    if equipment_id:
        rows = conn.execute(
            "SELECT sr.*, e.name as equipment_name FROM sensor_readings sr JOIN equipment e ON sr.equipment_id = e.id WHERE sr.equipment_id = ? AND sr.is_anomaly = 1 ORDER BY sr.timestamp DESC LIMIT ?",
            (equipment_id, limit)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT sr.*, e.name as equipment_name FROM sensor_readings sr JOIN equipment e ON sr.equipment_id = e.id WHERE sr.is_anomaly = 1 ORDER BY sr.timestamp DESC LIMIT ?",
            (limit,)
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─── Maintenance Log Operations ──────────────────────────────────────────────

def get_maintenance_logs(equipment_id: str = None, limit: int = 50):
    """Get maintenance logs, optionally filtered by equipment."""
    conn = get_connection()
    if equipment_id:
        rows = conn.execute(
            "SELECT ml.*, e.name as equipment_name FROM maintenance_logs ml JOIN equipment e ON ml.equipment_id = e.id WHERE ml.equipment_id = ? ORDER BY ml.date DESC LIMIT ?",
            (equipment_id, limit)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT ml.*, e.name as equipment_name FROM maintenance_logs ml JOIN equipment e ON ml.equipment_id = e.id ORDER BY ml.date DESC LIMIT ?",
            (limit,)
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def insert_maintenance_log(equipment_id: str, log_type: str, description: str, outcome: str = None, performed_by: str = None, duration_hours: float = None, parts_replaced: str = None):
    """Insert a new maintenance log entry."""
    conn = get_connection()
    conn.execute(
        "INSERT INTO maintenance_logs (equipment_id, date, type, description, outcome, performed_by, duration_hours, parts_replaced) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (equipment_id, datetime.now().isoformat(), log_type, description, outcome, performed_by, duration_hours, parts_replaced)
    )
    conn.commit()
    conn.close()


# ─── Alert Operations ────────────────────────────────────────────────────────

def insert_alert(equipment_id: str, severity: str, title: str, message: str):
    """Insert a new alert."""
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO alerts (equipment_id, severity, title, message, timestamp) VALUES (?, ?, ?, ?, ?)",
        (equipment_id, severity, title, message, datetime.now().isoformat())
    )
    alert_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return alert_id


def get_alerts(acknowledged: bool = None, severity: str = None, limit: int = 50):
    """Get alerts with optional filtering."""
    conn = get_connection()
    query = "SELECT a.*, e.name as equipment_name FROM alerts a JOIN equipment e ON a.equipment_id = e.id WHERE 1=1"
    params = []

    if acknowledged is not None:
        query += " AND a.acknowledged = ?"
        params.append(int(acknowledged))
    if severity:
        query += " AND a.severity = ?"
        params.append(severity)

    query += " ORDER BY a.timestamp DESC LIMIT ?"
    params.append(limit)

    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_alert_by_id(alert_id: int):
    """Get a specific alert by ID."""
    conn = get_connection()
    row = conn.execute("SELECT a.*, e.name as equipment_name FROM alerts a JOIN equipment e ON a.equipment_id = e.id WHERE a.id = ?", (alert_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def acknowledge_alert(alert_id: int):
    """Acknowledge an alert."""
    conn = get_connection()
    conn.execute("UPDATE alerts SET acknowledged = 1 WHERE id = ?", (alert_id,))
    conn.commit()
    conn.close()


def resolve_alert(alert_id: int):
    """Resolve an alert."""
    conn = get_connection()
    conn.execute(
        "UPDATE alerts SET resolved = 1, resolved_at = ? WHERE id = ?",
        (datetime.now().isoformat(), alert_id)
    )
    conn.commit()
    conn.close()


# ─── Conversation Operations ─────────────────────────────────────────────────

def create_conversation(conv_id: str, title: str = None):
    """Create a new conversation."""
    conn = get_connection()
    now = datetime.now().isoformat()
    conn.execute(
        "INSERT INTO conversations (id, created_at, updated_at, title, messages) VALUES (?, ?, ?, ?, ?)",
        (conv_id, now, now, title or "New Conversation", "[]")
    )
    conn.commit()
    conn.close()


def get_conversation(conv_id: str):
    """Get a conversation by ID."""
    conn = get_connection()
    row = conn.execute("SELECT * FROM conversations WHERE id = ?", (conv_id,)).fetchone()
    conn.close()
    if row:
        result = dict(row)
        result["messages"] = json.loads(result["messages"])
        return result
    return None


def update_conversation_messages(conv_id: str, messages: list):
    """Update conversation messages."""
    conn = get_connection()
    conn.execute(
        "UPDATE conversations SET messages = ?, updated_at = ? WHERE id = ?",
        (json.dumps(messages), datetime.now().isoformat(), conv_id)
    )
    conn.commit()
    conn.close()


def get_all_conversations():
    """Get all conversations."""
    conn = get_connection()
    rows = conn.execute("SELECT id, created_at, updated_at, title FROM conversations ORDER BY updated_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─── Feedback Operations ─────────────────────────────────────────────────────

def insert_feedback(conversation_id: str, message_index: int, rating: str, correction: str = None):
    """Insert feedback for a response."""
    conn = get_connection()
    conn.execute(
        "INSERT INTO feedback (conversation_id, message_index, rating, correction, timestamp) VALUES (?, ?, ?, ?, ?)",
        (conversation_id, message_index, rating, correction, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()


def get_feedback_stats():
    """Get feedback statistics."""
    conn = get_connection()
    total = conn.execute("SELECT COUNT(*) as count FROM feedback").fetchone()["count"]
    positive = conn.execute("SELECT COUNT(*) as count FROM feedback WHERE rating = 'positive'").fetchone()["count"]
    negative = conn.execute("SELECT COUNT(*) as count FROM feedback WHERE rating = 'negative'").fetchone()["count"]
    corrections = conn.execute("SELECT COUNT(*) as count FROM feedback WHERE correction IS NOT NULL AND correction != ''").fetchone()["count"]
    conn.close()
    return {
        "total": total,
        "positive": positive,
        "negative": negative,
        "corrections": corrections,
        "accuracy": round(positive / total * 100, 1) if total > 0 else 0
    }


def get_recent_feedback(limit: int = 20):
    """Get recent feedback entries."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM feedback ORDER BY timestamp DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─── Dashboard Stats ─────────────────────────────────────────────────────────

def get_dashboard_stats():
    """Get aggregated dashboard statistics."""
    conn = get_connection()

    total_equipment = conn.execute("SELECT COUNT(*) as count FROM equipment").fetchone()["count"]
    operational = conn.execute("SELECT COUNT(*) as count FROM equipment WHERE status = 'operational'").fetchone()["count"]
    warning = conn.execute("SELECT COUNT(*) as count FROM equipment WHERE status = 'warning'").fetchone()["count"]
    critical = conn.execute("SELECT COUNT(*) as count FROM equipment WHERE status = 'critical'").fetchone()["count"]
    offline = conn.execute("SELECT COUNT(*) as count FROM equipment WHERE status = 'offline'").fetchone()["count"]

    active_alerts = conn.execute("SELECT COUNT(*) as count FROM alerts WHERE resolved = 0").fetchone()["count"]
    critical_alerts = conn.execute("SELECT COUNT(*) as count FROM alerts WHERE severity = 'critical' AND resolved = 0").fetchone()["count"]

    recent_maintenance = conn.execute(
        "SELECT COUNT(*) as count FROM maintenance_logs WHERE date >= datetime('now', '-7 days')"
    ).fetchone()["count"]

    conn.close()

    return {
        "total_equipment": total_equipment,
        "operational": operational,
        "warning": warning,
        "critical": critical,
        "offline": offline,
        "active_alerts": active_alerts,
        "critical_alerts": critical_alerts,
        "recent_maintenance": recent_maintenance,
        "uptime_percentage": round(operational / total_equipment * 100, 1) if total_equipment > 0 else 0
    }


# ─── OEE (Overall Equipment Effectiveness) ──────────────────────────────────

def get_oee_metrics(equipment_id: str = None):
    """
    Calculate OEE metrics (Availability, Performance, Quality) for equipment.
    OEE = Availability × Performance × Quality
    
    For Tata Steel, OEE benchmarks:
    - World-class: 85%+
    - Average: 60-65%
    - Below average: <50%
    """
    conn = get_connection()
    
    if equipment_id:
        # Single equipment OEE
        equipment = conn.execute("SELECT * FROM equipment WHERE id = ?", (equipment_id,)).fetchone()
        if not equipment:
            conn.close()
            return {}
        
        eq = dict(equipment)
        
        # Availability: ratio of actual operating time to planned production time
        # Based on equipment status and maintenance history
        total_hours = 168  # 7 days = 168 hours planned
        
        # Downtime from maintenance logs (last 7 days)
        maintenance_hours = conn.execute(
            "SELECT COALESCE(SUM(duration_hours), 0) as total FROM maintenance_logs WHERE equipment_id = ? AND date >= datetime('now', '-7 days')",
            (equipment_id,)
        ).fetchone()["total"]
        
        # Status-based downtime adjustment
        if eq["status"] == "critical":
            status_downtime = 24  # Assume 24 hrs unplanned downtime
        elif eq["status"] == "warning":
            status_downtime = 8
        elif eq["status"] == "offline":
            status_downtime = 48
        else:
            status_downtime = 2  # Minor stops
        
        actual_downtime = min(maintenance_hours + status_downtime, total_hours)
        availability = round((total_hours - actual_downtime) / total_hours * 100, 1)
        
        # Performance: ratio of actual production speed to ideal speed
        # Based on sensor readings deviation from normal
        recent_readings = conn.execute(
            "SELECT metric, value, is_anomaly FROM sensor_readings WHERE equipment_id = ? ORDER BY timestamp DESC LIMIT 20",
            (equipment_id,)
        ).fetchall()
        
        anomaly_count = sum(1 for r in recent_readings if r["is_anomaly"])
        total_readings = len(recent_readings) if recent_readings else 1
        
        # Performance penalty from anomalies
        performance_penalty = anomaly_count / total_readings * 15  # Up to 15% penalty
        performance = round(max(70, 95 - performance_penalty), 1)
        
        # Quality: ratio of good product to total product
        # Based on alert severity and equipment condition
        critical_alerts = conn.execute(
            "SELECT COUNT(*) as count FROM alerts WHERE equipment_id = ? AND severity = 'critical' AND resolved = 0",
            (equipment_id,)
        ).fetchone()["count"]
        high_alerts = conn.execute(
            "SELECT COUNT(*) as count FROM alerts WHERE equipment_id = ? AND severity = 'high' AND resolved = 0",
            (equipment_id,)
        ).fetchone()["count"]
        
        quality_penalty = critical_alerts * 5 + high_alerts * 2  # Each critical = 5%, high = 2%
        quality = round(max(80, 98 - quality_penalty), 1)
        
        oee = round(availability * performance * quality / 10000, 1)
        
        conn.close()
        
        return {
            "availability": availability,
            "performance": performance,
            "quality": quality,
            "oee": oee,
            "downtime_hours": actual_downtime,
            "anomaly_rate": round(anomaly_count / total_readings * 100, 1) if total_readings > 0 else 0,
            "critical_alerts": critical_alerts,
            "high_alerts": high_alerts,
            "oee_rating": "World-Class" if oee >= 85 else ("Good" if oee >= 65 else ("Average" if oee >= 50 else "Below Average")),
        }
    
    else:
        # Plant-wide OEE
        equipment_list = conn.execute("SELECT id, name, type, status, criticality FROM equipment").fetchall()
        
        total_availability = 0
        total_performance = 0
        total_quality = 0
        count = 0
        equipment_oee_list = []
        
        for eq in equipment_list:
            eq_dict = dict(eq)
            eq_oee = get_oee_metrics(eq_dict["id"])
            if eq_oee:
                total_availability += eq_oee["availability"]
                total_performance += eq_oee["performance"]
                total_quality += eq_oee["quality"]
                count += 1
                equipment_oee_list.append({
                    "equipment_id": eq_dict["id"],
                    "equipment_name": eq_dict["name"],
                    "oee": eq_oee["oee"],
                    "availability": eq_oee["availability"],
                    "performance": eq_oee["performance"],
                    "quality": eq_oee["quality"],
                })
        
        conn.close()
        
        if count == 0:
            return {}
        
        avg_availability = round(total_availability / count, 1)
        avg_performance = round(total_performance / count, 1)
        avg_quality = round(total_quality / count, 1)
        plant_oee = round(avg_availability * avg_performance * avg_quality / 10000, 1)
        
        return {
            "plant_availability": avg_availability,
            "plant_performance": avg_performance,
            "plant_quality": avg_quality,
            "plant_oee": plant_oee,
            "equipment_count": count,
            "equipment_oee_list": equipment_oee_list,
            "oee_rating": "World-Class" if plant_oee >= 85 else ("Good" if plant_oee >= 65 else ("Average" if plant_oee >= 50 else "Below Average")),
        }


# ─── Cost Summary ────────────────────────────────────────────────────────────

def get_cost_summary():
    """
    Get plant-wide cost impact summary with Tata Steel financial metrics.
    """
    conn = get_connection()
    
    # Equipment status distribution
    stats = get_dashboard_stats()
    
    # Tata Steel cost benchmarks
    CRITICAL_DOWNTIME_COST_PER_HR = 15000000  # ₹1.5 crore/hr for critical equipment
    WARNING_DOWNTIME_COST_PER_HR = 8000000    # ₹80 lakh/hr for warning equipment
    OPERATIONAL_RISK_COST_PER_HR = 2000000    # ₹20 lakh/hr risk for operational
    
    # Estimated annual downtime risk
    critical_risk = stats["critical"] * CRITICAL_DOWNTIME_COST_PER_HR * 48  # 48 hrs avg
    warning_risk = stats["warning"] * WARNING_DOWNTIME_COST_PER_HR * 24     # 24 hrs avg
    operational_risk = stats["operational"] * OPERATIONAL_RISK_COST_PER_HR * 8  # 8 hrs minor
    
    total_annual_risk = critical_risk + warning_risk + operational_risk
    
    # Maintenance cost estimates
    maintenance_logs = conn.execute(
        "SELECT COALESCE(SUM(duration_hours), 0) as total FROM maintenance_logs WHERE date >= datetime('now', '-30 days')"
    ).fetchone()["total"]
    
    avg_maintenance_cost_per_hr = 28000  # ₹28,000/hr per team
    monthly_maintenance_cost = maintenance_logs * avg_maintenance_cost_per_hr
    estimated_annual_maintenance = monthly_maintenance_cost * 12
    
    # Preventive vs reactive ratio
    preventive_count = conn.execute(
        "SELECT COUNT(*) as count FROM maintenance_logs WHERE type = 'preventive'"
    ).fetchone()["count"]
    corrective_count = conn.execute(
        "SELECT COUNT(*) as count FROM maintenance_logs WHERE type = 'corrective'"
    ).fetchone()["count"]
    
    total_maintenance = preventive_count + corrective_count
    preventive_ratio = round(preventive_count / total_maintenance * 100, 1) if total_maintenance > 0 else 0
    
    # ROI calculation
    preventive_roi = round(
        (total_annual_risk * 0.6) / estimated_annual_maintenance, 1  # 60% risk reduction from preventive
    ) if estimated_annual_maintenance > 0 else 0
    
    conn.close()
    
    return {
        "annual_downtime_risk": {
            "critical": critical_risk,
            "warning": warning_risk,
            "operational": operational_risk,
            "total": total_annual_risk,
        },
        "maintenance_costs": {
            "monthly_cost": monthly_maintenance_cost,
            "estimated_annual_cost": estimated_annual_maintenance,
            "maintenance_hours_last_30_days": maintenance_logs,
        },
        "preventive_vs_reactive": {
            "preventive_count": preventive_count,
            "corrective_count": corrective_count,
            "preventive_ratio": preventive_ratio,
            "target_ratio": 80,  # Tata Steel target: 80% preventive
        },
        "roi": {
            "preventive_roi": preventive_roi,
            "risk_reduction_percentage": 60,
            "net_savings": total_annual_risk * 0.6 - estimated_annual_maintenance,
        },
        "currency": "INR",
        "steel_price_per_tonne": 52000,
        "plant_production_tonnes_per_day": 5000,
    }


# ─── Sensor Trend Data ───────────────────────────────────────────────────────

def get_sensor_trend_data(equipment_id: str, metric: str = None, hours: int = 24):
    """
    Get sensor trend data formatted for charting, with threshold lines.
    Returns data points, threshold values, and anomaly markers.
    """
    conn = get_connection()
    
    from datetime import datetime, timedelta
    cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
    
    if metric:
        readings = conn.execute(
            "SELECT timestamp, metric, value, unit, is_anomaly, early_warning, rul_hours FROM sensor_readings WHERE equipment_id = ? AND metric = ? AND timestamp >= ? ORDER BY timestamp ASC",
            (equipment_id, metric, cutoff)
        ).fetchall()
    else:
        readings = conn.execute(
            "SELECT timestamp, metric, value, unit, is_anomaly, early_warning, rul_hours FROM sensor_readings WHERE equipment_id = ? AND timestamp >= ? ORDER BY timestamp ASC",
            (equipment_id, cutoff)
        ).fetchall()
    
    conn.close()
    
    # Group by metric
    trends = {}
    for r in readings:
        r_dict = dict(r)
        m = r_dict["metric"]
        if m not in trends:
            trends[m] = {
                "metric": m,
                "unit": r_dict["unit"],
                "data_points": [],
                "anomaly_points": [],
                "early_warning_points": [],
            }
        
        point = {
            "timestamp": r_dict["timestamp"],
            "value": r_dict["value"],
        }
        trends[m]["data_points"].append(point)
        
        if r_dict["is_anomaly"]:
            trends[m]["anomaly_points"].append(point)
        
        if r_dict["early_warning"]:
            trends[m]["early_warning_points"].append(point)
    
    # Add threshold data from seed_data
    from data.seed_data import SENSOR_METRICS
    equipment = get_equipment_by_id(equipment_id)
    if equipment:
        eq_type = equipment["type"]
        metrics_defs = SENSOR_METRICS.get(eq_type, [])
        
        for metric_def in metrics_defs:
            m = metric_def["metric"]
            if m in trends:
                trends[m]["thresholds"] = {
                    "normal": metric_def["normal"],
                    "warn": metric_def["warn"],
                    "critical": metric_def["critical"],
                    "min": metric_def["min"],
                    "max": metric_def["max"],
                }
    
    return trends


# ─── Predictive Maintenance Timeline ─────────────────────────────────────────

def get_predictive_timeline(equipment_id: str = None):
    """
    Get predictive maintenance timeline based on RUL estimates,
    degradation trends, and equipment condition.
    """
    conn = get_connection()
    
    if equipment_id:
        # Get latest RUL estimates for this equipment
        readings = conn.execute(
            "SELECT metric, value, rul_hours, early_warning, is_anomaly, timestamp FROM sensor_readings WHERE equipment_id = ? ORDER BY timestamp DESC LIMIT 50",
            (equipment_id,)
        ).fetchall()
        
        equipment = conn.execute("SELECT * FROM equipment WHERE id = ?", (equipment_id,)).fetchone()
        if not equipment:
            conn.close()
            return []
        
        eq = dict(equipment)
    else:
        # Get all equipment
        equipment_list = conn.execute("SELECT id, name, type, status, criticality, last_maintenance FROM equipment").fetchall()
        readings = []
        equipment = None
        eq = None
    
    conn.close()
    
    timeline = []
    
    if equipment_id and eq:
        # Single equipment timeline
        metrics_rul = {}
        for r in readings:
            r_dict = dict(r)
            m = r_dict["metric"]
            if m not in metrics_rul:
                metrics_rul[m] = r_dict["rul_hours"]
        
        # Find minimum RUL (most critical metric)
        min_rul = min(metrics_rul.values()) if metrics_rul else 999
        
        # Determine maintenance urgency
        if min_rul < 48:
            urgency = "IMMEDIATE"
            action = "Schedule emergency maintenance within 24-48 hours"
            color = "#ef4444"
        elif min_rul < 168:  # 1 week
            urgency = "URGENT"
            action = "Schedule maintenance within this week"
            color = "#f59e0b"
        elif min_rul < 720:  # 30 days
            urgency = "PLANNED"
            action = "Schedule preventive maintenance within 30 days"
            color = "#3b82f6"
        else:
            urgency = "MONITOR"
            action = "Continue monitoring, no immediate action needed"
            color = "#10b981"
        
        timeline.append({
            "equipment_id": eq["id"],
            "equipment_name": eq["name"],
            "equipment_type": eq["type"],
            "status": eq["status"],
            "criticality": eq["criticality"],
            "min_rul_hours": round(min_rul, 1),
            "urgency": urgency,
            "recommended_action": action,
            "color": color,
            "metrics_rul": metrics_rul,
            "last_maintenance": eq.get("last_maintenance"),
        })
    
    else:
        # All equipment timeline
        for eq_dict in equipment_list:
            eq_timeline = get_predictive_timeline(eq_dict["id"])
            if eq_timeline:
                timeline.extend(eq_timeline)
        
        # Sort by urgency (IMMEDIATE first)
        urgency_order = {"IMMEDIATE": 0, "URGENT": 1, "PLANNED": 2, "MONITOR": 3}
        timeline.sort(key=lambda x: urgency_order.get(x["urgency"], 4))
    
    return timeline


# ─── Action Log Operations ───────────────────────────────────────────────────

def insert_action_log(equipment_id: str, action_type: str, details: str, status: str = 'pending'):
    """Insert a new action log."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO action_logs (equipment_id, action_type, details, status, timestamp) VALUES (?, ?, ?, ?, ?)",
        (equipment_id, action_type, details, status, datetime.now().isoformat())
    )
    action_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return action_id


def get_action_logs(equipment_id: str = None, limit: int = 50):
    """Get action logs, optionally filtered by equipment."""
    conn = get_connection()
    if equipment_id:
        rows = conn.execute(
            "SELECT al.*, e.name as equipment_name FROM action_logs al JOIN equipment e ON al.equipment_id = e.id WHERE al.equipment_id = ? ORDER BY al.timestamp DESC LIMIT ?",
            (equipment_id, limit)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT al.*, e.name as equipment_name FROM action_logs al JOIN equipment e ON al.equipment_id = e.id ORDER BY al.timestamp DESC LIMIT ?",
            (limit,)
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_action_status(action_id: int, status: str):
    """Update action log status. If approved, we also execute status updates for equipment if relevant."""
    conn = get_connection()
    conn.execute("UPDATE action_logs SET status = ? WHERE id = ?", (status, action_id))
    
    # If a shutdown was approved, let's also update the equipment status to 'offline' in the database!
    if status.lower() == 'approved':
        action = conn.execute("SELECT equipment_id, action_type FROM action_logs WHERE id = ?", (action_id,)).fetchone()
        if action:
            act_dict = dict(action)
            if act_dict["action_type"] == "shutdown_equipment":
                conn.execute("UPDATE equipment SET status = 'offline' WHERE id = ?", (act_dict["equipment_id"],))
            elif act_dict["action_type"] == "release_emergency_stop" or act_dict["action_type"] == "clear_shutdown":
                conn.execute("UPDATE equipment SET status = 'operational' WHERE id = ?", (act_dict["equipment_id"],))
                
    conn.commit()
    conn.close()


# ─── Equipment Health Score ──────────────────────────────────────────────────

def get_equipment_health_score(equipment_id: str) -> dict:
    """
    Compute a composite health score (0-100) for an equipment.
    
    Weighted components:
    - Sensor anomaly rate (30%) — fewer anomalies = higher score
    - RUL estimate (30%) — longer RUL = higher score
    - Active alert severity (20%) — fewer/lower alerts = higher score
    - Maintenance recency (20%) — more recent maintenance = higher score
    """
    conn = get_connection()
    
    equipment = conn.execute("SELECT * FROM equipment WHERE id = ?", (equipment_id,)).fetchone()
    if not equipment:
        conn.close()
        return {"score": 50, "grade": "C", "factors": {}}
    
    eq = dict(equipment)
    
    # 1. Sensor anomaly rate (last 50 readings)
    readings = conn.execute(
        "SELECT is_anomaly, rul_hours FROM sensor_readings WHERE equipment_id = ? ORDER BY timestamp DESC LIMIT 50",
        (equipment_id,)
    ).fetchall()
    
    if readings:
        anomaly_count = sum(1 for r in readings if r["is_anomaly"])
        anomaly_rate = anomaly_count / len(readings)
        sensor_score = max(0, 100 - (anomaly_rate * 300))  # 0 anomalies = 100, 33% = 0
        
        # Min RUL across readings
        rul_values = [r["rul_hours"] for r in readings if r["rul_hours"] < 900]
        if rul_values:
            min_rul = min(rul_values)
            if min_rul < 24:
                rul_score = 10
            elif min_rul < 72:
                rul_score = 30
            elif min_rul < 168:
                rul_score = 55
            elif min_rul < 720:
                rul_score = 80
            else:
                rul_score = 100
        else:
            rul_score = 95  # No concerning RUL = healthy
    else:
        sensor_score = 80
        rul_score = 80
    
    # 2. Active alerts
    critical_count = conn.execute(
        "SELECT COUNT(*) as c FROM alerts WHERE equipment_id = ? AND resolved = 0 AND severity = 'critical'",
        (equipment_id,)
    ).fetchone()["c"]
    high_count = conn.execute(
        "SELECT COUNT(*) as c FROM alerts WHERE equipment_id = ? AND resolved = 0 AND severity = 'high'",
        (equipment_id,)
    ).fetchone()["c"]
    medium_count = conn.execute(
        "SELECT COUNT(*) as c FROM alerts WHERE equipment_id = ? AND resolved = 0 AND severity = 'medium'",
        (equipment_id,)
    ).fetchone()["c"]
    
    alert_penalty = critical_count * 25 + high_count * 15 + medium_count * 5
    alert_score = max(0, 100 - alert_penalty)
    
    # 3. Maintenance recency
    last_maint = conn.execute(
        "SELECT date FROM maintenance_logs WHERE equipment_id = ? ORDER BY date DESC LIMIT 1",
        (equipment_id,)
    ).fetchone()
    
    if last_maint:
        try:
            from datetime import datetime as dt
            maint_date = dt.fromisoformat(last_maint["date"])
            days_since = (dt.now() - maint_date).days
            if days_since <= 7:
                maint_score = 100
            elif days_since <= 30:
                maint_score = 80
            elif days_since <= 90:
                maint_score = 60
            else:
                maint_score = 40
        except:
            maint_score = 60
    else:
        maint_score = 50
    
    conn.close()
    
    # Composite weighted score
    score = round(
        sensor_score * 0.30 +
        rul_score * 0.30 +
        alert_score * 0.20 +
        maint_score * 0.20
    )
    score = max(0, min(100, score))
    
    # Grade
    if score >= 85:
        grade = "A"
        label = "Excellent"
    elif score >= 70:
        grade = "B"
        label = "Good"
    elif score >= 50:
        grade = "C"
        label = "Fair"
    elif score >= 30:
        grade = "D"
        label = "Poor"
    else:
        grade = "F"
        label = "Critical"
    
    return {
        "score": score,
        "grade": grade,
        "label": label,
        "factors": {
            "sensor_health": round(sensor_score),
            "rul_health": round(rul_score),
            "alert_health": round(alert_score),
            "maintenance_health": round(maint_score),
        }
    }

