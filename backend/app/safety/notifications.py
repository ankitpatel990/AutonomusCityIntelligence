"""
Safety Event WebSocket Notifications

Implements FRD-05 FR-05.6: Real-time safety notifications.
Emits real-time WebSocket notifications for safety events.
"""

import time
from typing import Optional


class SafetyNotificationService:
    """
    Emit real-time safety notifications via WebSocket
    
    Events:
    - mode_changed
    - failsafe_triggered
    - failsafe_exited
    - override_created
    - override_cancelled
    - health_alert
    - signal_conflict
    """
    
    def __init__(self, socketio):
        """
        Initialize notification service
        
        Args:
            socketio: Socket.IO server instance
        """
        self.sio = socketio
        
        print("[SAFETY] Safety Notification Service initialized")
    
    async def emit_mode_changed(self, old_mode: str, new_mode: str, reason: str):
        """Emit mode change event"""
        if not self.sio:
            return
        
        try:
            await self.sio.emit('safety:mode_changed', {
                'oldMode': old_mode,
                'newMode': new_mode,
                'reason': reason,
                'timestamp': time.time()
            })
        except Exception as e:
            print(f"[NOTIFICATION] Error emitting mode_changed: {e}")
    
    async def emit_failsafe_triggered(self, reason: str):
        """Emit fail-safe triggered event"""
        if not self.sio:
            return
        
        try:
            await self.sio.emit('safety:failsafe_triggered', {
                'reason': reason,
                'timestamp': time.time()
            })
            
            # Also emit urgent alert
            await self.sio.emit('alert', {
                'level': 'CRITICAL',
                'message': f'FAIL-SAFE ACTIVATED: {reason}',
                'timestamp': time.time()
            })
        except Exception as e:
            print(f"[NOTIFICATION] Error emitting failsafe_triggered: {e}")
    
    async def emit_failsafe_exited(self, operator_id: str):
        """Emit fail-safe exited event"""
        if not self.sio:
            return
        
        try:
            await self.sio.emit('safety:failsafe_exited', {
                'operatorId': operator_id,
                'timestamp': time.time()
            })
        except Exception as e:
            print(f"[NOTIFICATION] Error emitting failsafe_exited: {e}")
    
    async def emit_override_created(self, override: dict):
        """Emit override created event"""
        if not self.sio:
            return
        
        try:
            await self.sio.emit('safety:override_created', override)
        except Exception as e:
            print(f"[NOTIFICATION] Error emitting override_created: {e}")
    
    async def emit_override_cancelled(self, override_id: str):
        """Emit override cancelled event"""
        if not self.sio:
            return
        
        try:
            await self.sio.emit('safety:override_cancelled', {
                'overrideId': override_id,
                'timestamp': time.time()
            })
        except Exception as e:
            print(f"[NOTIFICATION] Error emitting override_cancelled: {e}")
    
    async def emit_health_alert(self, check_name: str, severity: str, message: str):
        """Emit health alert"""
        if not self.sio:
            return
        
        try:
            await self.sio.emit('safety:health_alert', {
                'checkName': check_name,
                'severity': severity,
                'message': message,
                'timestamp': time.time()
            })
        except Exception as e:
            print(f"[NOTIFICATION] Error emitting health_alert: {e}")
    
    async def emit_signal_conflict(self, junction_id: str, details: dict):
        """Emit signal conflict detected"""
        if not self.sio:
            return
        
        try:
            await self.sio.emit('safety:signal_conflict', {
                'junctionId': junction_id,
                'details': details,
                'timestamp': time.time()
            })
            
            # Also emit alert
            await self.sio.emit('alert', {
                'level': 'CRITICAL',
                'message': f'Signal conflict at {junction_id}',
                'timestamp': time.time()
            })
        except Exception as e:
            print(f"[NOTIFICATION] Error emitting signal_conflict: {e}")


# Global instance
_notification_service: Optional[SafetyNotificationService] = None


def get_notification_service() -> Optional[SafetyNotificationService]:
    """Get global notification service"""
    return _notification_service


def set_notification_service(service: SafetyNotificationService):
    """Set global notification service"""
    global _notification_service
    _notification_service = service

