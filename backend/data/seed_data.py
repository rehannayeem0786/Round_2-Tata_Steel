"""
Seed data module — Populates the database with realistic steel plant equipment,
sensor readings, maintenance history, and active anomalies.
"""

import sqlite3
import json
import random
from datetime import datetime, timedelta
from data.database import get_connection, init_database


# ─── Equipment Definitions ───────────────────────────────────────────────────

EQUIPMENT = [
    {
        "id": "BF-001",
        "name": "Blast Furnace #1",
        "type": "Blast Furnace",
        "zone": "Ironmaking",
        "status": "warning",
        "criticality": "critical",
        "install_date": "2015-03-15",
        "last_maintenance": "2026-04-20",
        "description": "Primary blast furnace for iron ore smelting. Capacity: 5000 tonnes/day. Uses hot blast air at 1200°C with coke as reductant.",
        "specifications": json.dumps({
            "capacity": "5000 tonnes/day",
            "working_volume": "2500 m³",
            "hearth_diameter": "12.5 m",
            "tuyere_count": 28,
            "hot_blast_temp": "1200°C",
            "top_pressure": "2.5 bar"
        })
    },
    {
        "id": "BOF-001",
        "name": "BOF Converter #1",
        "type": "Basic Oxygen Furnace",
        "zone": "Steelmaking",
        "status": "operational",
        "criticality": "critical",
        "install_date": "2016-07-10",
        "last_maintenance": "2026-05-05",
        "description": "Basic Oxygen Furnace for converting pig iron to steel. Capacity: 300 tonnes per heat. Uses oxygen lance for decarburization.",
        "specifications": json.dumps({
            "capacity": "300 tonnes/heat",
            "vessel_diameter": "7.5 m",
            "lance_height": "adjustable 1.5-3.0 m",
            "blow_time": "16-20 minutes",
            "tap_temperature": "1650°C",
            "oxygen_flow": "800 Nm³/min"
        })
    },
    {
        "id": "CCM-001",
        "name": "Continuous Caster #1",
        "type": "Continuous Casting Machine",
        "zone": "Casting",
        "status": "critical",
        "criticality": "critical",
        "install_date": "2017-01-20",
        "last_maintenance": "2026-03-15",
        "description": "6-strand continuous casting machine for producing steel billets. Casting speed: 2.5 m/min. Electromagnetic stirring equipped.",
        "specifications": json.dumps({
            "strands": 6,
            "casting_speed": "2.5 m/min",
            "billet_size": "150x150 mm",
            "mould_length": "800 mm",
            "secondary_cooling": "air-mist",
            "em_stirring": True
        })
    },
    {
        "id": "HRM-001",
        "name": "Hot Rolling Mill",
        "type": "Rolling Mill",
        "zone": "Rolling",
        "status": "operational",
        "criticality": "high",
        "install_date": "2016-05-08",
        "last_maintenance": "2026-05-25",
        "description": "Continuous hot strip mill with 6 finishing stands. Produces hot-rolled coils from 1.2mm to 16mm thickness. Entry temperature: 1050°C.",
        "specifications": json.dumps({
            "finishing_stands": 6,
            "max_width": "1850 mm",
            "thickness_range": "1.2 - 16 mm",
            "entry_temp": "1050°C",
            "coiling_temp": "550-700°C",
            "max_speed": "20 m/s"
        })
    },
    {
        "id": "CRM-001",
        "name": "Cold Rolling Mill",
        "type": "Rolling Mill",
        "zone": "Rolling",
        "status": "operational",
        "criticality": "high",
        "install_date": "2018-09-12",
        "last_maintenance": "2026-05-30",
        "description": "5-stand tandem cold rolling mill for producing cold-rolled sheets. Thickness reduction up to 90%. Strip tension controlled.",
        "specifications": json.dumps({
            "stands": 5,
            "max_width": "1650 mm",
            "min_thickness": "0.15 mm",
            "max_reduction": "90%",
            "rolling_speed": "25 m/s",
            "coolant": "palm oil emulsion"
        })
    },
    {
        "id": "LF-001",
        "name": "Ladle Furnace #1",
        "type": "Ladle Furnace",
        "zone": "Secondary Steelmaking",
        "status": "operational",
        "criticality": "high",
        "install_date": "2016-11-25",
        "last_maintenance": "2026-04-10",
        "description": "Ladle refining furnace for secondary steelmaking. Temperature adjustment, desulfurization, and inclusion removal. 300-tonne capacity.",
        "specifications": json.dumps({
            "capacity": "300 tonnes",
            "electrode_diameter": "500 mm",
            "transformer_power": "40 MVA",
            "argon_stirring": True,
            "wire_feeding": True,
            "heating_rate": "4°C/min"
        })
    },
    {
        "id": "CT-001",
        "name": "Cooling Tower #3",
        "type": "Cooling System",
        "zone": "Utilities",
        "status": "warning",
        "criticality": "medium",
        "install_date": "2014-02-28",
        "last_maintenance": "2026-02-15",
        "description": "Induced draft cooling tower serving the casting and rolling areas. Cooling capacity: 50,000 m³/hr water flow. Basin capacity: 2000 m³.",
        "specifications": json.dumps({
            "type": "Induced Draft",
            "flow_rate": "50000 m³/hr",
            "approach_temp": "5°C",
            "fan_power": "250 kW",
            "basin_capacity": "2000 m³",
            "fill_type": "PVC film"
        })
    },
    {
        "id": "HP-001",
        "name": "Hydraulic Press 2000T",
        "type": "Hydraulic Press",
        "zone": "Forging",
        "status": "operational",
        "criticality": "medium",
        "install_date": "2019-04-15",
        "last_maintenance": "2026-05-18",
        "description": "2000-tonne hydraulic forging press for heavy forging operations. 4-column design with programmable stroke control.",
        "specifications": json.dumps({
            "max_force": "2000 tonnes",
            "stroke": "800 mm",
            "table_size": "2000x1500 mm",
            "hydraulic_pressure": "315 bar",
            "pump_capacity": "1200 L/min",
            "columns": 4
        })
    },
    {
        "id": "CR-001",
        "name": "Overhead Crane 150T",
        "type": "Crane System",
        "zone": "Material Handling",
        "status": "operational",
        "criticality": "high",
        "install_date": "2015-08-20",
        "last_maintenance": "2026-05-10",
        "description": "150-tonne overhead travelling crane for ladle and scrap handling in the melt shop. Double girder design with 30m span.",
        "specifications": json.dumps({
            "capacity": "150 tonnes",
            "span": "30 m",
            "lift_height": "20 m",
            "hoist_speed": "5 m/min",
            "trolley_speed": "30 m/min",
            "bridge_speed": "60 m/min"
        })
    },
    {
        "id": "GR-001",
        "name": "Gas Recovery Unit",
        "type": "Gas Recovery",
        "zone": "Energy",
        "status": "operational",
        "criticality": "medium",
        "install_date": "2017-06-30",
        "last_maintenance": "2026-04-28",
        "description": "Blast furnace gas recovery and cleaning system. Recovers BF gas for power generation and heating. Dust removal via electrostatic precipitator.",
        "specifications": json.dumps({
            "gas_flow": "300000 Nm³/hr",
            "dust_removal": "Electrostatic Precipitator",
            "gas_holder_capacity": "80000 m³",
            "calorific_value": "3.5 MJ/Nm³",
            "pressure_recovery": "TRT equipped",
            "cleaning_efficiency": "99.5%"
        })
    }
]


# ─── Sensor Metric Definitions per Equipment Type ────────────────────────────

SENSOR_METRICS = {
    "Blast Furnace": [
        {"metric": "temperature", "unit": "°C", "min": 1100, "max": 1300, "normal": 1200, "warn": 1250, "critical": 1280},
        {"metric": "pressure", "unit": "bar", "min": 1.8, "max": 3.0, "normal": 2.5, "warn": 2.8, "critical": 2.95},
        {"metric": "vibration", "unit": "mm/s", "min": 0.5, "max": 8.0, "normal": 2.0, "warn": 5.0, "critical": 7.0},
        {"metric": "gas_flow", "unit": "Nm³/hr", "min": 200000, "max": 350000, "normal": 280000, "warn": 320000, "critical": 340000},
    ],
    "Basic Oxygen Furnace": [
        {"metric": "temperature", "unit": "°C", "min": 1500, "max": 1750, "normal": 1650, "warn": 1700, "critical": 1730},
        {"metric": "oxygen_flow", "unit": "Nm³/min", "min": 600, "max": 900, "normal": 800, "warn": 850, "critical": 880},
        {"metric": "vibration", "unit": "mm/s", "min": 0.3, "max": 6.0, "normal": 1.5, "warn": 4.0, "critical": 5.5},
        {"metric": "lance_position", "unit": "m", "min": 1.0, "max": 3.5, "normal": 2.0, "warn": 2.8, "critical": 3.2},
    ],
    "Continuous Casting Machine": [
        {"metric": "temperature", "unit": "°C", "min": 1450, "max": 1600, "normal": 1530, "warn": 1570, "critical": 1590},
        {"metric": "casting_speed", "unit": "m/min", "min": 1.0, "max": 3.5, "normal": 2.5, "warn": 3.0, "critical": 3.3},
        {"metric": "vibration", "unit": "mm/s", "min": 0.2, "max": 5.0, "normal": 1.0, "warn": 3.5, "critical": 4.5},
        {"metric": "mould_level", "unit": "mm", "min": -5, "max": 5, "normal": 0, "warn": 3, "critical": 4.5},
    ],
    "Rolling Mill": [
        {"metric": "temperature", "unit": "°C", "min": 60, "max": 120, "normal": 75, "warn": 95, "critical": 110},
        {"metric": "vibration", "unit": "mm/s", "min": 0.5, "max": 10.0, "normal": 2.5, "warn": 6.0, "critical": 8.5},
        {"metric": "motor_current", "unit": "A", "min": 200, "max": 600, "normal": 350, "warn": 500, "critical": 570},
        {"metric": "roll_force", "unit": "kN", "min": 5000, "max": 20000, "normal": 12000, "warn": 17000, "critical": 19000},
    ],
    "Ladle Furnace": [
        {"metric": "temperature", "unit": "°C", "min": 1550, "max": 1700, "normal": 1620, "warn": 1670, "critical": 1690},
        {"metric": "electrode_current", "unit": "kA", "min": 20, "max": 50, "normal": 35, "warn": 45, "critical": 48},
        {"metric": "argon_flow", "unit": "NL/min", "min": 100, "max": 600, "normal": 300, "warn": 500, "critical": 570},
        {"metric": "vibration", "unit": "mm/s", "min": 0.3, "max": 5.0, "normal": 1.2, "warn": 3.5, "critical": 4.5},
    ],
    "Cooling System": [
        {"metric": "water_temp_in", "unit": "°C", "min": 20, "max": 45, "normal": 28, "warn": 38, "critical": 43},
        {"metric": "water_temp_out", "unit": "°C", "min": 15, "max": 35, "normal": 22, "warn": 30, "critical": 33},
        {"metric": "flow_rate", "unit": "m³/hr", "min": 30000, "max": 55000, "normal": 48000, "warn": 38000, "critical": 33000},
        {"metric": "fan_vibration", "unit": "mm/s", "min": 0.5, "max": 8.0, "normal": 2.0, "warn": 5.5, "critical": 7.0},
    ],
    "Hydraulic Press": [
        {"metric": "hydraulic_pressure", "unit": "bar", "min": 250, "max": 330, "normal": 315, "warn": 280, "critical": 260},
        {"metric": "oil_temperature", "unit": "°C", "min": 30, "max": 75, "normal": 45, "warn": 60, "critical": 70},
        {"metric": "vibration", "unit": "mm/s", "min": 0.5, "max": 7.0, "normal": 1.8, "warn": 4.5, "critical": 6.0},
        {"metric": "cycle_time", "unit": "s", "min": 8, "max": 25, "normal": 12, "warn": 18, "critical": 22},
    ],
    "Crane System": [
        {"metric": "load_weight", "unit": "tonnes", "min": 0, "max": 160, "normal": 80, "warn": 140, "critical": 155},
        {"metric": "hoist_motor_temp", "unit": "°C", "min": 30, "max": 100, "normal": 55, "warn": 80, "critical": 95},
        {"metric": "vibration", "unit": "mm/s", "min": 0.3, "max": 6.0, "normal": 1.5, "warn": 4.0, "critical": 5.5},
        {"metric": "rope_tension", "unit": "kN", "min": 50, "max": 1500, "normal": 800, "warn": 1300, "critical": 1450},
    ],
    "Gas Recovery": [
        {"metric": "gas_flow", "unit": "Nm³/hr", "min": 200000, "max": 350000, "normal": 280000, "warn": 320000, "critical": 340000},
        {"metric": "dust_level", "unit": "mg/Nm³", "min": 0, "max": 15, "normal": 3, "warn": 8, "critical": 12},
        {"metric": "pressure", "unit": "kPa", "min": 5, "max": 30, "normal": 15, "warn": 25, "critical": 28},
        {"metric": "temperature", "unit": "°C", "min": 100, "max": 350, "normal": 200, "warn": 280, "critical": 330},
    ],
}


# ─── Maintenance History ─────────────────────────────────────────────────────

MAINTENANCE_HISTORY = [
    {"equipment_id": "BF-001", "date": "2026-04-20T14:30:00", "type": "preventive", "description": "Scheduled tuyere inspection and cooling system check. Replaced 3 damaged tuyere noses. Cleaned blast pipe connections.", "outcome": "All tuyeres functional. Slight wear detected on tuyere #14 — scheduled for next replacement.", "performed_by": "Maintenance Team A", "duration_hours": 12, "parts_replaced": "3x tuyere noses, gaskets"},
    {"equipment_id": "BF-001", "date": "2026-01-10T08:15:00", "type": "corrective", "description": "Emergency repair of burden distribution chute. Chute actuator failed causing uneven burden distribution.", "outcome": "Replaced actuator motor and position sensor. Calibrated chute angles.", "performed_by": "Maintenance Team A", "duration_hours": 8, "parts_replaced": "Chute actuator motor, position sensor"},
    {"equipment_id": "BOF-001", "date": "2026-05-05T10:45:00", "type": "preventive", "description": "Quarterly inspection of oxygen lance and vessel lining. Measured refractory thickness using laser scanner.", "outcome": "Refractory thickness at 65% of original. Estimated 200 more heats before relining needed.", "performed_by": "Maintenance Team B", "duration_hours": 6, "parts_replaced": "None"},
    {"equipment_id": "CCM-001", "date": "2026-03-15T16:20:00", "type": "corrective", "description": "Bearing replacement on segment roller #23 in strand 3. Bearing failure detected via vibration analysis.", "outcome": "Replaced both bearings. Root cause: inadequate lubrication due to blocked grease line.", "performed_by": "Maintenance Team C", "duration_hours": 5, "parts_replaced": "2x SKF 23128 bearings, grease line"},
    {"equipment_id": "CCM-001", "date": "2025-12-08T09:00:00", "type": "corrective", "description": "Mould copper plate replacement on strand 1. Surface cracking detected during routine inspection.", "outcome": "Replaced narrow face copper plate. Old plate sent for re-machining.", "performed_by": "Maintenance Team C", "duration_hours": 8, "parts_replaced": "Mould narrow face copper plate"},
    {"equipment_id": "HRM-001", "date": "2026-05-25T11:30:00", "type": "preventive", "description": "Work roll change and bearing inspection on finishing stand F3. Roll surface profiling check.", "outcome": "Roll profile within tolerance. Bearing temperatures normal. Hydraulic AGC calibrated.", "performed_by": "Rolling Team", "duration_hours": 4, "parts_replaced": "Work rolls (pair)"},
    {"equipment_id": "CRM-001", "date": "2026-05-30T13:10:00", "type": "preventive", "description": "Coolant system cleaning and filter replacement. Backup roll inspection on stand 2.", "outcome": "Coolant concentration adjusted to 3.5%. All filters replaced. Backup roll surface acceptable.", "performed_by": "Rolling Team", "duration_hours": 6, "parts_replaced": "Coolant filters (8x), emulsion additives"},
    {"equipment_id": "CT-001", "date": "2026-02-15T07:45:00", "type": "preventive", "description": "Fan motor bearing replacement and fill media inspection. Basin cleaning and biocide treatment.", "outcome": "Motor bearings replaced. 15% fill media degradation noted — full replacement recommended in 6 months.", "performed_by": "Utilities Team", "duration_hours": 10, "parts_replaced": "Fan motor bearings (2x), biocide chemicals"},
    {"equipment_id": "HP-001", "date": "2026-05-18T15:00:00", "type": "preventive", "description": "Hydraulic system oil analysis and filter change. Seal inspection on main cylinder.", "outcome": "Oil analysis normal — no metal particles detected. Minor seepage on main cylinder — monitor.", "performed_by": "Forge Team", "duration_hours": 3, "parts_replaced": "Hydraulic oil filters (4x)"},
    {"equipment_id": "CR-001", "date": "2026-05-10T08:30:00", "type": "preventive", "description": "Hoist wire rope inspection and lubrication. Brake pad measurement and electrical system check.", "outcome": "Wire rope at 88% capacity — replace within 12 months. Brake pads at 60% — adequate.", "performed_by": "Crane Team", "duration_hours": 5, "parts_replaced": "Wire rope lubricant"},
    {"equipment_id": "GR-001", "date": "2026-04-28T14:15:00", "type": "preventive", "description": "Electrostatic precipitator cleaning and high-voltage transformer inspection. Gas holder seal check.", "outcome": "ESP efficiency restored to 99.5%. Gas holder seal in good condition.", "performed_by": "Energy Team", "duration_hours": 8, "parts_replaced": "ESP plates (4x sections)"},
    {"equipment_id": "LF-001", "date": "2026-04-10T10:05:00", "type": "corrective", "description": "Electrode arm hydraulic cylinder repair. Slow response detected during arc heating.", "outcome": "Replaced hydraulic cylinder seals and recalibrated position control.", "performed_by": "Maintenance Team B", "duration_hours": 6, "parts_replaced": "Hydraulic cylinder seals, hydraulic fluid"},
]


def seed_database():
    """Populate the database with simulated steel plant data."""
    init_database()
    conn = get_connection()
    cursor = conn.cursor()

    # Check if data already exists
    count = cursor.execute("SELECT COUNT(*) as count FROM equipment").fetchone()["count"]
    if count > 0:
        print("[SKIP] Database already seeded, skipping...")
        # Re-apply canonical statuses every startup so the Digital Twin always
        # shows the correct warning/critical states (e.g. after a scenario reset).
        for eq in EQUIPMENT:
            cursor.execute(
                "UPDATE equipment SET status = ? WHERE id = ?",
                (eq["status"], eq["id"])
            )
        conn.commit()
        conn.close()
        return

    # Insert equipment
    for eq in EQUIPMENT:
        cursor.execute(
            "INSERT INTO equipment (id, name, type, zone, status, criticality, install_date, last_maintenance, description, specifications) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (eq["id"], eq["name"], eq["type"], eq["zone"], eq["status"], eq["criticality"], eq["install_date"], eq["last_maintenance"], eq["description"], eq["specifications"])
        )

    # Insert maintenance history
    for log in MAINTENANCE_HISTORY:
        cursor.execute(
            "INSERT INTO maintenance_logs (equipment_id, date, type, description, outcome, performed_by, duration_hours, parts_replaced) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (log["equipment_id"], log["date"], log["type"], log["description"], log["outcome"], log["performed_by"], log["duration_hours"], log["parts_replaced"])
        )

    # Generate historical sensor readings (last 7 days, every 30 minutes)
    now = datetime.now()
    for eq in EQUIPMENT:
        eq_type = eq["type"]
        metrics = SENSOR_METRICS.get(eq_type, [])

        for metric_def in metrics:
            # Generate readings for the last 7 days
            for hours_ago in range(0, 168, 1):  # every hour for 7 days
                timestamp = now - timedelta(hours=hours_ago)
                normal = metric_def["normal"]
                warn = metric_def["warn"]

                # Add degradation pattern for warning/critical equipment
                degradation = 0
                if eq["status"] in ("warning", "critical") and hours_ago < 48:
                    # Equipment degrading over last 2 days
                    degradation = (48 - hours_ago) / 48 * (warn - normal) * (1.2 if eq["status"] == "critical" else 0.8)

                # Generate realistic value with noise
                noise = random.gauss(0, (metric_def["max"] - metric_def["min"]) * 0.02)
                value = normal + degradation + noise

                is_anomaly = abs(value) >= abs(warn) if warn > normal else value <= warn

                cursor.execute(
                    "INSERT INTO sensor_readings (equipment_id, timestamp, metric, value, unit, is_anomaly) VALUES (?, ?, ?, ?, ?, ?)",
                    (eq["id"], timestamp.isoformat(), metric_def["metric"], round(value, 2), metric_def["unit"], int(is_anomaly))
                )

    # Insert some active alerts for warning/critical equipment
    active_alerts = [
        {"equipment_id": "BF-001", "severity": "high", "title": "Elevated Vibration — Blast Furnace",
         "message": "Vibration levels on Blast Furnace #1 have exceeded warning threshold (5.2 mm/s vs 5.0 mm/s limit). Trend shows gradual increase over 36 hours. Possible causes: burden distribution issue, cooling system imbalance, or structural wear."},
        {"equipment_id": "BF-001", "severity": "medium", "title": "Temperature Trending Up — Blast Furnace",
         "message": "Hot blast temperature trending upward. Current: 1248°C (warning at 1250°C). Monitor closely and check cooling water flow rates."},
        {"equipment_id": "CCM-001", "severity": "critical", "title": "Bearing Failure Imminent — Caster Strand 4",
         "message": "Vibration signature on segment roller bearing in strand 4 matches known failure pattern. RMS velocity: 4.8 mm/s (critical at 4.5 mm/s). Immediate inspection required. Similar failure occurred on strand 3 in March 2026."},
        {"equipment_id": "CCM-001", "severity": "high", "title": "Mould Level Instability — Caster",
         "message": "Mould level fluctuations detected on strand 2. Peak deviation: ±3.2mm (normal: ±1mm). Possible causes: SEN clogging, tundish nozzle wear, or flow control valve issue."},
        {"equipment_id": "CT-001", "severity": "medium", "title": "Reduced Cooling Efficiency — Tower #3",
         "message": "Cooling tower outlet temperature 2.5°C above expected. Fill media degradation (noted in Feb 2026 inspection) likely contributing. Monitor approach temperature."},
    ]

    for alert in active_alerts:
        cursor.execute(
            "INSERT INTO alerts (equipment_id, severity, title, message, timestamp) VALUES (?, ?, ?, ?, ?)",
            (alert["equipment_id"], alert["severity"], alert["title"], alert["message"],
             (now - timedelta(hours=random.randint(1, 24))).isoformat())
        )

    conn.commit()
    conn.close()
    print("[OK] Database seeded with steel plant data")


if __name__ == "__main__":
    seed_database()
