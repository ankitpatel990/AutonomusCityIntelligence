/**
 * Prediction Types for Congestion Prediction System
 * FRD-06: AI-Based Congestion Prediction
 * 
 * TypeScript interfaces for prediction data and API responses.
 */

// ============================================
// Enums
// ============================================

export enum CongestionLevel {
  LOW = 'LOW',
  MEDIUM = 'MEDIUM',
  HIGH = 'HIGH',
  CRITICAL = 'CRITICAL'
}

export enum AlertSeverity {
  INFO = 'INFO',
  WARNING = 'WARNING',
  CRITICAL = 'CRITICAL'
}

// ============================================
// Core Types
// ============================================

export interface PredictionPoint {
  timestamp: number;
  minutesAhead: number;
  predictedDensity: number;
  congestionLevel: CongestionLevel;
}

export interface RoadPrediction {
  roadId: string;
  predictedAt: number;
  horizon: number;  // minutes
  confidence: number;  // 0-1
  algorithm: string;
  currentDensity: number;
  maxCongestionLevel: CongestionLevel;
  predictions: PredictionPoint[];
}

export interface JunctionPrediction {
  junctionId: string;
  connectedRoads: string[];
  predictedAt: number;
  horizon: number;
  currentDensity: number;
  maxCongestionLevel: CongestionLevel;
  predictions: {
    minutesAhead: number;
    avgPredictedDensity: number;
    congestionLevel: CongestionLevel;
  }[];
}

export interface CongestionAlert {
  alertId: string;
  roadId: string;
  predictedLevel: CongestionLevel;
  predictedAtTime: number;
  minutesAhead: number;
  predictedDensity: number;
  confidence: number;
  severity: AlertSeverity;
  message: string;
  createdAt: number;
  resolved: boolean;
}

export interface PredictionStatistics {
  engine: {
    algorithm: string;
    totalPredictions: number;
    trackedRoads: number;
    avgHistoryLength: number;
    predictionHorizon: number;
    updateFrequency: number;
    cacheSize: number;
    lastPredictionTime: number;
  };
  classifier: {
    totalAlertsGenerated: number;
    activeAlerts: number;
    alertsBySeverity: {
      INFO: number;
      WARNING: number;
      CRITICAL: number;
    };
    alertedRoads: number;
    thresholds: Record<string, string>;
  };
  timestamp: number;
}

export interface PredictionAccuracy {
  accuracy: {
    totalComparisons: number;
    meanAbsoluteError: number;
    rmse: number;
    classificationAccuracy: number;
    accuracyByTimeAhead: Record<string, {
      correct: number;
      total: number;
      accuracy: number;
    }>;
    timeWindowHours: number;
    timestamp: number;
  };
  bestWorst: {
    best: PredictionComparison[];
    worst: PredictionComparison[];
  };
  recentComparisons: PredictionComparison[];
  timestamp: number;
}

export interface PredictionComparison {
  roadId: string;
  roadName: string;
  timestamp: number;
  predictionTime: number;
  timeAhead: number;
  predictedDensity: number;
  actualDensity: number;
  absoluteError: number;
  relativeError: number;
  predictedCongestion: string;
  actualCongestion: string;
  correctClassification: boolean;
  confidence: number;
  dataSource: string;
}

export interface ModelStatus {
  predictionMode: string;
  algorithms: {
    moving_average: boolean;
    linear_trend: boolean;
    exponential_smoothing: boolean;
    neural_network: boolean;
  };
  rlPredictor: {
    available: boolean;
    statistics: any | null;
  };
  nnPredictor: {
    available: boolean;
    pytorchAvailable: boolean;
    statistics: any | null;
  };
  timestamp: number;
}

// ============================================
// API Response Types
// ============================================

export interface PredictionsResponse {
  totalRoads: number;
  predictions: RoadPrediction[];
  generatedAt: number;
  nextUpdate: number;
}

export interface AlertsResponse {
  totalAlerts: number;
  alerts: CongestionAlert[];
}

export interface ConfigureRequest {
  algorithm?: string;
  horizon?: number;
}

export interface ConfigureResponse {
  status: string;
  changes: string[];
  currentConfig: {
    algorithm: string;
    horizon: number;
    updateFrequency: number;
  };
  timestamp: number;
}

// ============================================
// WebSocket Event Types
// ============================================

export interface PredictionUpdatedEvent {
  timestamp: number;
  totalRoads: number;
  predictions: {
    roadId: string;
    currentDensity: number;
    maxCongestionLevel: CongestionLevel;
    predictions: {
      minutesAhead: number;
      predictedDensity: number;
      congestionLevel: CongestionLevel;
    }[];
  }[];
}

export interface PredictionAlertEvent {
  timestamp: number;
  alerts: {
    alertId: string;
    roadId: string;
    predictedLevel: CongestionLevel;
    minutesAhead: number;
    severity: AlertSeverity;
    message: string;
  }[];
}

// ============================================
// API Client
// ============================================

const API_BASE = '/api/predictions';

export const predictionAPI = {
  /**
   * Get all current predictions
   */
  getAllPredictions: async (roadIds?: string[], minConfidence?: number): Promise<PredictionsResponse> => {
    const params = new URLSearchParams();
    if (roadIds && roadIds.length > 0) {
      params.set('roadIds', roadIds.join(','));
    }
    if (minConfidence !== undefined) {
      params.set('minConfidence', minConfidence.toString());
    }
    
    const url = params.toString() ? `${API_BASE}?${params}` : API_BASE;
    const res = await fetch(url);
    if (!res.ok) throw new Error('Failed to fetch predictions');
    return res.json();
  },
  
  /**
   * Get prediction for specific road
   */
  getRoadPrediction: async (roadId: string): Promise<RoadPrediction> => {
    const res = await fetch(`${API_BASE}/roads/${roadId}`);
    if (!res.ok) throw new Error('Failed to fetch road prediction');
    return res.json();
  },
  
  /**
   * Get prediction for junction
   */
  getJunctionPrediction: async (junctionId: string, horizon?: number): Promise<JunctionPrediction> => {
    const params = horizon ? `?horizon=${horizon}` : '';
    const res = await fetch(`${API_BASE}/junction/${junctionId}${params}`);
    if (!res.ok) throw new Error('Failed to fetch junction prediction');
    return res.json();
  },
  
  /**
   * Get congestion alerts
   */
  getAlerts: async (roadId?: string, severity?: AlertSeverity, active?: boolean): Promise<AlertsResponse> => {
    const params = new URLSearchParams();
    if (roadId) params.set('roadId', roadId);
    if (severity) params.set('severity', severity);
    if (active !== undefined) params.set('active', active.toString());
    
    const url = params.toString() ? `${API_BASE}/alerts?${params}` : `${API_BASE}/alerts`;
    const res = await fetch(url);
    if (!res.ok) throw new Error('Failed to fetch alerts');
    return res.json();
  },
  
  /**
   * Resolve (dismiss) an alert
   */
  resolveAlert: async (alertId: string): Promise<{ status: string; alertId: string }> => {
    const res = await fetch(`${API_BASE}/alerts/${alertId}/resolve`, { method: 'POST' });
    if (!res.ok) throw new Error('Failed to resolve alert');
    return res.json();
  },
  
  /**
   * Get prediction statistics
   */
  getStatistics: async (): Promise<PredictionStatistics> => {
    const res = await fetch(`${API_BASE}/statistics`);
    if (!res.ok) throw new Error('Failed to fetch statistics');
    return res.json();
  },
  
  /**
   * Get prediction accuracy metrics
   */
  getAccuracy: async (timeWindow?: number): Promise<PredictionAccuracy> => {
    const params = timeWindow ? `?timeWindow=${timeWindow}` : '';
    const res = await fetch(`${API_BASE}/accuracy${params}`);
    if (!res.ok) throw new Error('Failed to fetch accuracy');
    return res.json();
  },
  
  /**
   * Get prediction history for a road
   */
  getHistory: async (roadId: string, duration?: number): Promise<any> => {
    const params = duration ? `?duration=${duration}` : '';
    const res = await fetch(`${API_BASE}/history/${roadId}${params}`);
    if (!res.ok) throw new Error('Failed to fetch history');
    return res.json();
  },
  
  /**
   * Configure prediction engine
   */
  configure: async (config: ConfigureRequest): Promise<ConfigureResponse> => {
    const res = await fetch(`${API_BASE}/configure`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config)
    });
    if (!res.ok) throw new Error('Failed to configure engine');
    return res.json();
  },
  
  /**
   * Get model status
   */
  getModelStatus: async (): Promise<ModelStatus> => {
    const res = await fetch(`${API_BASE}/model/status`);
    if (!res.ok) throw new Error('Failed to fetch model status');
    return res.json();
  },
  
  /**
   * Clear prediction cache
   */
  clearCache: async (): Promise<{ status: string; timestamp: number }> => {
    const res = await fetch(`${API_BASE}/clear-cache`, { method: 'POST' });
    if (!res.ok) throw new Error('Failed to clear cache');
    return res.json();
  }
};

// ============================================
// Utility Functions
// ============================================

/**
 * Get color for congestion level
 */
export const getCongestionColor = (level: CongestionLevel): string => {
  switch (level) {
    case CongestionLevel.LOW:
      return '#4ade80';  // Green
    case CongestionLevel.MEDIUM:
      return '#fbbf24';  // Yellow
    case CongestionLevel.HIGH:
      return '#f97316';  // Orange
    case CongestionLevel.CRITICAL:
      return '#ef4444';  // Red
    default:
      return '#9ca3af';  // Gray
  }
};

/**
 * Get Tailwind class for congestion level
 */
export const getCongestionClass = (level: CongestionLevel): string => {
  switch (level) {
    case CongestionLevel.LOW:
      return 'bg-green-500 text-white';
    case CongestionLevel.MEDIUM:
      return 'bg-yellow-500 text-black';
    case CongestionLevel.HIGH:
      return 'bg-orange-500 text-white';
    case CongestionLevel.CRITICAL:
      return 'bg-red-500 text-white';
    default:
      return 'bg-gray-500 text-white';
  }
};

/**
 * Get severity color
 */
export const getSeverityColor = (severity: AlertSeverity): string => {
  switch (severity) {
    case AlertSeverity.INFO:
      return '#3b82f6';  // Blue
    case AlertSeverity.WARNING:
      return '#f97316';  // Orange
    case AlertSeverity.CRITICAL:
      return '#ef4444';  // Red
    default:
      return '#9ca3af';  // Gray
  }
};

/**
 * Format prediction time
 */
export const formatPredictionTime = (minutesAhead: number): string => {
  if (minutesAhead <= 0) return 'Now';
  return `+${minutesAhead}min`;
};

/**
 * Format confidence as percentage
 */
export const formatConfidence = (confidence: number): string => {
  return `${(confidence * 100).toFixed(0)}%`;
};

/**
 * Get algorithm display name
 */
export const getAlgorithmName = (algorithm: string): string => {
  switch (algorithm) {
    case 'moving_average':
      return 'Moving Average';
    case 'linear_trend':
      return 'Linear Trend';
    case 'exponential_smoothing':
      return 'Exponential Smoothing';
    case 'neural_network':
      return 'Neural Network (LSTM)';
    default:
      return algorithm;
  }
};

