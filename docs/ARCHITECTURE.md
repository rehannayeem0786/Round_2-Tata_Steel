# System Architecture — Intelligent Maintenance Wizard

## Overview
The Intelligent Maintenance Wizard is an agentic AI-powered decision support system for industrial equipment maintenance in Tata Steel's steel manufacturing plants. It leverages **8 specialized AI agents**, a RAG-based knowledge system, **OEE analytics**, **cost impact analysis**, an **Interactive Digital Twin**, **Multi-Modal Vision AI**, and real-time sensor monitoring to provide explainable, actionable maintenance recommendations with measurable business impact (₹).

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    FRONTEND (Web Dashboard)                      │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────────────┐  │
│  │ Chat UI  │ │Dashboard │ │ Alerts   │ │ OEE & Analytics   │  │
│  │(Voice,   │ │(Digital  │ │(Real-    │ │ (Charts, OEE,     │  │
│  │ Vision)  │ │ Twin)    │ │ time)    │ │  Cost, Timeline)  │  │
│  └──────────┘ └──────────┘ └──────────┘ └───────────────────┘  │
│  ┌──────────┐ ┌──────────┐                                      │
│  │Knowledge │ │ Logbook  │  [Chart.js Visualizations]           │
│  │ (Upload/ │ │ (Auto    │  [PDF Report Export]                 │
│  │  Browse) │ │  Records)│                                      │
│  └──────────┘ └──────────┘                                      │
└────────────────────────┬────────────────────────────────────────┘
                         │ REST API + WebSocket
┌────────────────────────▼────────────────────────────────────────┐
│                  BACKEND (FastAPI + Python)                      │
│                                                                  │
│  ┌────────────────── Agent Orchestrator ──────────────────────┐ │
│  │           (LLM Intent Classification + Routing)            │ │
│  │                                                            │ │
│  │  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐ │ │
│  │  │ Diagnostic  │  │    Risk       │  │ Recommendation   │ │ │
│  │  │   Agent     │  │  Assessment   │  │    Agent         │ │ │
│  │  │• Fault ID   │  │• Risk Level   │  │• Action Plans    │ │ │
│  │  │• Vision AI  │  │• Urgency      │  │• Spare Parts     │ │ │
│  │  │• RUL Pred.  │  │• Priority     │  │• Schedules       │ │ │
│  │  └─────────────┘  └──────────────┘  └──────────────────┘ │ │
│  │                                                            │ │
│  │  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐ │ │
│  │  │ Reporting   │  │  Alerting    │  │  Cost Impact     │ │ │
│  │  │   Agent     │  │   Agent      │  │    Agent (₹)     │ │ │
│  │  │• Reports    │  │• Anomaly Det.│  │• Downtime Cost   │ │ │
│  │  │• Summaries  │  │• Notifications│ │• ROI Analysis    │ │ │
│  │  └─────────────┘  └──────────────┘  │• Business Impact │ │ │
│  │                                     └──────────────────┘ │ │
│  │  ┌─────────────┐  ┌──────────────┐                       │ │
│  │  │ Feedback    │  │ Action Agent │ [State passes between │ │
│  │  │   Agent     │  │ • API Execute│  agents]              │ │
│  │  └─────────────┘  └──────────────┘                       │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌─────────────── Analytics Layer ───────────────────────────┐ │
│  │  OEE Metrics  │  Cost Summary  │  Predictive Timeline     │ │
│  │  Sensor Trends │  PDF Export   │  Business Intelligence    │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌─────────────── Knowledge Layer (RAG) ─────────────────────┐ │
│  │  ChromaDB Vector Store  │  Document Processor (TXT)       │ │
│  │  Equipment Manuals      │  SOPs & Maintenance Records     │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌─────────────── Data Layer ────────────────────────────────┐ │
│  │  SQLite (Equipment, Logs, Feedback)  │  Sensor Simulator  │ │
│  └────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

## Technology Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Frontend | HTML/CSS/JS + Chart.js | No build step, premium dark-theme UI with interactive charts |
| Backend | Python + FastAPI | Async-capable, auto-docs, modern Python API framework |
| Agent Orchestration | LangChain + Custom Router | LLM-based intent classification + agent routing |
| LLM | NVIDIA NIM / Groq / OpenRouter / Google Gemini | Multi-provider (priority order) with automatic fallback |
| ML / Anomaly Detection | scikit-learn (Isolation Forest) + NumPy/SciPy | Unsupervised anomaly detection + robust statistics |
| Vector DB | ChromaDB | Lightweight, local, persistent |
| Database | SQLite | Zero-config, file-based, no setup |
| Real-time | WebSocket (FastAPI native) | Live sensor data and alert streaming |
| Charts | Chart.js | Interactive OEE gauges, cost charts, sensor trends |
| Embeddings | all-MiniLM-L6-v2 (ONNX) | Fast local document embeddings for RAG retrieval |

## Data Flow

1. **User Query** → FastAPI receives the request
2. **Intent Classification** → LLM-based classification with 8 intent categories (diagnostic, risk, recommendation, report, alert, cost, action, general)
3. **Equipment Detection** → Identifies which equipment the query relates to
4. **RAG Retrieval** → Searches ChromaDB for relevant knowledge documents
5. **Database Context** → Fetches equipment data, sensor readings, alerts, maintenance history
6. **Agent Routing** → Dispatches to the appropriate agent(s) with full context
7. **State Passing** → Agents pass outputs to subsequent agents (e.g., Diagnostic → Risk → Recommendation)
8. **LLM Reasoning** → Agent uses LLM to analyze context and generate response
9. **Response Assembly** → Combines agent outputs with source attribution
10. **Conversation Storage** → Stores in SQLite for multi-turn context

## Model Design and Reasoning Pipeline

### Agent Orchestrator
- Uses LLM-based intent classification with 8 intent categories
- Each category has keyword-based fallback patterns for robust classification
- Falls back to "diagnostic" intent (most common use case)
- Supports multi-turn conversations with stored history
- **State passing**: Agents receive outputs from previous agents as additional context

### Individual Agents
Each agent has:
- A specialized system prompt defining its expertise and output format
- Access to RAG-retrieved context (knowledge base + database)
- Conversation history for multi-turn reasoning
- Fallback mode when LLM is unavailable

### Cost Impact Agent (NEW)
- Tata Steel-specific financial benchmarks (₹52,000/tonne HRC, ₹15-25 lakh/hr downtime)
- Equipment cost profiles with production rate, downtime cost, and ROI ratios
- Preventive vs reactive maintenance cost comparison
- Cascading production impact analysis
- Business impact scoring with investment recommendations

### Analytics Layer (NEW)
- **OEE Metrics**: Availability × Performance × Quality per equipment and plant-wide
- **Cost Summary**: Annual downtime risk, maintenance costs, preventive ROI
- **Predictive Timeline**: RUL-based urgency ranking (IMMEDIATE/URGENT/PLANNED/MONITOR)
- **Sensor Trends**: Chart.js line charts with threshold overlays and anomaly markers
- **PDF Export**: Print-ready analytics report with Tata Steel branding

### RAG Pipeline
1. Documents chunked at ~512 characters with 50-char overlap
2. Chunks indexed in ChromaDB with metadata (source, category)
3. Query triggers semantic search across all collections
4. Top-K results filtered by relevance threshold
5. Results combined with database context for comprehensive grounding

## Alerting and Prediction Logic

### Sensor Simulator
- Generates readings every 5 seconds for all equipment
- Applies degradation patterns to warning/critical equipment
- Injects random anomaly spikes with configurable probability
- Pushes data via WebSocket to connected clients

### Anomaly Detection (ML-based ensemble)
Implemented in `ml/anomaly_detector.py` with two complementary detectors:
- **Online detector** (every live reading): robust modified z-score (median + MAD) + EWMA control-chart deviation → 0–1 anomaly score driving early-warning flags.
- **Batch ML detector** (on demand): **Isolation Forest** (scikit-learn, unsupervised) over engineered features `[value, first-difference, rolling deviation]`, combined with a physics-anchored severity band and robust z-score.
- **Ensemble score:** `0.7·band + 0.2·robust_z + 0.1·IF_rate` → Healthy / Degrading / Anomalous.
- Threshold crossings (normal/warn/critical) still raise classified alerts; the ML layer adds calibrated, multivariate, trend-aware detection on top.
- Graceful fallback to pure-Python robust statistics if NumPy/scikit-learn are unavailable.

### RUL Prediction
- `predict_rul_regression()` fits a **linear regression** (`y = mx + c`) over the last 30 readings per metric.
- Projects time-to-critical-threshold from the degradation slope and direction; returns hours-to-failure (or "Stable" when not degrading).
- LLM reasoning augmented with equipment manual failure-mode data; feeds the predictive maintenance timeline.

## OEE Calculation Methodology

### Availability
- (Planned Production Time - Downtime) / Planned Production Time × 100
- Downtime includes: maintenance hours + status-based unplanned downtime
- Critical equipment: 24hr unplanned, Warning: 8hr, Operational: 2hr

### Performance
- 95% base - anomaly rate penalty (up to 15%)
- Based on ratio of actual production speed to ideal speed
- Minimum floor: 70%

### Quality
- 98% base - alert severity penalty (Critical: 5%, High: 2%)
- Based on ratio of good product to total product
- Minimum floor: 80%

### OEE Rating
- World-Class: ≥85%
- Good: ≥65%
- Average: ≥50%
- Below Average: <50%

## Cost Impact Methodology

### Tata Steel Benchmarks
- Steel price: ₹52,000/tonne (HRC)
- Blast Furnace: 5,000 tonnes/day → ₹1.08 crore/hr downtime
- Caster: 250 tonnes/hr per strand → ₹13 lakh/hr
- Emergency repair premium: 2.5× planned maintenance cost
- Preventive maintenance ROI: 3:1 to 10:1

### Annual Risk Calculation
- Critical equipment: downtime_cost × 48 hours risk
- Warning equipment: downtime_cost × 24 hours risk
- Operational: downtime_cost × 8 hours minor risk

## Assumptions and Limitations

### Assumptions
- Steel plant equipment operates 24/7 with scheduled maintenance windows
- Sensor data follows known patterns for each equipment type
- Knowledge base documents are accurate and up-to-date
- Internet connectivity available for LLM API calls
- Tata Steel Jamshedpur production benchmarks are representative

### Limitations
- Simulated sensor data (not connected to real IoT devices)
- Multi-provider LLM with priority order + automatic fallback model on rate-limit/error
- Text-only knowledge base ingestion (no PDF/OCR yet; chat-side vision is supported)
- No user authentication (suitable for demo/prototype)
- ML anomaly detection is unsupervised (Isolation Forest + robust statistics + physics bands); not yet trained on long-horizon labelled failure data
- OEE calculations use estimated downtime, not actual production logs
- Action execution is simulated (SCADA/ERP commands are logged, not dispatched to live systems)
