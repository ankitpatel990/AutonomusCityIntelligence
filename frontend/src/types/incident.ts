/**
 * Post-Incident Vehicle Tracking Types (FRD-08)
 * 
 * TypeScript interfaces for incident management and vehicle inference.
 */

/**
 * Incident types
 */
export type IncidentType = 'HIT_AND_RUN' | 'THEFT' | 'SUSPICIOUS' | 'ACCIDENT' | 'OTHER';

/**
 * Incident status
 */
export type IncidentStatus = 'PROCESSING' | 'COMPLETED' | 'RESOLVED' | 'FAILED';

/**
 * Request to report a vehicle incident
 */
export interface IncidentReportRequest {
  numberPlate: string;
  incidentTime: number;
  incidentType: IncidentType;
  location?: string;
  locationName?: string;
  lat?: number;
  lon?: number;
  description?: string;
}

/**
 * Response from incident report
 */
export interface IncidentReportResponse {
  incidentId: string;
  status: string;
  message: string;
  estimatedProcessingTime: number;
}

/**
 * Probable location where the vehicle might be
 */
export interface ProbableLocation {
  junctionId: string;
  junctionName?: string;
  lat?: number;
  lon?: number;
  confidence: number;
  distance: number;
  estimatedTravelTime: number;
}

/**
 * Detection record in vehicle history
 */
export interface DetectionHistoryItem {
  junctionId: string;
  junctionName?: string;
  timestamp: number;
  direction: string;
  lat?: number;
  lon?: number;
}

/**
 * Vehicle location inference result
 */
export interface InferenceResult {
  incidentId: string;
  numberPlate: string;
  
  lastKnownLocation?: string;
  lastKnownLocationName?: string;
  lastSeenTime?: number;
  lastSeenLat?: number;
  lastSeenLon?: number;
  
  timeElapsed: number;
  
  probableLocations: ProbableLocation[];
  searchRadius: number;
  searchCenterLat?: number;
  searchCenterLon?: number;
  
  detectionHistory: DetectionHistoryItem[];
  detectionCount: number;
  
  confidence: number;
  inferenceTimeMs: number;
  processedAt: number;
}

/**
 * Full incident details
 */
export interface Incident {
  id: string;
  numberPlate: string;
  incidentType: IncidentType;
  incidentTime: number;
  location?: string;
  locationName?: string;
  lat?: number;
  lon?: number;
  description?: string;
  
  status: IncidentStatus;
  reportedAt: number;
  processedAt?: number;
  resolvedAt?: number;
  resolutionNotes?: string;
  
  inferenceResult?: InferenceResult;
}

/**
 * Incident list response
 */
export interface IncidentListResponse {
  total: number;
  incidents: Incident[];
}

/**
 * Incident system statistics
 */
export interface IncidentStatistics {
  timestamp: number;
  incidentManager?: {
    totalIncidents: number;
    totalResolved: number;
    activeIncidents: number;
    hasInferenceEngine: boolean;
  };
  inferenceEngine?: {
    totalInferences: number;
    avgInferenceTimeMs: number;
    avgCitySpeed: number;
    maxSearchRadius: number;
    detectionTimeWindow: number;
    graphNodes: number;
    graphEdges: number;
    cachedJunctions: number;
  };
  detectionLogger?: {
    totalDetections: number;
    totalFlushes: number;
    bufferSize: number;
    lastFlushTime: number;
    retentionHours: number;
  };
}

/**
 * Detection log entry (for simulation integration)
 */
export interface DetectionLogEntry {
  vehicleId: string;
  numberPlate: string;
  junctionId: string;
  direction: 'N' | 'E' | 'S' | 'W';
  positionX: number;
  positionY: number;
  speed: number;
  vehicleType: string;
  timestamp: number;
}

