"""
Safety systems, fail-safe, and watchdog

Implements FRD-05: Safety & Fail-Safe Monitoring Systems.
"""

from .conflict_validator import ConflictValidator
from .system_modes import SystemMode, SystemModeManager
from .watchdog import Watchdog
from .manual_override import ManualOverrideManager, OverrideType
from .notifications import SafetyNotificationService, get_notification_service, set_notification_service

__all__ = [
    "ConflictValidator",
    "SystemMode",
    "SystemModeManager",
    "Watchdog",
    "ManualOverrideManager",
    "OverrideType",
    "SafetyNotificationService",
    "get_notification_service",
    "set_notification_service",
]
