/**
 * usePrediction Hook - React Hook for Congestion Predictions
 * FRD-06: AI-Based Congestion Prediction
 * 
 * Provides easy access to prediction data and real-time updates.
 */

import { useState, useEffect, useCallback } from 'react';
import { socket } from '../services/websocket';
import {
  RoadPrediction,
  CongestionAlert,
  PredictionsResponse,
  AlertsResponse,
  PredictionUpdatedEvent,
  PredictionAlertEvent,
  PredictionStatistics,
  predictionAPI,
  CongestionLevel
} from '../types/prediction';

// ============================================
// Hook: usePredictions
// ============================================

interface UsePredictionsOptions {
  roadIds?: string[];
  minConfidence?: number;
  autoRefresh?: boolean;
  refreshInterval?: number;  // ms
}

interface UsePredictionsResult {
  predictions: RoadPrediction[];
  loading: boolean;
  error: Error | null;
  refresh: () => Promise<void>;
  lastUpdated: number | null;
}

export const usePredictions = (options: UsePredictionsOptions = {}): UsePredictionsResult => {
  const { roadIds, minConfidence, autoRefresh = true, refreshInterval = 30000 } = options;
  
  const [predictions, setPredictions] = useState<RoadPrediction[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [lastUpdated, setLastUpdated] = useState<number | null>(null);
  
  const refresh = useCallback(async () => {
    try {
      setLoading(true);
      const response = await predictionAPI.getAllPredictions(roadIds, minConfidence);
      setPredictions(response.predictions);
      setLastUpdated(response.generatedAt);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to fetch predictions'));
    } finally {
      setLoading(false);
    }
  }, [roadIds, minConfidence]);
  
  // Initial fetch
  useEffect(() => {
    refresh();
  }, [refresh]);
  
  // Auto-refresh
  useEffect(() => {
    if (!autoRefresh) return;
    
    const interval = setInterval(refresh, refreshInterval);
    return () => clearInterval(interval);
  }, [autoRefresh, refreshInterval, refresh]);
  
  // WebSocket updates
  useEffect(() => {
    const handlePredictionUpdate = (data: PredictionUpdatedEvent) => {
      // Update predictions from WebSocket event
      setPredictions(prevPredictions => {
        const updatedMap = new Map<string, RoadPrediction>();
        
        // Keep existing predictions
        for (const pred of prevPredictions) {
          updatedMap.set(pred.roadId, pred);
        }
        
        // Update with new data
        for (const update of data.predictions) {
          const existing = updatedMap.get(update.roadId);
          if (existing) {
            updatedMap.set(update.roadId, {
              ...existing,
              currentDensity: update.currentDensity,
              maxCongestionLevel: update.maxCongestionLevel,
              predictions: update.predictions.map(p => ({
                timestamp: Date.now() + p.minutesAhead * 60000,
                minutesAhead: p.minutesAhead,
                predictedDensity: p.predictedDensity,
                congestionLevel: p.congestionLevel
              }))
            });
          }
        }
        
        return Array.from(updatedMap.values());
      });
      
      setLastUpdated(data.timestamp);
    };
    
    socket.on('prediction:updated', handlePredictionUpdate);
    
    return () => {
      socket.off('prediction:updated', handlePredictionUpdate);
    };
  }, []);
  
  return { predictions, loading, error, refresh, lastUpdated };
};

// ============================================
// Hook: useRoadPrediction
// ============================================

interface UseRoadPredictionResult {
  prediction: RoadPrediction | null;
  loading: boolean;
  error: Error | null;
  refresh: () => Promise<void>;
}

export const useRoadPrediction = (roadId: string): UseRoadPredictionResult => {
  const [prediction, setPrediction] = useState<RoadPrediction | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  
  const refresh = useCallback(async () => {
    if (!roadId) return;
    
    try {
      setLoading(true);
      const data = await predictionAPI.getRoadPrediction(roadId);
      setPrediction(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to fetch prediction'));
    } finally {
      setLoading(false);
    }
  }, [roadId]);
  
  useEffect(() => {
    refresh();
  }, [refresh]);
  
  // Auto-refresh every 30 seconds
  useEffect(() => {
    const interval = setInterval(refresh, 30000);
    return () => clearInterval(interval);
  }, [refresh]);
  
  return { prediction, loading, error, refresh };
};

// ============================================
// Hook: usePredictionAlerts
// ============================================

interface UsePredictionAlertsOptions {
  roadId?: string;
  activeOnly?: boolean;
  autoRefresh?: boolean;
  showNotifications?: boolean;
}

interface UsePredictionAlertsResult {
  alerts: CongestionAlert[];
  loading: boolean;
  error: Error | null;
  resolveAlert: (alertId: string) => Promise<void>;
  refresh: () => Promise<void>;
}

export const usePredictionAlerts = (options: UsePredictionAlertsOptions = {}): UsePredictionAlertsResult => {
  const { roadId, activeOnly = true, autoRefresh = true, showNotifications = true } = options;
  
  const [alerts, setAlerts] = useState<CongestionAlert[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  
  const refresh = useCallback(async () => {
    try {
      setLoading(true);
      const response = await predictionAPI.getAlerts(roadId, undefined, activeOnly);
      setAlerts(response.alerts);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to fetch alerts'));
    } finally {
      setLoading(false);
    }
  }, [roadId, activeOnly]);
  
  const resolveAlert = useCallback(async (alertId: string) => {
    try {
      await predictionAPI.resolveAlert(alertId);
      setAlerts(prev => prev.filter(a => a.alertId !== alertId));
    } catch (err) {
      console.error('Failed to resolve alert:', err);
    }
  }, []);
  
  // Initial fetch
  useEffect(() => {
    refresh();
  }, [refresh]);
  
  // Auto-refresh
  useEffect(() => {
    if (!autoRefresh) return;
    
    const interval = setInterval(refresh, 30000);
    return () => clearInterval(interval);
  }, [autoRefresh, refresh]);
  
  // WebSocket alerts
  useEffect(() => {
    const handleAlertEvent = (data: PredictionAlertEvent) => {
      // Add new alerts
      const newAlerts: CongestionAlert[] = data.alerts.map(a => ({
        alertId: a.alertId,
        roadId: a.roadId,
        predictedLevel: a.predictedLevel,
        predictedAtTime: Date.now() + a.minutesAhead * 60000,
        minutesAhead: a.minutesAhead,
        predictedDensity: 0,  // Not provided in event
        confidence: 0,  // Not provided in event
        severity: a.severity,
        message: a.message,
        createdAt: data.timestamp,
        resolved: false
      }));
      
      setAlerts(prev => [...newAlerts, ...prev]);
      
      // Show browser notification for critical alerts
      if (showNotifications) {
        for (const alert of newAlerts) {
          if (alert.severity === 'CRITICAL') {
            showBrowserNotification({
              title: 'Critical Congestion Alert',
              body: alert.message,
              icon: '/vite.svg'
            });
          }
        }
      }
    };
    
    socket.on('prediction:alert', handleAlertEvent);
    
    return () => {
      socket.off('prediction:alert', handleAlertEvent);
    };
  }, [showNotifications]);
  
  return { alerts, loading, error, resolveAlert, refresh };
};

// ============================================
// Hook: usePredictionStats
// ============================================

interface UsePredictionStatsResult {
  statistics: PredictionStatistics | null;
  loading: boolean;
  error: Error | null;
  refresh: () => Promise<void>;
}

export const usePredictionStats = (): UsePredictionStatsResult => {
  const [statistics, setStatistics] = useState<PredictionStatistics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  
  const refresh = useCallback(async () => {
    try {
      setLoading(true);
      const data = await predictionAPI.getStatistics();
      setStatistics(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to fetch statistics'));
    } finally {
      setLoading(false);
    }
  }, []);
  
  useEffect(() => {
    refresh();
  }, [refresh]);
  
  // Refresh every 60 seconds
  useEffect(() => {
    const interval = setInterval(refresh, 60000);
    return () => clearInterval(interval);
  }, [refresh]);
  
  return { statistics, loading, error, refresh };
};

// ============================================
// Helper: Browser Notification
// ============================================

interface NotificationOptions {
  title: string;
  body: string;
  icon?: string;
}

const showBrowserNotification = (options: NotificationOptions): void => {
  if (!('Notification' in window)) return;
  
  if (Notification.permission === 'granted') {
    new Notification(options.title, {
      body: options.body,
      icon: options.icon
    });
  } else if (Notification.permission !== 'denied') {
    Notification.requestPermission().then(permission => {
      if (permission === 'granted') {
        new Notification(options.title, {
          body: options.body,
          icon: options.icon
        });
      }
    });
  }
};

// ============================================
// Hook: usePredictionWebSocket
// ============================================

interface UsePredictionWebSocketOptions {
  onPredictionUpdate?: (data: PredictionUpdatedEvent) => void;
  onAlert?: (alerts: CongestionAlert[]) => void;
}

export const usePredictionWebSocket = (options: UsePredictionWebSocketOptions = {}): void => {
  const { onPredictionUpdate, onAlert } = options;
  
  useEffect(() => {
    const handlePredictionUpdate = (data: PredictionUpdatedEvent) => {
      onPredictionUpdate?.(data);
    };
    
    const handleAlert = (data: PredictionAlertEvent) => {
      const alerts: CongestionAlert[] = data.alerts.map(a => ({
        alertId: a.alertId,
        roadId: a.roadId,
        predictedLevel: a.predictedLevel,
        predictedAtTime: Date.now() + a.minutesAhead * 60000,
        minutesAhead: a.minutesAhead,
        predictedDensity: 0,
        confidence: 0,
        severity: a.severity,
        message: a.message,
        createdAt: data.timestamp,
        resolved: false
      }));
      
      onAlert?.(alerts);
    };
    
    socket.on('prediction:updated', handlePredictionUpdate);
    socket.on('prediction:alert', handleAlert);
    
    return () => {
      socket.off('prediction:updated', handlePredictionUpdate);
      socket.off('prediction:alert', handleAlert);
    };
  }, [onPredictionUpdate, onAlert]);
};

export default usePredictions;

