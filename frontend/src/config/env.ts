/**
 * Environment Configuration
 * 
 * Centralized configuration for API URLs and environment settings
 */

export const config = {
  // API Configuration
  apiUrl: import.meta.env.VITE_API_URL || 'http://localhost:8001/api',
  wsUrl: import.meta.env.VITE_WS_URL || 'http://localhost:8001',
  
  // Environment
  isDevelopment: import.meta.env.DEV,
  isProduction: import.meta.env.PROD,
  
  // Feature Flags
  enableDebugLogs: import.meta.env.DEV,
  enableMockData: false,
  
  // Simulation Defaults
  defaultSimulationSpeed: 1,
  maxVehicles: 200,
  canvasWidth: 800,
  canvasHeight: 600,
  
  // Animation
  targetFPS: 60,
  animationInterval: 1000 / 60, // ~16.67ms
  
  // Refresh Intervals (ms)
  statsRefreshInterval: 2000,
  healthCheckInterval: 5000,
  densityRefreshInterval: 1000,
};

export default config;

