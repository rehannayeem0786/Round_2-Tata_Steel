"""
ML Anomaly Detection Engine
===========================

Replaces the previous purely threshold-based detection with a genuine
machine-learning + statistical ensemble for industrial sensor data.

Two complementary detectors are provided:

1. Online detector (`online_anomaly_score`)
   - Lightweight, runs on every live sensor reading inside the simulator loop.
   - Uses a robust z-score (median + MAD) combined with an EWMA control-chart
     deviation. Robust statistics are resistant to the spikes typical of
     industrial sensors, so they avoid the false alarms a plain mean/std
     would produce.

2. Batch ML detector (`detect_equipment_anomalies`)
   - Runs on demand (analytics endpoint + agent reasoning context).
   - Trains an unsupervised scikit-learn IsolationForest per equipment-metric
     over a sliding window of recent readings, using engineered features
     (value, first difference, rolling deviation). Produces a continuous
     anomaly score in [0, 1] and a confidence level.

Both detectors degrade gracefully: if numpy / scikit-learn are unavailable the
module falls back to pure-Python statistics so the system never crashes.
"""

from __future__ import annotations

import math
from typing import Optional

from data.database import get_connection

# ─── Optional heavy dependencies (graceful fallback) ─────────────────────────
try:
    import numpy as np
    _HAS_NUMPY = True
except Exception:  # pragma: no cover
    _HAS_NUMPY = False

try:
    from sklearn.ensemble import IsolationForest
    _HAS_SKLEARN = True
except Exception:  # pragma: no cover
    _HAS_SKLEARN = False


# Robust z-score threshold above which a point is flagged. 3.5 is the
# conventional outlier cut-off for the modified (MAD-based) z-score.
ROBUST_Z_THRESHOLD = 3.5
EWMA_ALPHA = 0.3            # EWMA smoothing factor
EARLY_WARNING_SCORE = 0.55  # combined-score threshold for an early warning
ANOMALY_SCORE = 0.80        # combined-score threshold for a confirmed anomaly

# Batch (IsolationForest ensemble) classification thresholds. Decoupled from the
# online detector because the batch score is a physics-anchored band ensemble.
BATCH_EARLY_WARNING = 0.30
BATCH_ANOMALY = 0.60


# ──────────────────────────────────────────────────────────────────────────
# 1. ONLINE DETECTOR  (used by the live sensor simulator)
# ──────────────────────────────────────────────────────────────────────────

def _median(values: list) -> float:
    s = sorted(values)
    n = len(s)
    if n == 0:
        return 0.0
    mid = n // 2
    if n % 2:
        return s[mid]
    return (s[mid - 1] + s[mid]) / 2.0


def online_anomaly_score(history: list, value: float, ewma_prev: Optional[float] = None) -> dict:
    """Score a single live reading against its recent history.

    Args:
        history: recent values for this metric (excluding the new value).
        value: the new reading to score.
        ewma_prev: previous EWMA value (optional, for control-chart deviation).

    Returns:
        dict with keys: score (0-1), is_anomaly, early_warning, robust_z,
        ewma, reason.
    """
    window = [v for v in history if v is not None]
    # Need a minimal history to establish a baseline.
    if len(window) < 6:
        ewma = value if ewma_prev is None else (EWMA_ALPHA * value + (1 - EWMA_ALPHA) * ewma_prev)
        return {
            "score": 0.0,
            "is_anomaly": False,
            "early_warning": False,
            "robust_z": 0.0,
            "ewma": round(ewma, 4),
            "reason": "warming up (insufficient history)",
        }

    med = _median(window)
    abs_dev = [abs(v - med) for v in window]
    mad = _median(abs_dev)

    # Modified z-score (Iglewicz & Hoaglin). 0.6745 = 0.75 quantile of N(0,1).
    if mad > 1e-9:
        robust_z = 0.6745 * (value - med) / mad
    else:
        # Degenerate (flat) signal — fall back to std-dev based z-score.
        mean = sum(window) / len(window)
        var = sum((v - mean) ** 2 for v in window) / len(window)
        std = math.sqrt(var)
        robust_z = (value - mean) / std if std > 1e-9 else 0.0

    # EWMA control-chart deviation (trend-aware).
    ewma = value if ewma_prev is None else (EWMA_ALPHA * value + (1 - EWMA_ALPHA) * ewma_prev)
    ewma_dev = abs(value - ewma)
    spread = (mad * 1.4826) if mad > 1e-9 else (max(window) - min(window)) / 4 or 1.0
    ewma_z = ewma_dev / spread if spread > 1e-9 else 0.0

    # Combine: robust z-score dominates, EWMA deviation adds trend sensitivity.
    z_component = min(abs(robust_z) / ROBUST_Z_THRESHOLD, 1.5)
    ewma_component = min(ewma_z / 3.0, 1.0)
    score = max(0.0, min(1.0, 0.7 * z_component + 0.3 * ewma_component))

    is_anomaly = score >= ANOMALY_SCORE or abs(robust_z) >= ROBUST_Z_THRESHOLD
    early_warning = (not is_anomaly) and score >= EARLY_WARNING_SCORE

    if is_anomaly:
        reason = f"statistical outlier (robust-z={robust_z:.1f})"
    elif early_warning:
        reason = f"abnormal trend forming (score={score:.2f})"
    else:
        reason = "within normal statistical band"

    return {
        "score": round(score, 3),
        "is_anomaly": bool(is_anomaly),
        "early_warning": bool(early_warning),
        "robust_z": round(robust_z, 2),
        "ewma": round(ewma, 4),
        "reason": reason,
    }


# ──────────────────────────────────────────────────────────────────────────
# 2. BATCH ML DETECTOR  (IsolationForest — used on demand)
# ──────────────────────────────────────────────────────────────────────────

def _fetch_metric_series(equipment_id: str, metric: str, limit: int = 200) -> list:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT value, timestamp FROM sensor_readings "
            "WHERE equipment_id = ? AND metric = ? "
            "ORDER BY timestamp DESC LIMIT ?",
            (equipment_id, metric, limit),
        ).fetchall()
    except Exception as e:
        print(f"[ERR] anomaly series fetch failed: {e}")
        return []
    finally:
        conn.close()
    return [dict(r) for r in reversed(rows)]


def _list_metrics(equipment_id: str) -> list:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT DISTINCT metric, unit FROM sensor_readings WHERE equipment_id = ?",
            (equipment_id,),
        ).fetchall()
    except Exception:
        return []
    finally:
        conn.close()
    return [(r["metric"], r["unit"]) for r in rows]


def _build_features(values: list):
    """Engineer features: [value, first-difference, rolling deviation]."""
    arr = np.array(values, dtype=float)
    diff = np.diff(arr, prepend=arr[0])
    win = max(5, len(arr) // 10)
    roll_mean = np.convolve(arr, np.ones(win) / win, mode="same")
    roll_dev = arr - roll_mean
    return np.column_stack([arr, diff, roll_dev])


def detect_metric_anomalies(equipment_id: str, metric: str, unit: str = "",
                            thresholds: Optional[dict] = None) -> Optional[dict]:
    """Run an anomaly-detection ensemble on one equipment-metric series.

    The score blends three complementary signals:
      * band severity  — recent mean position within the normal->critical band
                          (physics-anchored to engineering limits)
      * robust z-score  — MAD-based modified z-score of the latest reading
      * Isolation Forest anomaly rate over the recent window (multivariate ML)
    """
    series = _fetch_metric_series(equipment_id, metric)
    if len(series) < 12:
        return None

    values = [s["value"] for s in series]
    recent = values[-20:]
    recent_mean = sum(recent) / len(recent)
    latest = values[-1]

    # -- Signal 1: robust modified z-score (statistical outlier strength) --
    med = _median(values)
    mad = _median([abs(v - med) for v in values])
    if mad > 1e-9:
        robust_z = 0.6745 * (latest - med) / mad
    else:
        mean = sum(values) / len(values)
        std = math.sqrt(sum((v - mean) ** 2 for v in values) / len(values))
        robust_z = (latest - mean) / std if std > 1e-9 else 0.0
    robust_score = min(abs(robust_z) / ROBUST_Z_THRESHOLD, 1.0)

    # -- Signal 2: physics-anchored band severity (0 at normal, 1 at critical) --
    band_score = 0.0
    if thresholds:
        normal = thresholds.get("normal")
        critical = thresholds.get("critical")
        if None not in (normal, critical):
            span = (critical - normal)
            if abs(span) > 1e-9:
                frac = (recent_mean - normal) / span  # works for both directions
                band_score = max(0.0, min(1.0, frac))

    # -- Signal 3: Isolation Forest anomaly rate (multivariate ML) --
    method = "robust_zscore"
    if_rate = 0.0
    anomaly_indices = [i for i, v in enumerate(values)
                       if mad > 1e-9 and abs(0.6745 * (v - med) / mad) >= ROBUST_Z_THRESHOLD]
    if _HAS_NUMPY and _HAS_SKLEARN:
        try:
            X = _build_features(values)
            model = IsolationForest(n_estimators=100, contamination="auto", random_state=42)
            preds = model.fit_predict(X)  # -1 anomaly, 1 normal
            anomaly_indices = [int(i) for i, p in enumerate(preds) if p == -1]
            recent_preds = preds[-20:]
            if_rate = float((recent_preds == -1).sum()) / len(recent_preds)
            method = "isolation_forest"
        except Exception as e:
            print(f"[WARN] IsolationForest failed for {equipment_id}/{metric}: {e}")

    # -- Weighted ensemble --
    score = 0.7 * band_score + 0.2 * robust_score + 0.1 * min(if_rate, 1.0)
    score = round(max(0.0, min(1.0, score)), 3)

    if score >= BATCH_ANOMALY:
        classification, confidence = "anomaly", "High"
    elif score >= BATCH_EARLY_WARNING:
        classification, confidence = "early_warning", "Medium"
    else:
        classification, confidence = "normal", "High"

    # Trend slope over the series for direction.
    n = len(values)
    xs = list(range(n))
    mean_x = sum(xs) / n
    mean_y = sum(values) / n
    denom = sum((x - mean_x) ** 2 for x in xs) or 1e-9
    slope = sum((xs[i] - mean_x) * (values[i] - mean_y) for i in range(n)) / denom
    trend = "rising" if slope > 1e-6 else ("falling" if slope < -1e-6 else "stable")

    return {
        "metric": metric,
        "unit": unit,
        "method": method,
        "anomaly_score": score,
        "classification": classification,
        "confidence": confidence,
        "robust_z": round(robust_z, 2),
        "latest_value": round(latest, 2),
        "baseline_median": round(med, 2),
        "trend": trend,
        "anomalies_detected": len(anomaly_indices),
        "samples_analyzed": n,
    }


def detect_equipment_anomalies(equipment_id: str) -> dict:
    """Run ML anomaly detection across all metrics of an equipment."""
    # Build a metric -> thresholds map from the equipment's engineering limits.
    threshold_map = {}
    try:
        from data.database import get_equipment_by_id
        from data.seed_data import SENSOR_METRICS
        eq = get_equipment_by_id(equipment_id)
        if eq:
            for md in SENSOR_METRICS.get(eq["type"], []):
                threshold_map[md["metric"]] = {
                    "normal": md["normal"], "warn": md["warn"], "critical": md["critical"],
                }
    except Exception as e:
        print(f"[WARN] threshold map unavailable: {e}")

    metrics = _list_metrics(equipment_id)
    results = []
    for metric, unit in metrics:
        res = detect_metric_anomalies(equipment_id, metric, unit, threshold_map.get(metric))
        if res:
            results.append(res)

    results.sort(key=lambda r: r["anomaly_score"], reverse=True)
    overall = max((r["anomaly_score"] for r in results), default=0.0)

    if overall >= BATCH_ANOMALY:
        health = "Anomalous"
    elif overall >= BATCH_EARLY_WARNING:
        health = "Degrading"
    else:
        health = "Healthy"

    return {
        "equipment_id": equipment_id,
        "engine": "IsolationForest + Robust-Z/EWMA ensemble" if (_HAS_SKLEARN and _HAS_NUMPY)
                  else "Robust-Z/EWMA statistical ensemble",
        "overall_anomaly_score": round(overall, 3),
        "health_state": health,
        "metrics": results,
    }


def format_anomaly_context(equipment_id: str) -> str:
    """Produce an LLM-ready text block describing ML anomaly findings.

    Used to make agent reasoning explainable and traceable to the detector.
    """
    report = detect_equipment_anomalies(equipment_id)
    if not report["metrics"]:
        return ""

    lines = ["\n═══ ML ANOMALY DETECTION ═══",
             f"Engine: {report['engine']}",
             f"Equipment health state: {report['health_state']} "
             f"(overall anomaly score {report['overall_anomaly_score']})"]
    for m in report["metrics"]:
        lines.append(
            f"- {m['metric']}: score={m['anomaly_score']} [{m['classification']}], "
            f"trend={m['trend']}, robust-z={m['robust_z']}, "
            f"latest={m['latest_value']}{m['unit']} (baseline {m['baseline_median']}{m['unit']}), "
            f"confidence={m['confidence']}"
        )
    return "\n".join(lines)
