/**
 * API Client for Traffic Intelligence System
 * 
 * Provides type-safe methods for interacting with the backend REST API.
 */

import axios, { AxiosInstance, AxiosError } from 'axios';
import type { 
  SystemState, 
  Vehicle, 
  Junction, 
  RoadSegment,
  Violation,
  Challan,
  MapArea
} from '../types/models';
import type {
  Incident,
  IncidentReportRequest,
  IncidentReportResponse,
  InferenceResult,
  IncidentListResponse,
  IncidentStatistics,
  DetectionHistoryItem
} from '../types/incident';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001/api';

class ApiClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      timeout: 10000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor for logging
    this.client.interceptors.request.use(
      (config) => {
        console.log(`🌐 API Request: ${config.method?.toUpperCase()} ${config.url}`);
        return config;
      },
      (error) => {
        console.error('API Request Error:', error);
        return Promise.reject(error);
      }
    );

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        const message = error.response?.data || error.message;
        console.error('API Error:', message);
        return Promise.reject(error);
      }
    );
  }

  // ============================================
  // System State
  // ============================================

  async getSystemState(): Promise<SystemState> {
    const response = await this.client.get<SystemState>('/state');
    return response.data;
  }

  async getVehicles(type?: string): Promise<Vehicle[]> {
    const response = await this.client.get<Vehicle[]>('/vehicles', { 
      params: { type } 
    });
    return response.data;
  }

  async getJunctions(): Promise<Junction[]> {
    const response = await this.client.get<Junction[]>('/junctions');
    return response.data;
  }

  async getRoads(): Promise<RoadSegment[]> {
    const response = await this.client.get<RoadSegment[]>('/roads');
    return response.data;
  }

  async getDensity(): Promise<{ citywide: number; perJunction: Record<string, number>; perRoad: Record<string, number> }> {
    const response = await this.client.get('/density');
    return response.data;
  }

  // ============================================
  // Agent Control
  // ============================================

  async startAgent(strategy: 'RL' | 'RULE_BASED' = 'RL'): Promise<{ status: string; strategy: string; timestamp: number }> {
    const response = await this.client.post('/agent/start', { strategy });
    return response.data;
  }

  async stopAgent(): Promise<{ status: string; timestamp: number }> {
    const response = await this.client.post('/agent/stop');
    return response.data;
  }

  async pauseAgent(): Promise<{ status: string; timestamp: number }> {
    const response = await this.client.post('/agent/pause');
    return response.data;
  }

  async resumeAgent(): Promise<{ status: string; timestamp: number }> {
    const response = await this.client.post('/agent/resume');
    return response.data;
  }

  async getAgentStatus(): Promise<{ status: string; strategy: string; uptime: number; decisions: number; avgLatency: number }> {
    const response = await this.client.get('/agent/status');
    return response.data;
  }

  // ============================================
  // Simulation Control
  // ============================================

  async startSimulation(): Promise<{ status: string; timestamp: number }> {
    const response = await this.client.post('/simulation/start');
    return response.data;
  }

  async stopSimulation(): Promise<{ status: string; timestamp: number }> {
    const response = await this.client.post('/simulation/stop');
    return response.data;
  }

  async pauseSimulation(): Promise<{ status: string; timestamp: number }> {
    const response = await this.client.post('/simulation/pause');
    return response.data;
  }

  async resumeSimulation(): Promise<{ status: string; timestamp: number }> {
    const response = await this.client.post('/simulation/resume');
    return response.data;
  }

  async resetSimulation(): Promise<{ status: string; timestamp: number }> {
    const response = await this.client.post('/simulation/reset');
    return response.data;
  }

  async setSimulationSpeed(multiplier: 1 | 5 | 10): Promise<{ status: string; multiplier: number; timestamp: number }> {
    const response = await this.client.post('/simulation/speed', { multiplier });
    return response.data;
  }

  async getSimulationStatus(): Promise<{ running: boolean; paused: boolean; currentTime: number; timeMultiplier: number; totalVehicles: number }> {
    const response = await this.client.get('/simulation/status');
    return response.data;
  }

  // ============================================
  // Emergency Control (FRD-07)
  // ============================================

  async triggerEmergency(
    spawnPoint: string, 
    destination: string, 
    vehicleType: 'AMBULANCE' | 'FIRE_TRUCK' | 'POLICE' = 'AMBULANCE'
  ): Promise<any> {
    const response = await this.client.post('/emergency/trigger', { 
      spawnPoint, 
      destination,
      vehicleType 
    });
    return response.data;
  }

  async getEmergencyStatus(): Promise<any> {
    const response = await this.client.get('/emergency/status');
    return response.data;
  }

  async cancelEmergency(sessionId?: string, reason?: string): Promise<{ status: string }> {
    const params = sessionId ? { session_id: sessionId } : {};
    const response = await this.client.post('/emergency/cancel', { reason }, { params });
    return response.data;
  }

  async getEmergencyCorridor(): Promise<any> {
    const response = await this.client.get('/emergency/corridor');
    return response.data;
  }

  async getEmergencyStatistics(): Promise<any> {
    const response = await this.client.get('/emergency/statistics');
    return response.data;
  }

  async getEmergencyHistory(limit: number = 20): Promise<any> {
    const response = await this.client.get('/emergency/history', { params: { limit } });
    return response.data;
  }

  async simulateEmergency(spawn: string, destination: string, dryRun: boolean = true): Promise<any> {
    const response = await this.client.post('/emergency/simulate', null, { 
      params: { spawn, destination, dryRun } 
    });
    return response.data;
  }

  async calculateEmergencyPath(start: string, end: string): Promise<any> {
    const response = await this.client.get('/emergency/path', { 
      params: { start, end } 
    });
    return response.data;
  }

  // ============================================
  // Violations & Challans
  // ============================================

  async getViolations(limit: number = 100): Promise<Violation[]> {
    const response = await this.client.get<Violation[]>('/violations', { params: { limit } });
    return response.data;
  }

  async getChallans(status?: string): Promise<Challan[]> {
    const response = await this.client.get<Challan[]>('/challans', { params: { status } });
    return response.data;
  }

  async getChallanStats(): Promise<{ total: number; paid: number; pending: number; totalFines: number; collectedFines: number }> {
    const response = await this.client.get('/challans/stats');
    return response.data;
  }

  // ============================================
  // Map & Live Traffic (NEW v2.0)
  // ============================================

  async getMapAreas(): Promise<MapArea[]> {
    const response = await this.client.get<MapArea[]>('/map/areas');
    return response.data;
  }

  async loadMapArea(areaId: string): Promise<{ junctions: any[]; roads: any[]; bounds: any }> {
    const response = await this.client.post(`/map/load/${areaId}`);
    return response.data;
  }

  async getTrafficDataSource(): Promise<any> {
    const response = await this.client.get('/traffic/source');
    return response.data;
  }

  async setTrafficMode(mode: 'LIVE_API' | 'SIMULATION' | 'HYBRID' | 'MANUAL'): Promise<{ status: string; mode: string }> {
    const response = await this.client.post('/traffic/mode', { mode });
    return response.data;
  }

  // ============================================
  // Post-Incident Tracking (FRD-08)
  // ============================================

  /**
   * Report a vehicle incident for tracking
   */
  async reportIncident(request: IncidentReportRequest): Promise<IncidentReportResponse> {
    const response = await this.client.post<IncidentReportResponse>('/incident/report', request);
    return response.data;
  }

  /**
   * Get incident details
   */
  async getIncident(incidentId: string): Promise<Incident> {
    const response = await this.client.get<Incident>(`/incident/${incidentId}`);
    return response.data;
  }

  /**
   * Get inference results for an incident
   */
  async getInferenceResult(incidentId: string): Promise<InferenceResult> {
    const response = await this.client.get<InferenceResult>(`/incident/${incidentId}/inference`);
    return response.data;
  }

  /**
   * Get vehicle movement timeline for an incident
   */
  async getIncidentTimeline(incidentId: string): Promise<DetectionHistoryItem[]> {
    const response = await this.client.get<DetectionHistoryItem[]>(`/incident/${incidentId}/timeline`);
    return response.data;
  }

  /**
   * List all incidents
   */
  async listIncidents(
    status?: string,
    limit: number = 50,
    offset: number = 0
  ): Promise<IncidentListResponse> {
    const response = await this.client.get<IncidentListResponse>('/incidents', {
      params: { status, limit, offset }
    });
    return response.data;
  }

  /**
   * Resolve an incident
   */
  async resolveIncident(
    incidentId: string,
    resolution?: string
  ): Promise<{ incidentId: string; status: string; resolution?: string; resolvedAt: number }> {
    const response = await this.client.post(`/incident/${incidentId}/resolve`, null, {
      params: { resolution }
    });
    return response.data;
  }

  /**
   * Get incident system statistics
   */
  async getIncidentStatistics(): Promise<IncidentStatistics> {
    const response = await this.client.get<IncidentStatistics>('/incident/statistics');
    return response.data;
  }

  // ============================================
  // Health Check
  // ============================================

  async healthCheck(): Promise<{ status: string; timestamp: number }> {
    // Health check is at root, not under /api
    const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
    const rootUrl = baseUrl.replace('/api', '');
    const response = await axios.get(`${rootUrl}/health`);
    return response.data;
  }
}

// Export singleton instance
export const api = new ApiClient();

