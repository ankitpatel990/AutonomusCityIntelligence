"""
Autonomous City Traffic Intelligence System
Main FastAPI Application Entry Point

This is the main entry point for the backend server.
It initializes FastAPI, Socket.IO, database, and all core components.
"""

import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import socketio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Create Socket.IO server
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins='*',
    logger=False,  # Reduce noise in production
    engineio_logger=False,
    ping_interval=25,
    ping_timeout=60
)

# Global instances for WebSocket
ws_emitter = None
ws_handlers = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events - startup and shutdown"""
    global ws_emitter, ws_handlers
    
    # Startup
    print("=" * 60)
    print("[STARTUP] Autonomous City Traffic Intelligence System")
    print("=" * 60)
    
    # Initialize database
    from app.database.database import init_db
    init_db()
    print("[OK] Database initialized")
    
    # Initialize configuration
    from app.config import config, get_config
    print("[OK] Configuration loaded")
    
    # Initialize WebSocket emitter and handlers
    from app.websocket import WebSocketEmitter, WebSocketHandlers, set_emitter, set_handlers
    
    ws_emitter = WebSocketEmitter(sio)
    ws_handlers = WebSocketHandlers(sio, ws_emitter)
    
    # Set global instances
    set_emitter(ws_emitter)
    set_handlers(ws_handlers)
    
    print("[OK] WebSocket emitter and handlers initialized")
    
    # Initialize Density Tracker (FRD-02)
    from app.density import init_density_tracker, get_density_tracker
    cfg = get_config()
    density_tracker = init_density_tracker(cfg.get_traffic_config() if cfg else {})
    print("[OK] Density tracker initialized")
    
    # Initialize Autonomous Agent (FRD-03)
    from app.agent import (
        init_agent, 
        PerceptionModule, 
        DecisionModule, 
        ActionModule, 
        MonitoringModule
    )
    
    # Create agent with configuration
    agent_config = cfg.get_system_config() if cfg else {}
    agent_config['loopInterval'] = 1.0  # 1 second cycle
    
    agent = init_agent(
        config=agent_config,
        simulation_manager=None,  # Will be set when simulation starts
        density_tracker=density_tracker
    )
    
    # Create and inject agent modules
    perception = PerceptionModule(density_tracker=density_tracker)
    decision = DecisionModule()
    action = ActionModule()
    monitor = MonitoringModule()
    
    # Initialize RL Inference Service (FRD-04)
    from app.rl import get_inference_service, init_inference_service
    import os
    
    # Try to load default RL model if available
    default_model_path = './models/ppo_traffic_final.zip'
    if os.path.exists(default_model_path):
        rl_service = init_inference_service(default_model_path)
        if rl_service.is_ready():
            decision.inject_rl_agent(rl_service.model)
            
            # Also set RL model in prediction's RL predictor
            if rl_predictor:
                rl_predictor.set_model(rl_service.model)
            
            print("[OK] RL agent loaded and injected into decision module")
    else:
        print("[INFO] No RL model found. Using rule-based decisions.")
        print("       Train a model: python train_rl.py train --quick")
    
    # Initialize Prediction Engine (FRD-06)
    from app.prediction import (
        init_prediction_engine,
        init_congestion_classifier,
        init_prediction_validator,
        init_rl_predictor,
        init_nn_predictor,
        init_broadcast_service,
        get_prediction_engine,
        get_broadcast_service
    )
    
    # Load prediction config
    prediction_config = cfg.get('prediction', {}) if cfg else {}
    
    # Initialize prediction components
    prediction_engine = init_prediction_engine(prediction_config)
    congestion_classifier = init_congestion_classifier(prediction_config)
    prediction_validator = init_prediction_validator()
    rl_predictor = init_rl_predictor()  # Model set later if RL is loaded
    nn_predictor = init_nn_predictor()  # Optional neural network
    
    # Initialize broadcast service (will start after WebSocket is ready)
    broadcast_service = init_broadcast_service(
        ws_emitter=ws_emitter,
        interval=prediction_config.get('updateFrequency', 30)
    )
    
    print("[OK] Prediction engine initialized (FRD-06)")
    
    agent.inject_modules(
        perception=perception,
        prediction=prediction_engine,  # FRD-06: Prediction engine
        decision=decision,
        action=action,
        monitor=monitor
    )
    
    # Set WebSocket emitter for real-time updates
    agent.set_ws_emitter(ws_emitter)
    action.set_ws_emitter(ws_emitter)
    monitor.set_ws_emitter(ws_emitter)
    
    print("[OK] Autonomous agent initialized (FRD-03)")
    
    # Initialize Safety Systems (FRD-05)
    from app.safety import (
        ConflictValidator,
        SystemModeManager,
        Watchdog,
        ManualOverrideManager,
        SafetyNotificationService,
        set_notification_service
    )
    
    # Create safety components
    conflict_validator = ConflictValidator()
    mode_manager = SystemModeManager()
    override_manager = ManualOverrideManager(
        simulation_manager=None,  # Will be set when simulation starts
        agent_loop=agent,
        mode_manager=mode_manager
    )
    watchdog = Watchdog(
        mode_manager=mode_manager,
        simulation_manager=None,  # Will be set when simulation starts
        agent_loop=agent,
        conflict_validator=conflict_validator
    )
    
    # Initialize notification service
    notification_service = SafetyNotificationService(sio)
    set_notification_service(notification_service)
    
    # Inject safety validator into action module
    action.set_safety_validator(conflict_validator)
    
    # Register safety API routes (will be included after app creation)
    from app.api.safety_routes import set_safety_components
    set_safety_components(mode_manager, watchdog, override_manager, conflict_validator)
    
    # Start watchdog
    await watchdog.start()
    
    print("[OK] Safety systems initialized (FRD-05)")
    
    # Start prediction broadcast service
    if broadcast_service:
        await broadcast_service.start()
        print("[OK] Prediction broadcast service started")
    
    print("=" * 60)
    print("[SERVER] Ready at http://localhost:8000")
    print("[DOCS] API docs at http://localhost:8000/docs")
    print("[WS] WebSocket ready for connections")
    print("[AGENT] Agent ready - use POST /api/agent/start to begin")
    print("=" * 60)
    
    yield
    
    # Shutdown
    print("[SHUTDOWN] Shutting down...")
    
    # Stop prediction broadcast service
    try:
        from app.prediction import get_broadcast_service
        broadcast_svc = get_broadcast_service()
        if broadcast_svc:
            await broadcast_svc.stop()
            print("[SHUTDOWN] Prediction broadcast service stopped")
    except Exception as e:
        print(f"[SHUTDOWN] Error stopping prediction broadcast: {e}")
    
    # Stop agent if running
    from app.agent import get_agent
    agent = get_agent()
    if agent and agent.status.value != "STOPPED":
        await agent.stop()
        print("[SHUTDOWN] Agent stopped")
    
    # Stop watchdog
    try:
        from app.safety import Watchdog
        # Watchdog will be stopped automatically when running flag is False
        print("[SHUTDOWN] Watchdog stopped")
    except Exception as e:
        print(f"[SHUTDOWN] Error stopping watchdog: {e}")
    
    print("[SHUTDOWN] Complete")


# Create FastAPI application
app = FastAPI(
    title="Traffic Intelligence System API",
    description="Autonomous City Traffic Intelligence System - AutonomousHacks 2026",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",  # Alternative dev server
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "*"  # Allow all for development
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================
# Include API Routers
# ============================================

from app.api import (
    system_router,
    agent_router,
    simulation_router,
    traffic_router,
    emergency_router,
    incident_router,
    challan_router,
    prediction_router,
    density_router,
    test_tomtom_router,
    rl_router,
)
# Safety routes imported in lifespan

# System routes: /api/state, /api/vehicles, /api/junctions, /api/roads, /api/density
app.include_router(system_router)

# Agent routes: /api/agent/start, /api/agent/stop, /api/agent/status, etc.
app.include_router(agent_router)

# Simulation routes: /api/simulation/start, /api/simulation/pause, etc.
app.include_router(simulation_router)

# Traffic control routes: /api/traffic/*, /api/map/*
app.include_router(traffic_router)

# Emergency routes: /api/emergency/trigger, /api/emergency/status
app.include_router(emergency_router)

# Incident routes: /api/incident/report, /api/incident/{id}/inference
app.include_router(incident_router)

# Challan routes: /api/violations, /api/challans, /api/owners, /api/revenue
app.include_router(challan_router)

# Prediction routes: /api/predictions
app.include_router(prediction_router)

# Density routes: /api/density/*
app.include_router(density_router)

# TomTom test routes: /api/test-tomtom/*
app.include_router(test_tomtom_router)

# RL routes: /api/rl/* (FRD-04)
app.include_router(rl_router)

# Safety routes: /api/safety/* (FRD-05)
from app.api.safety_routes import router as safety_router
app.include_router(safety_router)


# ============================================
# Root Endpoints
# ============================================

@app.get("/", tags=["root"])
async def root():
    """Root endpoint - API information"""
    return {
        "name": "Autonomous City Traffic Intelligence System",
        "version": "1.0.0",
        "status": "operational",
        "documentation": "/docs",
        "websocket": "ws://localhost:8000",
        "endpoints": {
            "system": "/api/state",
            "vehicles": "/api/vehicles",
            "junctions": "/api/junctions",
            "roads": "/api/roads",
            "density": "/api/density",
            "agent": "/api/agent/*",
            "simulation": "/api/simulation/*",
            "traffic_control": "/api/traffic/*",
            "map": "/api/map/*",
            "emergency": "/api/emergency/*",
            "incident": "/api/incident/*",
            "violations": "/api/violations",
            "challans": "/api/challans",
            "predictions": "/api/predictions",
            "rl": "/api/rl/*"
        }
    }


@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint"""
    from app.websocket import get_handlers
    
    handlers = get_handlers()
    ws_clients = handlers.get_client_count() if handlers else 0
    
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "uptime": time.time(),
        "websocket": {
            "connected_clients": ws_clients,
            "status": "ready"
        }
    }


@app.get("/ws/stats", tags=["websocket"])
async def websocket_stats():
    """Get WebSocket statistics"""
    from app.websocket import get_emitter, get_handlers
    
    emitter = get_emitter()
    handlers = get_handlers()
    
    return {
        "emitter": emitter.get_stats() if emitter else None,
        "clients": {
            "count": handlers.get_client_count() if handlers else 0,
            "connected": list(handlers.get_connected_clients().keys()) if handlers else []
        },
        "timestamp": time.time()
    }


# ============================================
# Create Socket.IO ASGI app
# ============================================

sio_app = socketio.ASGIApp(sio, app)


# ============================================
# WebSocket Event Reference (handled by WebSocketHandlers)
# ============================================
# 
# Server → Client Events:
#   - connection:success      : Connection established
#   - vehicle:update          : Vehicle position update (10 Hz)
#   - vehicle:spawned         : New vehicle spawned
#   - vehicle:removed         : Vehicle removed
#   - signal:change           : Signal state changed
#   - density:update          : Road density update (1 Hz)
#   - prediction:update       : Congestion predictions (0.2 Hz)
#   - agent:decision          : Agent made decision
#   - agent:status_update     : Agent status changed
#   - emergency:activated     : Emergency mode started
#   - emergency:deactivated   : Emergency mode ended
#   - emergency:progress      : Emergency corridor progress
#   - failsafe:triggered      : Fail-safe mode activated
#   - failsafe:cleared        : Fail-safe mode cleared
#   - violation:detected      : Traffic violation detected
#   - challan:issued          : Challan generated
#   - challan:paid            : Challan payment processed
#   - traffic:control:active  : Manual control activated
#   - traffic:control:removed : Manual control removed
#   - live:traffic:updated    : Live API data updated
#   - live:traffic:error      : Live API error
#   - map:loaded              : Map area loaded
#   - map:loading             : Map loading in progress
#   - map:error               : Map loading error
#   - data:mode:changed       : Traffic data mode changed
#   - system:state_update     : System state changed
#
# Client → Server Events:
#   - simulation:control      : Control simulation (PAUSE/RESUME/RESET)
#   - vehicle:spawn           : Request vehicle spawn
#   - signal:override         : Override signal state
#   - traffic:adjust          : Adjust traffic parameters
#   - emergency:trigger       : Trigger emergency mode
#   - emergency:clear         : Clear emergency mode
#   - map:load:request        : Request map load
#   - traffic:mode:change     : Change traffic data mode
#   - traffic:override:set    : Set manual traffic override
#   - traffic:override:clear  : Clear traffic override
#   - subscribe:updates       : Subscribe to update channels
#   - unsubscribe:updates     : Unsubscribe from channels


# ============================================
# Entry Point
# ============================================

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:sio_app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
