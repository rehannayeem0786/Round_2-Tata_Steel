# 🏭 Intelligent Maintenance Wizard

**Agentic AI Decision Support System for Tata Steel Plant Maintenance**

An end-to-end multi-agent AI system that provides real-time equipment diagnostics, risk assessment, OEE analytics, cost impact analysis, maintenance recommendations, and predictive insights for industrial steel manufacturing plants. Built with a modular 8-agent architecture, RAG-powered knowledge retrieval, and a premium real-time dashboard with Chart.js visualizations.

> **Built for Tata Steel Hackathon 2026** — Demonstrating measurable business impact through AI-driven predictive maintenance, with ₹ crore-level downtime cost quantification and OEE optimization targeting world-class 85%+ benchmarks.

---

## 📸 Dashboard Preview

| Plant Dashboard | AI Chat Interface |
|:---:|:---:|
| Real-time equipment monitoring with live sensor data | Multi-agent conversational AI with structured outputs |

| Alert Center | OEE & Analytics |
|:---:|:---:|
| Severity-filtered alerts with acknowledge/resolve actions | OEE gauges, cost impact charts, predictive timeline |

| Knowledge Base | Digital Logbook |
|:---:|:---:|
| Semantic search across equipment manuals & SOPs | Automated maintenance records and reports |

---

## 💰 Business Impact for Tata Steel

| Metric | Current State | With AI System | Impact |
|--------|--------------|----------------|--------|
| **Plant OEE** | ~60% | Target 85%+ | +25% productivity gain |
| **Unplanned Downtime** | ₹15-25 lakh/hr | Reduced by 60% | ₹9-15 crore annual savings |
| **Preventive Ratio** | ~50% | Target 80% | 3:1 to 10:1 ROI |
| **Mean Time to Repair** | 6-8 hrs | Reduced by 40% | Faster recovery |
| **Safety Incidents** | Baseline | Reduced by 50% | Zero-harm goal |

---

## ✨ Key Features

### ✨ Hackathon Top-3 Advanced Features (New)
- **🦾 Autonomous Action Execution** — Beyond Chat: The AI parses action intents and simulates SCADA commands or ERP replacement orders (Action Agent).
- **🏭 Interactive Digital Twin Dashboard** — Real-time CSS-grid layout of the plant equipment pulsing red when anomalies are detected via WebSocket.
- **🎤 Hands-Free Voice Mode** — Uses Web Speech API (Speech-to-Text & Text-to-Speech) allowing field engineers to talk to the AI hands-free.
- **👁️ Multi-Modal Vision AI** — Image upload capabilities allowing the AI to "see" physical defects, leaks, and damage alongside sensor data.

### 🤖 Multi-Agent AI System (8 Specialized Agents)
- **Action Agent** — Executes operations and triggers external systems.
- **Diagnostic Agent** — Fault identification, root cause analysis (5-Why), remaining useful life (RUL) prediction.
- **Risk Assessment Agent** — Risk classification (Low/Medium/High/Critical), urgency scoring, bottleneck prioritization.
- **Recommendation Agent** — Step-by-step maintenance procedures, spare parts lists, optimized scheduling.
- **Cost Impact Agent** — Downtime cost quantification (₹), ROI analysis, preventive vs reactive comparison.
- **Reporting Agent** — Structured plant-wide maintenance reports with data aggregation.
- **Alerting Agent** — Real-time anomaly analysis, severity assessment, contextualized alert interpretation.
- **Feedback Agent** — Continuous improvement through user corrections and accuracy tracking.

### 📊 OEE & Business Intelligence Analytics
- **ML Anomaly Detection** — Unsupervised Isolation Forest + robust modified z-score (MAD) + EWMA control charts + physics-anchored severity bands, scoring every equipment-metric in real time with explainable, traceable output fed into agent reasoning.
- **Overall Equipment Effectiveness** — Availability × Performance × Quality metrics per equipment.
- **Plant-wide OEE Dashboard** — Doughnut gauges, bar charts, equipment comparison.
- **Cost Impact Analysis** — ₹-quantified downtime risk, annual maintenance costs, preventive ROI.
- **Predictive Maintenance Timeline** — RUL-based urgency ranking (IMMEDIATE/URGENT/PLANNED/MONITOR).
- **Sensor Trend Visualization** — Chart.js line charts with threshold overlays and anomaly markers.
- **PDF Report Export** — Print-ready analytics reports with Tata Steel branding.

### 📚 RAG-Powered Knowledge Retrieval
- ChromaDB vector store with semantic search.
- Pre-loaded with 12 industrial documents (equipment manuals, SOPs, maintenance records, failure reports).
- Multi-source context assembly (knowledge base + database + sensor data).
- Document upload for expanding the knowledge base.

### 📊 Real-Time Monitoring & Digital Twin
- WebSocket-based live sensor data streaming.
- Automatic anomaly detection with configurable thresholds.
- Interactive Plant Layout (Digital Twin) visualizing equipment state.
- RUL (Remaining Useful Life) prediction per metric.
- Alert generation with severity classification.

### 💬 Conversational AI Interface
- Natural language query processing with LLM-based intent classification.
- Multi-turn conversation support with context memory.
- Multi-Modal Image support for visual diagnostics.
- Thumbs up/down feedback on every response.
- Role-based context (Field Engineer / Shift Supervisor / Plant Manager).

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    FRONTEND (Web Dashboard)                      │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────────────┐  │
│  │ Chat UI  │ │Dashboard │ │ Alerts   │ │ OEE & Analytics   │  │
│  └──────────┘ └──────────┘ └──────────┘ └───────────────────┘  │
│  ┌──────────┐ ┌──────────┐                                      │
│  │Knowledge │ │ Logbook  │  [Chart.js Visualizations]           │
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
│  │  └─────────────┘  └──────────────┘  └──────────────────┘ │ │
│  │  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐ │ │
│  │  │ Reporting   │  │  Alerting    │  │  Cost Impact     │ │ │
│  │  │   Agent     │  │   Agent      │  │    Agent (₹)     │ │ │
│  │  └─────────────┘  └──────────────┘  └──────────────────┘ │ │
│  │  ┌─────────────┐                                            │ │
│  │  │ Feedback    │  [State passes between agents]             │ │
│  │  │   Agent     │                                            │ │
│  │  └─────────────┘                                            │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌─────────────── Analytics Layer ───────────────────────────┐ │
│  │  OEE Metrics  │  Cost Summary  │  Predictive Timeline     │ │
│  │  Sensor Trends │  PDF Export   │  Business Intelligence    │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌─────────────── Knowledge Layer (RAG) ─────────────────────┐ │
│  │  ChromaDB Vector Store  │  Document Processor             │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌─────────────── Data Layer ────────────────────────────────┐ │
│  │  SQLite Database  │  Sensor Simulator  │  Seed Data       │ │
│  └────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | HTML, CSS, JavaScript + Chart.js | Premium dark-theme SPA with interactive charts |
| **Backend** | Python 3.11 + FastAPI | Async API server with auto-generated docs |
| **AI/LLM** | NVIDIA / Groq / OpenRouter / Google Gemini | Multi-provider LLM reasoning for all 8 agents |
| **Agent Framework** | LangChain + Custom Orchestrator | LLM intent classification + agent routing |
| **Vector Database** | ChromaDB | Local, persistent embedding search |
| **Database** | SQLite + aiosqlite | Equipment, sensors, alerts, conversations |
| **Real-time** | WebSocket (FastAPI native) | Live sensor data + alert streaming |
| **ML / Anomaly Detection** | scikit-learn (Isolation Forest) + robust statistics | Unsupervised anomaly detection & predictive analytics |
| **Embeddings** | all-MiniLM-L6-v2 (ONNX) | Document embeddings for RAG retrieval |

---

## 🚀 Quick Start

### Prerequisites
- **Python 3.9+** installed
- **An LLM API key** — NVIDIA (recommended), Groq, OpenRouter, or Google Gemini *(optional; the system runs in fallback mode without one)*

### 1. Clone & Install

```bash
cd "Round demo 1"
pip install -r backend/requirements.txt
```

### 2. Configure Environment

```bash
cd backend
copy .env.example .env
# Edit .env and add one of the supported API keys, e.g.:
# NVIDIA_API_KEY=your_key_here
```

### 3. Start the Server

```bash
cd backend
python main.py
```

### 4. Open the Dashboard

Navigate to **http://localhost:8000** in your browser.

> **First run** will automatically:
> - Create and seed the SQLite database with 10 equipment units
> - Download the embedding model (~79MB, one-time)
> - Index 12 knowledge documents into ChromaDB
> - Start the real-time sensor simulator

---

## 💬 Sample Queries

Try these in the AI Chat interface:

| Category | Example Query |
|----------|--------------|
| **Diagnostics** | *"The blast furnace is showing unusual vibration. What could be wrong?"* |
| **Risk Assessment** | *"What is the risk level for the continuous caster bearing?"* |
| **Maintenance** | *"How do I replace a bearing on the caster segment roller?"* |
| **Cost Impact** | *"What is the cost impact of the caster bearing failure? Calculate downtime cost and ROI"* |
| **Reports** | *"Generate a maintenance status report for the plant"* |
| **Alerts** | *"What are the current active alerts and their severity?"* |
| **General** | *"Show me all equipment"* or *"What can you help me with?"* |

---

## 🚀 Quick Start / How to Run

### 1. Backend (API & AI Agents)
The backend is built with FastAPI and runs the AI agents and sensor simulator.

```bash
# 1. Open a terminal and navigate to the project directory
cd "Round demo 1"

# 2. Activate the virtual environment
.\.venv\Scripts\activate

# 3. Start the FastAPI server
python backend\main.py
```
*The server will start on `http://localhost:8000` and serves the dashboard directly.*

### 2. Frontend (Dashboard)
The frontend is a vanilla JS application served automatically by the backend at `http://localhost:8000`. No separate web server is required — just open that URL in your browser.

> If you prefer to serve the static files independently (optional), from the `frontend` directory you can run `python -m http.server 3000`, but the bundled backend server is the recommended way to run the app.

---

## 📁 Project Structure

```
Round demo 1/
├── README.md                          # This file
├── docs/
│   ├── SOLUTION_DOCUMENT.md            # ⭐ Master submission document (architecture, flow, traceability, sample I/O)
│   ├── PRESENTATION.md                 # Pitch deck outline + demo script (for the screen recording)
│   ├── ARCHITECTURE.md                # Detailed system architecture
│   ├── SETUP.md                       # Installation guide
│   └── SAMPLE_IO.md                   # Sample input/output demonstrations
│
├── backend/
│   ├── main.py                        # FastAPI entry point
│   ├── config.py                      # Configuration & environment variables
│   ├── requirements.txt               # Python dependencies
│   ├── .env.example                   # Environment template
│   │
│   ├── agents/                        # Multi-agent system
│   │   ├── orchestrator.py            # Intent classification + agent routing
│   │   ├── llm_provider.py            # Multi-provider LLM client + retry/fallback
│   │   ├── diagnostic_agent.py        # Fault diagnosis & RCA
│   │   ├── risk_agent.py              # Risk classification & urgency
│   │   ├── recommendation_agent.py    # Maintenance action plans
│   │   ├── cost_agent.py              # Downtime cost & ROI analysis (₹)
│   │   ├── action_agent.py            # SCADA/ERP action execution
│   │   ├── reporting_agent.py         # Structured report generation
│   │   ├── alerting_agent.py          # Anomaly & alert analysis
│   │   ├── logbook_agent.py           # Auto-generated logbook entries
│   │   └── feedback_agent.py          # User feedback & accuracy tracking
│   │
│   ├── data/                          # Data layer
│   │   ├── database.py                # SQLite schema & operations
│   │   ├── seed_data.py               # Sample steel plant data
│   │   └── sensor_simulator.py        # Real-time sensor generator
│   │
│   ├── knowledge/                     # RAG knowledge layer
│   │   ├── vector_store.py            # ChromaDB wrapper
│   │   ├── document_processor.py      # Document chunking & indexing
│   │   └── rag_engine.py              # Multi-source context retrieval
│   │
│   ├── ml/                            # Machine learning layer
│   │   └── anomaly_detector.py        # Isolation Forest + robust-Z/EWMA anomaly engine
│   │
│   ├── api/                           # REST API routes
│   │   ├── chat_routes.py             # Chat, feedback & conversation endpoints
│   │   ├── dashboard_routes.py        # Equipment, stats & action endpoints
│   │   ├── alert_routes.py            # Alert management endpoints
│   │   ├── analytics_routes.py        # OEE, cost & predictive analytics
│   │   ├── knowledge_routes.py        # Knowledge search & upload
│   │   ├── scenario_routes.py         # Demo scenario triggers
│   │   └── websocket_handler.py       # Real-time WebSocket handler
│   │
│   └── sample_knowledge/              # Pre-loaded knowledge documents
│       ├── equipment_manuals/         # 3 equipment manuals
│       ├── sops/                      # 3 SOPs
│       ├── maintenance_records/       # Historical records
│       └── failure_reports/           # Failure analysis reports
│
└── frontend/
    ├── index.html                     # Main SPA shell
    ├── css/
    │   └── styles.css                 # Premium dark-theme design system
    └── js/
        ├── app.js                     # View routing & initialization
        ├── chat.js                    # AI chat interface
        ├── dashboard.js               # Equipment monitoring & digital twin
        ├── alerts.js                  # Alert management
        ├── analytics.js               # OEE & analytics charts
        ├── knowledge.js               # Knowledge base search
        ├── logbook.js                 # Digital logbook timeline
        ├── websocket.js               # Real-time WebSocket client
        ├── particles.js               # Ambient particle background
        └── utils.js                   # Shared utilities
```

---

## ⚙️ Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `NVIDIA_API_KEY` | *(recommended)* | NVIDIA API key for fast LLM reasoning |
| `GROQ_API_KEY` | *(optional)* | Groq Cloud API key |
| `OPENROUTER_API_KEY` | *(optional)* | OpenRouter API key |
| `GOOGLE_API_KEY` | *(optional)* | Google Gemini API key |
| `LLM_MODEL` | `meta/llama-3.1-70b-instruct` | LLM model to use |
| `LLM_TEMPERATURE` | `0.3` | LLM response temperature |
| `PORT` | `8000` | Server port |
| `SENSOR_INTERVAL` | `5` | Sensor reading interval (seconds) |
| `ANOMALY_PROBABILITY` | `0.05` | Probability of anomaly per reading |
| `RAG_TOP_K` | `5` | Number of RAG results per query |
| `RAG_SCORE_THRESHOLD` | `0.3` | Minimum relevance score for RAG results |

> At least one API key must be set for full AI capabilities. Provider priority is NVIDIA → Groq → OpenRouter → Google. If none is set, the system runs in fallback mode.

---

## 🔧 API Reference

Interactive API documentation is auto-generated at **http://localhost:8000/docs** (Swagger UI).

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/chat` | Send a message to the AI agents |
| `POST` | `/api/chat/feedback` | Submit feedback on a response |
| `GET` | `/api/chat/conversations` | List past conversations |
| `GET` | `/api/chat/conversations/{id}` | Get a conversation's full history |
| `GET` | `/api/dashboard/stats` | Get plant-wide statistics |
| `GET` | `/api/dashboard/equipment` | List all equipment (with health scores) |
| `GET` | `/api/dashboard/equipment/{id}` | Get equipment details + sensors |
| `GET` | `/api/dashboard/maintenance` | List maintenance logbook entries |
| `GET` | `/api/alerts` | List alerts (optionally filtered) |
| `GET` | `/api/alerts/active` | Get all active (unresolved) alerts |
| `POST` | `/api/alerts/{id}` | Acknowledge or resolve an alert |
| `GET` | `/api/analytics/oee` | OEE metrics for all equipment |
| `GET` | `/api/analytics/cost-summary` | Plant-wide cost impact summary |
| `GET` | `/api/analytics/predictive-timeline` | RUL-based maintenance timeline |
| `GET` | `/api/analytics/anomaly-detection` | ML anomaly detection (Isolation Forest) for all equipment |
| `GET` | `/api/analytics/anomaly-detection/{id}` | ML anomaly detection with per-metric scores |
| `GET` | `/api/knowledge/search?q=...` | Search the knowledge base |
| `POST` | `/api/knowledge/upload` | Upload a document |
| `GET` | `/api/scenarios/list` | List demo scenarios |
| `POST` | `/api/scenarios/trigger` | Trigger a demo failure scenario |
| `POST` | `/api/scenarios/reset` | Reset all equipment to operational |
| `GET` | `/api/health` | Health check |
| `WS` | `/ws` | WebSocket for real-time sensor data |

---

## 🧠 How It Works

### Agent Orchestration Flow

1. **User sends a query** via the chat interface
2. **Intent Classification** — an LLM classifies the query into one of 8 categories: diagnostic, risk, recommendation, report, alert, cost, action, or general (with a keyword-based fallback when the LLM is unavailable)
3. **Equipment Detection** — Auto-identifies which equipment the query relates to
4. **RAG Context Assembly** — Retrieves relevant docs from ChromaDB + live data from SQLite
5. **Agent Routing** — Dispatches to the appropriate specialized agent(s) with full context
6. **LLM Reasoning** — Agent uses the configured LLM provider (NVIDIA/Groq/OpenRouter/Google) to analyze context and generate a structured response
7. **Response Delivery** — Formatted markdown with source attribution, agent tags, and an execution trace
8. **Feedback Loop** — User ratings stored for continuous improvement

### Fallback Mode

When no LLM API key is configured, the system operates in **fallback mode**:
- All RAG retrieval and data aggregation still works
- Agents return pre-formatted context summaries instead of LLM-generated analysis
- The dashboard, alerts, and knowledge base are fully functional
- Sensor simulator and real-time WebSocket streaming continue normally

---

## 🛡️ Assumptions & Limitations

### Assumptions
- Steel plant equipment operates 24/7 with scheduled maintenance windows
- Sensor data follows known patterns per equipment type
- Knowledge base documents are accurate and current

### Current Limitations
- **Simulated sensors** — Not connected to real IoT devices
- **Text-only knowledge** — No PDF or image parsing for the knowledge base
- **No authentication** — Suitable for demo/prototype deployment
- **ML anomaly detection** — Uses Isolation Forest + robust modified z-score + EWMA + physics-anchored severity bands. Not yet trained on long-horizon labelled failure data (unsupervised on streaming sensor data)

---

## 📄 License

This project is for educational and demonstration purposes.

---

<p align="center">
  <strong>Built with ❤️ using FastAPI, LangChain, ChromaDB, and multi-provider LLMs (NVIDIA / Groq / OpenRouter / Google Gemini)</strong>
</p>
