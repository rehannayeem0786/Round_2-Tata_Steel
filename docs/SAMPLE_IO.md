# Sample Input and Output Demonstrations

## Sample 1: Diagnostic Query

### Input
```
The blast furnace is showing unusual vibration readings. What could be wrong?
```

### Expected Output (AI-Generated)
```
## 🔍 Fault Diagnosis

Based on the current sensor data for Blast Furnace #1 (BF-001), vibration levels 
have reached 5.2 mm/s RMS, exceeding the warning threshold of 5.0 mm/s.

**Most Probable Causes (ranked by likelihood):**
1. **Burden Distribution Issue** (High Confidence) — Uneven burden distribution 
   causing gas channeling. This is consistent with the elevated vibration trend 
   over the past 36 hours. Historical record MR-2026-001 shows a similar pattern 
   when the distribution chute actuator failed.

2. **Cooling System Imbalance** (Medium Confidence) — Uneven cooling can cause 
   thermal stress and vibration. Temperature readings show slight upward trend.

3. **Structural Wear** (Low Confidence) — Long-term wear on furnace shell 
   components. Equipment installed in 2015 (11 years of service).

## 🔗 Root Cause Analysis
Using 5-Why methodology:
- Why is vibration high? → Uneven gas flow pattern
- Why is gas flow uneven? → Burden distribution may be asymmetric
- Why is burden distribution asymmetric? → Possible chute position deviation
- Why chute position deviation? → Actuator motor or sensor drift
- Why motor/sensor issues? → Previous failure (Jan 2026) may indicate pattern

## ⏱️ Remaining Useful Life Estimate
Based on current degradation rate: **2-4 weeks** before vibration reaches 
critical threshold (7.0 mm/s). However, if root cause is burden distribution, 
equipment can continue operating with reduced blast volume.

## ⚠️ Early Warnings
- Temperature trending toward warning threshold (1248°C vs 1250°C limit)
- Gas flow pattern should be monitored for channeling signs

## 📊 Confidence Assessment
Overall confidence: **Medium-High** (78%)
Based on: Sensor data consistency, historical pattern match, knowledge base alignment
```

---

## Sample 2: Risk Assessment Query

### Input
```
What is the risk level for the continuous caster bearing assembly?
```

### Expected Output (AI-Generated)
```
## 🚦 Risk Classification
**Risk Level: CRITICAL** 🔴

The continuous caster CCM-001 strand 4 segment roller bearing is showing 
vibration of 4.8 mm/s, which exceeds the critical threshold of 4.5 mm/s.

## ⏰ Urgency Assessment
**Urgency: IMMEDIATE** — Inspection and bearing replacement should be 
scheduled within the next 24-48 hours.

## 🏭 Plant Impact Analysis
- **Process Criticality**: CRITICAL — Caster is a bottleneck; failure stops 
  all upstream steelmaking
- **Cascading Risk**: If strand 4 bearing seizes, strand must be stopped. 
  If multiple strands affected, entire caster stops.
- **Production Impact**: ~250 tonnes/hour lost per strand
- **Safety Risk**: Bearing seizure could cause strand breakout (liquid steel 
  leak) — SAFETY CRITICAL

## 📋 Priority Score Breakdown
| Factor | Score | Weight | Weighted |
|--------|-------|--------|----------|
| Process Criticality | 10/10 | 30% | 3.0 |
| Delay Severity | 9/10 | 25% | 2.25 |
| Failure Probability | 8/10 | 25% | 2.0 |
| Spares Availability | 7/10 | 20% | 1.4 |
| **Total Priority Score** | | | **8.65/10** |

## 🎯 Recommended Action Timeline
- **NOW**: Reduce casting speed on strand 4 by 20%
- **Within 4 hours**: Detailed vibration analysis and bearing inspection
- **Within 24 hours**: Replace bearing during next sequence change
- **Within 1 week**: Inspect all strand 4 segment roller bearings
```

---

## Sample 3: Maintenance Recommendation

### Input
```
How do I replace a bearing on the caster segment roller?
```

### Expected Output (AI-Generated)
```
## 🔧 Immediate Actions (Do Now)
1. Coordinate with production for strand shutdown window
2. Verify replacement bearing is in stock (SKF 23128, C3 clearance)
3. Prepare work permit and LOTO procedure
4. Arrange crane availability for roller segment handling

## 📅 Step-by-Step Replacement Procedure
(Based on SOP-MECH-001: Bearing Replacement)

### Pre-Work (30 min)
1. Apply LOTO on all energy sources for the affected strand
2. Drain cooling water from segment area
3. Allow cooling to below 50°C

### Removal (2-3 hours)
4. Unbolt segment cover bolts in star pattern
5. Use hydraulic bearing puller — apply even force
6. **NEVER use hammers on precision surfaces**
7. Inspect shaft for damage after removal

### Installation (2-3 hours)
8. Clean shaft bearing seat with solvent
9. Heat new bearing to 80-100°C using induction heater
10. Slide onto shaft and hold against shoulder until cool
11. Install new seals (lip facing lubricant side)
12. Reassemble housing, torque bolts to spec

### Post-Installation (1 hour)
13. Fill with grease (30-50% of free space — do NOT over-grease)
14. Trial run at low speed for 30 minutes
15. Verify temperature < ambient + 40°C
16. Check vibration < 2.0 mm/s

## 🔩 Required Spare Parts & Materials
- 2x SKF 23128 spherical roller bearings (C3 clearance)
- 1x Bearing seal kit
- SKF LGMT 3 grease
- Non-chlorinated cleaning solvent
- Lint-free wipes

## ⏱️ Estimated Timeline & Resources
- **Duration**: 4-6 hours
- **Personnel**: 2 mechanics + 1 crane operator
- **Tools**: Hydraulic puller, induction heater, torque wrench

## 🛡️ Safety Precautions
- LOTO mandatory — minimum 2 persons
- PPE: Safety helmet, steel-toe boots, heat-resistant gloves
- Equipment must be below 50°C before work
```

---

## Sample 4: Report Generation

### Input
```
Generate a maintenance status report for the plant
```

### Expected Output
A comprehensive plant-wide report including:
- Executive summary with key metrics
- Equipment fleet status table
- Active alert summary
- Recent maintenance activities
- Risk assessment for critical equipment
- Recommendations for upcoming actions

---

## Sample 5: Alert Analysis

### Input
```
What are the current active alerts?
```

### Expected Output
Analysis of all active alerts with:
- Severity assessment for each
- Prioritized list by urgency
- Recommended actions per alert
## Sample 6: Action Execution (Action Agent)

### Input
```
Order a replacement bearing for the Caster segment roller, we need 2 of them.
```

### Expected Output
```
✅ **PO GENERATED:** Successfully generated pending purchase order for 2x bearing (Equipment: CCM-001). Reference ID: ACT-0007.

*Reasoning:* User requested to order a replacement part specifying the part name (bearing) and quantity (2).
```
> The action is also logged to the `action_logs` table and broadcast live over WebSocket, appearing in the dashboard's action log.

---

## Sample 7: Vision AI Diagnostics

### Input
```
[User uploads an image of a cracked pipe]
What is causing this damage?
```

### Expected Output
```
## 🔍 Visual Fault Diagnosis

Based on the image provided and the current sensor data for the hydraulic system:

**Most Probable Causes:**
1. **Fatigue Failure** (High Confidence) — The image shows a classic transverse fatigue crack. This aligns with the recent high-frequency pressure pulsations (sensor reading: 120 bar oscillating ±15 bar).
2. **Overpressure Event** (Medium Confidence) — A sudden pressure spike could have initiated the crack, which then propagated.

## ⚠️ Recommendation
- Immediately depressurize the affected hydraulic line.
- Replace the cracked pipe section.
- Inspect the accumulator nitrogen pre-charge to ensure it is dampening pressure pulsations effectively.
```
