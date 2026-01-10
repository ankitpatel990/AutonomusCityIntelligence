"""
Auto-Challan and Violation Enforcement System (FRD-09)

This module implements the automated traffic violation detection
and challan (fine) processing system.

Components:
- ViolationDetector: Real-time violation detection
- VehicleOwnerDatabase: Mock vehicle owner records
- ChallanManager: Challan generation and management
- AutoChallanService: Automated workflow integration

Usage:
    from app.challan import (
        init_violation_detector,
        init_vehicle_owner_db,
        init_challan_manager,
        init_auto_challan_service
    )
    
    # Initialize components
    detector = init_violation_detector(config)
    owner_db = init_vehicle_owner_db(config)
    manager = init_challan_manager(owner_db)
    service = init_auto_challan_service(detector, manager, config)
    
    # Start automatic processing
    await service.start()
"""

# Violation Detection
from .violation_detector import (
    ViolationType,
    ViolationEvent,
    ViolationDetector,
    init_violation_detector,
    get_violation_detector,
)

# Vehicle Owner Database
from .vehicle_owner_db import (
    VehicleOwnerRecord,
    VehicleOwnerDatabase,
    init_vehicle_owner_db,
    get_vehicle_owner_db,
)

# Challan Management
from .challan_manager import (
    ChallanStatus,
    ChallanRecord,
    ChallanManager,
    init_challan_manager,
    get_challan_manager,
)

# Auto-Challan Service
from .auto_challan_service import (
    AutoChallanService,
    init_auto_challan_service,
    get_auto_challan_service,
)


__all__ = [
    # Violation Detection
    "ViolationType",
    "ViolationEvent",
    "ViolationDetector",
    "init_violation_detector",
    "get_violation_detector",
    
    # Vehicle Owner Database
    "VehicleOwnerRecord",
    "VehicleOwnerDatabase",
    "init_vehicle_owner_db",
    "get_vehicle_owner_db",
    
    # Challan Management
    "ChallanStatus",
    "ChallanRecord",
    "ChallanManager",
    "init_challan_manager",
    "get_challan_manager",
    
    # Auto-Challan Service
    "AutoChallanService",
    "init_auto_challan_service",
    "get_auto_challan_service",
]
