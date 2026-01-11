"""
Prediction Broadcast Service
FRD-06: AI-Based Congestion Prediction - FR-06.5

Background task to broadcast predictions and alerts via WebSocket
to connected clients in real-time.

Broadcast frequency:
- Predictions: Every 30 seconds
- Alerts: Immediately when generated

Part of the Autonomous City Traffic Intelligence System.
"""

import asyncio
import time
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from app.websocket.emitter import WebSocketEmitter


class PredictionBroadcastService:
    """
    Background service to broadcast predictions and alerts
    
    Broadcasts:
    - prediction:updated - All predictions every 30 seconds
    - prediction:alert - New alerts immediately
    
    Usage:
        service = PredictionBroadcastService(ws_emitter)
        await service.start()
        # ... later ...
        await service.stop()
    """
    
    def __init__(self, 
                 ws_emitter: 'WebSocketEmitter' = None,
                 broadcast_interval: float = 30.0):
        """
        Initialize prediction broadcast service
        
        Args:
            ws_emitter: WebSocket emitter instance
            broadcast_interval: Seconds between prediction broadcasts
        """
        self.ws_emitter = ws_emitter
        self.broadcast_interval = broadcast_interval
        
        self._running = False
        self._task: Optional[asyncio.Task] = None
        
        # Statistics
        self.total_broadcasts = 0
        self.total_alerts_sent = 0
        self.last_broadcast_time = 0
    
    def set_ws_emitter(self, emitter: 'WebSocketEmitter'):
        """Set the WebSocket emitter"""
        self.ws_emitter = emitter
    
    async def start(self):
        """Start the background broadcast task"""
        if self._running:
            return
        
        self._running = True
        self._task = asyncio.create_task(self._broadcast_loop())
        print("[OK] Prediction broadcast service started")
    
    async def stop(self):
        """Stop the background broadcast task"""
        self._running = False
        
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        
        print("🛑 Prediction broadcast service stopped")
    
    async def _broadcast_loop(self):
        """Main broadcast loop"""
        from app.prediction import (
            get_prediction_engine,
            get_congestion_classifier
        )
        
        while self._running:
            try:
                # Get prediction engine and classifier
                engine = get_prediction_engine()
                classifier = get_congestion_classifier()
                
                if not engine or not classifier:
                    await asyncio.sleep(5)
                    continue
                
                # Get all predictions
                road_ids = list(engine.density_history.keys())
                
                if road_ids:
                    predictions = engine.predict_all_roads(road_ids)
                    
                    # Check for alerts
                    all_alerts = []
                    for road_id, prediction in predictions.items():
                        alerts = classifier.check_for_alerts(prediction)
                        all_alerts.extend(alerts)
                    
                    # Broadcast predictions
                    await self._broadcast_predictions(predictions, classifier)
                    
                    # Broadcast alerts if any
                    if all_alerts:
                        await self._broadcast_alerts(all_alerts)
                
                # Wait for next broadcast
                await asyncio.sleep(self.broadcast_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"[ERROR] Prediction broadcast error: {e}")
                await asyncio.sleep(5)
    
    async def _broadcast_predictions(self, predictions: dict, classifier):
        """Broadcast prediction updates"""
        if not self.ws_emitter:
            return
        
        try:
            current_time = time.time()
            
            # Format predictions for broadcast (limit to 20 roads)
            formatted = []
            for road_id, pred in list(predictions.items())[:20]:
                max_level = classifier.get_max_predicted_level(pred)
                
                formatted.append({
                    'roadId': road_id,
                    'currentDensity': round(pred.current_density, 2),
                    'maxCongestionLevel': max_level.value,
                    'confidence': round(pred.confidence, 2),
                    'predictions': [
                        {
                            'minutesAhead': int((ts - pred.predicted_at) / 60),
                            'predictedDensity': round(density, 2),
                            'congestionLevel': classifier.classify_density(density).value
                        }
                        for ts, density in pred.predictions[:5]  # First 5 predictions
                    ]
                })
            
            # Emit via WebSocket
            await self.ws_emitter._emit('prediction:updated', {
                'timestamp': current_time,
                'totalRoads': len(formatted),
                'predictions': formatted
            })
            
            self.total_broadcasts += 1
            self.last_broadcast_time = current_time
            
        except Exception as e:
            print(f"[WARN] Failed to broadcast predictions: {e}")
    
    async def _broadcast_alerts(self, alerts: list):
        """Broadcast prediction alerts"""
        if not self.ws_emitter:
            return
        
        try:
            current_time = time.time()
            
            formatted_alerts = [
                {
                    'alertId': alert.alert_id,
                    'roadId': alert.road_id,
                    'predictedLevel': alert.predicted_level.value,
                    'minutesAhead': max(0, int((alert.predicted_at_time - alert.created_at) / 60)),
                    'severity': alert.severity.value,
                    'message': alert.message
                }
                for alert in alerts
            ]
            
            await self.ws_emitter._emit('prediction:alert', {
                'timestamp': current_time,
                'alerts': formatted_alerts
            })
            
            self.total_alerts_sent += len(alerts)
            
        except Exception as e:
            print(f"[WARN] Failed to broadcast alerts: {e}")
    
    async def broadcast_single_alert(self, alert):
        """Broadcast a single alert immediately"""
        if not self.ws_emitter:
            return
        
        await self._broadcast_alerts([alert])
    
    def get_statistics(self) -> dict:
        """Get broadcast service statistics"""
        return {
            'running': self._running,
            'totalBroadcasts': self.total_broadcasts,
            'totalAlertsSent': self.total_alerts_sent,
            'lastBroadcastTime': self.last_broadcast_time,
            'broadcastInterval': self.broadcast_interval
        }


# Global broadcast service instance
_broadcast_service: Optional[PredictionBroadcastService] = None


def get_broadcast_service() -> Optional[PredictionBroadcastService]:
    """Get the global broadcast service instance"""
    return _broadcast_service


def init_broadcast_service(ws_emitter=None, interval: float = 30.0) -> PredictionBroadcastService:
    """Initialize the global broadcast service"""
    global _broadcast_service
    _broadcast_service = PredictionBroadcastService(ws_emitter, interval)
    return _broadcast_service

