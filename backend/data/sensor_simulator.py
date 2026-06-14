"""
Sensor simulator — Generates realistic real-time sensor readings
with gradual degradation patterns and random anomaly events.
Pushes data via WebSocket to connected clients.
"""

import asyncio
import json
import random
import math
from datetime import datetime
from data.database import (
    get_all_equipment, insert_sensor_readings_batch, insert_alert, get_connection
)
from data.seed_data import SENSOR_METRICS
from config import SENSOR_INTERVAL_SECONDS, ANOMALY_PROBABILITY


# Connected WebSocket clients (wrapped in dict to survive hot-reloads)
_ws_state = {"clients": set()}

def get_connected_clients():
    """Get the set of connected WebSocket clients."""
    return _ws_state["clients"]

# Track degradation state per equipment
_last_alert_time = {}
degradation_state = {}


ALERT_DEBOUNCE_SECONDS = 120


_alert_lock = asyncio.Lock()


async def _should_create_alert(equipment_id: str, metric: str, severity: str, title: str, message: str) -> bool:
    now = datetime.now()
    key = f"{equipment_id}_{metric}"
    async with _alert_lock:
        last_time = _last_alert_time.get(key)
        if last_time and (now - last_time).total_seconds() < ALERT_DEBOUNCE_SECONDS:
            return False
        _last_alert_time[key] = now
    return True

def predict_rul_regression(equipment_id: str, metric: str, critical_threshold: float, normal_val: float) -> float:
    """
    Predict Remaining Useful Life (RUL) in hours using a mathematical linear regression line.
    Fits y = mx + c to the last 30 database readings.
    """
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT value, timestamp FROM sensor_readings WHERE equipment_id = ? AND metric = ? ORDER BY timestamp DESC LIMIT 30",
            (equipment_id, metric)
        ).fetchall()
    except Exception as e:
        print(f"[ERR] predict_rul_regression query error: {e}")
        return 999.0
    finally:
        conn.close()

    if len(rows) < 10:
        return 999.0

    readings = [dict(r) for r in reversed(rows)]
    
    import datetime
    def parse_time(ts_str):
        try:
            return datetime.datetime.fromisoformat(ts_str)
        except Exception:
            return datetime.datetime.now()

    start_time = parse_time(readings[0]["timestamp"])
    x = []
    y = []
    for r in readings:
        delta = (parse_time(r["timestamp"]) - start_time).total_seconds() / 3600.0  # Time in hours
        x.append(delta)
        y.append(r["value"])

    n = len(x)
    sum_x = sum(x)
    sum_y = sum(y)
    sum_xx = sum(val * val for val in x)
    sum_xy = sum(x[i] * y[i] for i in range(n))

    denominator = (n * sum_xx - sum_x * sum_x)
    if abs(denominator) < 1e-7:
        return 999.0

    m = (n * sum_xy - sum_x * sum_y) / denominator
    c = (sum_y - m * sum_x) / n

    latest_val = y[-1]
    latest_time = x[-1]

    is_degrading = False
    if critical_threshold > normal_val:
        if m > 0.0001 and latest_val < critical_threshold:
            is_degrading = True
    else:
        if m < -0.0001 and latest_val > critical_threshold:
            is_degrading = True

    if is_degrading:
        target_time = (critical_threshold - c) / m
        rul_hours = target_time - latest_time
        if rul_hours > 0:
            return round(min(rul_hours, 999.0), 1)

    return 999.0


def get_sensor_value(metric_def: dict, equipment_id: str, eq_status: str) -> tuple:
    normal = metric_def["normal"]
    warn = metric_def["warn"]
    critical = metric_def["critical"]
    min_val = metric_def["min"]
    max_val = metric_def["max"]

    key = f"{equipment_id}_{metric_def['metric']}"
    if key not in degradation_state:
        # Seed the degradation level from the equipment's known condition so that
        # warning/critical units immediately produce realistically degraded
        # readings instead of ramping up from normal over several minutes.
        init_level = {"critical": 0.9, "warning": 0.55}.get(eq_status, 0.0)
        degradation_state[key] = {"level": init_level, "trend": 0.0}

    state = degradation_state[key]

    base_noise = random.gauss(0, (max_val - min_val) * 0.015)

    if eq_status in ("warning", "critical"):
        state["trend"] += random.gauss(0.001, 0.0005)
        state["level"] += state["trend"]
        state["level"] = max(0, min(state["level"], 1.0))
        degradation_offset = state["level"] * (warn - normal) * (1.5 if eq_status == "critical" else 0.7)
    else:
        state["level"] = max(0, state["level"] - 0.01)
        degradation_offset = state["level"] * (warn - normal) * 0.1

    anomaly_spike = 0
    force_anomaly = False
    if random.random() < ANOMALY_PROBABILITY:
        spike_direction = 1 if warn > normal else -1
        anomaly_spike = spike_direction * random.uniform(0.3, 0.8) * abs(critical - warn)
        force_anomaly = True

    cycle = math.sin(datetime.now().timestamp() / 300) * (max_val - min_val) * 0.02

    value = normal + degradation_offset + base_noise + anomaly_spike + cycle
    value = round(max(min_val, min(max_val, value)), 2)

    # ── ML-based statistical anomaly detection (robust z-score + EWMA) ──
    if "history" not in state:
        state["history"] = []
    history_before = list(state["history"])  # history excluding the new value
    state["history"].append(value)
    if len(state["history"]) > 30:
        state["history"].pop(0)

    try:
        from ml.anomaly_detector import online_anomaly_score
        ml_result = online_anomaly_score(history_before, value, state.get("ewma"))
        state["ewma"] = ml_result["ewma"]
        early_warning = ml_result["early_warning"]
        anomaly_score = ml_result["score"]
        ml_anomaly = ml_result["is_anomaly"]
    except Exception as e:
        print(f"[WARN] online anomaly scoring failed: {e}")
        early_warning = False
        anomaly_score = 0.0
        ml_anomaly = False

    # RUL calculation (Remaining Useful Life in hours) using Linear Regression
    if eq_status == "critical":
        rul_hours = 0.0
    else:
        try:
            rul_hours = predict_rul_regression(equipment_id, metric_def["metric"], critical, normal)
        except Exception as e:
            print(f"[WARN] RUL regression failed: {e}")
            rul_hours = 999.0

    if warn > normal:
        is_anomaly = value >= critical or force_anomaly or ml_anomaly
    else:
        is_anomaly = value <= critical or force_anomaly or ml_anomaly

    return value, is_anomaly, early_warning, rul_hours, anomaly_score


async def broadcast_to_clients(message: dict):
    """Send a message to all connected WebSocket clients."""
    clients = get_connected_clients()
    if not clients:
        return

    message_str = json.dumps(message)
    disconnected = set()

    for client in clients:
        try:
            await client.send_text(message_str)
        except Exception:
            disconnected.add(client)

    for client in disconnected:
        clients.discard(client)


async def run_sensor_simulator():
    """Main sensor simulation loop."""
    print(f"[SIM] Sensor simulator started (interval: {SENSOR_INTERVAL_SECONDS}s)")

    while True:
        try:
            equipment_list = get_all_equipment()
            batch_readings = []

            for eq in equipment_list:
                eq_type = eq["type"]
                metrics = SENSOR_METRICS.get(eq_type, [])

                for metric_def in metrics:
                    value, is_anomaly, early_warning, rul_hours, anomaly_score = get_sensor_value(metric_def, eq["id"], eq["status"])

                    reading = {
                        "equipment_id": eq["id"],
                        "equipment_name": eq["name"],
                        "metric": metric_def["metric"],
                        "value": value,
                        "unit": metric_def["unit"],
                        "is_anomaly": is_anomaly,
                        "early_warning": early_warning,
                        "anomaly_score": anomaly_score,
                        "rul_hours": rul_hours,
                        "timestamp": datetime.now().isoformat(),
                        "thresholds": {
                            "normal": metric_def["normal"],
                            "warn": metric_def["warn"],
                            "critical": metric_def["critical"]
                        }
                    }
                    batch_readings.append(reading)

                    if is_anomaly:
                        severity = "critical" if (
                            (metric_def["warn"] < metric_def["critical"] and value >= metric_def["critical"]) or
                            (metric_def["warn"] > metric_def["critical"] and value <= metric_def["critical"])
                        ) else "high"

                        alert_title = f"{metric_def['metric'].replace('_', ' ').title()} Alert \u2014 {eq['name']}"
                        alert_msg = (
                            f"{metric_def['metric'].replace('_', ' ').title()} reading of {value} {metric_def['unit']} "
                            f"{'exceeds' if value > metric_def['normal'] else 'below'} threshold. "
                            f"Normal: {metric_def['normal']} {metric_def['unit']}, "
                            f"Warning: {metric_def['warn']} {metric_def['unit']}, "
                            f"Critical: {metric_def['critical']} {metric_def['unit']}."
                        )

                        if not await _should_create_alert(eq["id"], metric_def["metric"], severity, alert_title, alert_msg):
                            continue

                        alert_id = await asyncio.to_thread(insert_alert, eq["id"], severity, alert_title, alert_msg)

                        # Broadcast alert
                        await broadcast_to_clients({
                            "type": "alert",
                            "data": {
                                "id": alert_id,
                                "equipment_id": eq["id"],
                                "equipment_name": eq["name"],
                                "severity": severity,
                                "title": alert_title,
                                "message": alert_msg,
                                "timestamp": datetime.now().isoformat()
                            }
                        })

            # Store batch in database asynchronously in a thread to prevent event loop blocking
            await asyncio.to_thread(insert_sensor_readings_batch, batch_readings)

            # Broadcast sensor readings batch
            await broadcast_to_clients({
                "type": "sensor_update",
                "data": batch_readings,
                "timestamp": datetime.now().isoformat()
            })

        except Exception as e:
            print(f"[ERR] Sensor simulator error: {e}")

        await asyncio.sleep(SENSOR_INTERVAL_SECONDS)
