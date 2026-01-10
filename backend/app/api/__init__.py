"""
API Routes Package

This module exports all FastAPI routers for the Traffic Intelligence System.
"""

from .system_routes import router as system_router
from .agent_routes import router as agent_router
from .simulation_routes import router as simulation_router
from .traffic_routes import router as traffic_router
from .emergency_routes import router as emergency_router
from .incident_routes import router as incident_router
from .challan_routes import router as challan_router
from .prediction_routes import router as prediction_router
from .density_routes import router as density_router
from .test_tomtom_routes import router as test_tomtom_router
from .rl_routes import router as rl_router

__all__ = [
    "system_router",
    "agent_router",
    "simulation_router",
    "traffic_router",
    "emergency_router",
    "incident_router",
    "challan_router",
    "prediction_router",
    "density_router",
    "test_tomtom_router",
    "rl_router",
]
