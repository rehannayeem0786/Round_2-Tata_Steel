"""
Main application entry point — FastAPI server for the
Intelligent Maintenance Wizard.
"""

import asyncio
import sys
import os

# Fix Windows console encoding for Unicode
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Add backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager

from config import HOST, PORT, DEBUG, FRONTEND_DIR, API_KEY, API_PROVIDER, LLM_MODEL
from data.database import init_database
from data.seed_data import seed_database
from knowledge.document_processor import load_knowledge_base
from data.sensor_simulator import run_sensor_simulator
from api.chat_routes import router as chat_router
from api.dashboard_routes import router as dashboard_router
from api.knowledge_routes import router as knowledge_router
from api.alert_routes import router as alert_router
from api.analytics_routes import router as analytics_router
from api.scenario_routes import router as scenario_router
from api.websocket_handler import websocket_endpoint


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    import config
    config.LOOP = asyncio.get_running_loop()
    
    print("=" * 60)
    print("[FACTORY] INTELLIGENT MAINTENANCE WIZARD")
    print("   Agentic AI for Steel Plant Maintenance")
    print("=" * 60)
    
    # Initialize database
    print("\n[INIT] Initializing database...")
    init_database()
    
    # Seed with sample data
    print("[SEED] Seeding sample data...")
    seed_database()
    
    # Load knowledge base into vector store
    print("\n[KB] Loading knowledge base...")
    try:
        load_knowledge_base()
    except Exception as e:
        print(f"[WARN] Knowledge base loading error (non-fatal): {e}")
        print("   The system will work but without RAG knowledge retrieval.")
    
    # Check API key
    if API_KEY:
        print(f"\n[OK] AI enabled via {API_PROVIDER} ({LLM_MODEL})")
    else:
        print(f"\n[WARN] No API key set -- AI agents will use fallback mode")
        print(f"   Set OPENROUTER_API_KEY in .env for full AI capabilities")
    
    # Start sensor simulator in background
    print(f"\n[SIM] Starting sensor simulator...")
    sensor_task = asyncio.create_task(run_sensor_simulator())
    
    print(f"\n[READY] Server ready at http://localhost:{PORT}")
    print(f"   Dashboard: http://localhost:{PORT}")
    print(f"   API Docs:  http://localhost:{PORT}/docs")
    print("=" * 60)
    
    yield
    
    # Shutdown
    sensor_task.cancel()
    print("\n[STOP] Shutting down Maintenance Wizard...")


# ─── Create FastAPI App ──────────────────────────────────────────────────────

app = FastAPI(
    title="Intelligent Maintenance Wizard",
    description="Agentic AI Decision Support System for Steel Plant Maintenance",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers
app.include_router(chat_router)
app.include_router(dashboard_router)
app.include_router(knowledge_router)
app.include_router(alert_router)
app.include_router(analytics_router)
app.include_router(scenario_router)

# WebSocket endpoint
app.websocket("/ws")(websocket_endpoint)


# ─── Health Check ────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health_check():
    """API health check endpoint."""
    return {
        "status": "healthy",
        "service": "Intelligent Maintenance Wizard",
        "version": "1.0.0",
        "ai_enabled": bool(API_KEY),
        "ai_provider": API_PROVIDER,
        "ai_model": LLM_MODEL if API_KEY else None,
    }


# ─── Serve Frontend ─────────────────────────────────────────────────────────

# Mount static files (CSS, JS, assets)
if FRONTEND_DIR.exists():
    app.mount("/css", StaticFiles(directory=str(FRONTEND_DIR / "css")), name="css")
    app.mount("/js", StaticFiles(directory=str(FRONTEND_DIR / "js")), name="js")
    
    @app.get("/")
    async def serve_frontend():
        """Serve the main frontend page."""
        return FileResponse(str(FRONTEND_DIR / "index.html"))
else:
    @app.get("/")
    async def no_frontend():
        return {"message": "Frontend not found. API available at /docs"}


# ─── Run Server ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=HOST,
        port=PORT,
        reload=DEBUG,
        log_level="info",
    )
