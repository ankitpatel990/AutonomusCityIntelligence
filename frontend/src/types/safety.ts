/**
 * Safety System TypeScript Types
 * 
 * Type definitions for safety and fail-safe system integration.
 * Implements FRD-05 FR-05.7: Safety dashboard data structures.
 */

export enum SystemMode {
  NORMAL = 'NORMAL',
  EMERGENCY = 'EMERGENCY',
  INCIDENT = 'INCIDENT',
  FAIL_SAFE = 'FAIL_SAFE'
}

export interface ModeState {
  mode: SystemMode;
  enteredAt: number;
  duration: number;
  reason: string;
  previousMode?: SystemMode;
}

export interface HealthCheck {
  name: string;
  critical: boolean;
  consecutiveFailures: number;
  maxFailures: number;
  healthy: boolean;
}

export interface HealthStatus {
  running: boolean;
  healthy: boolean;
  totalChecks: number;
  totalFailures: number;
  checks: HealthCheck[];
}

export interface ManualOverride {
  overrideId: string;
  type: 'JUNCTION_SIGNAL' | 'AGENT_DISABLE' | 'EMERGENCY_STOP' | 'MODE_CHANGE';
  operatorId: string;
  timestamp: number;
  targetId: string;
  parameters: any;
  active?: boolean;
  duration?: number;
  reason: string;
}

export interface SafetyAlert {
  level: 'INFO' | 'WARNING' | 'CRITICAL';
  message: string;
  timestamp: number;
}

// API client functions
export const safetyAPI = {
  // Mode management
  getCurrentMode: async (): Promise<ModeState> => {
    const res = await fetch('/api/safety/mode');
    if (!res.ok) throw new Error(`Failed to get mode: ${res.statusText}`);
    return res.json();
  },
  
  changeMode: async (mode: SystemMode, reason: string) => {
    const res = await fetch('/api/safety/mode/change', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({mode, reason})
    });
    if (!res.ok) throw new Error(`Failed to change mode: ${res.statusText}`);
    return res.json();
  },
  
  // Fail-safe
  triggerFailSafe: async (reason: string, operatorId: string) => {
    const res = await fetch('/api/safety/failsafe/trigger', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Operator-ID': operatorId
      },
      body: JSON.stringify({reason})
    });
    if (!res.ok) throw new Error(`Failed to trigger fail-safe: ${res.statusText}`);
    return res.json();
  },
  
  exitFailSafe: async (operatorId: string) => {
    const res = await fetch('/api/safety/failsafe/exit', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({operatorId})
    });
    if (!res.ok) throw new Error(`Failed to exit fail-safe: ${res.statusText}`);
    return res.json();
  },
  
  // Manual overrides
  forceSignal: async (params: {
    junctionId: string;
    direction: string;
    duration: number;
    operatorId: string;
    reason: string;
  }) => {
    const res = await fetch('/api/safety/override/signal', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(params)
    });
    if (!res.ok) throw new Error(`Failed to force signal: ${res.statusText}`);
    return res.json();
  },
  
  disableAgent: async (operatorId: string, reason: string) => {
    const res = await fetch('/api/safety/override/agent', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({action: 'disable', operatorId, reason})
    });
    if (!res.ok) throw new Error(`Failed to disable agent: ${res.statusText}`);
    return res.json();
  },
  
  enableAgent: async (operatorId: string) => {
    const res = await fetch('/api/safety/override/agent', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({action: 'enable', operatorId})
    });
    if (!res.ok) throw new Error(`Failed to enable agent: ${res.statusText}`);
    return res.json();
  },
  
  emergencyStop: async (operatorId: string, reason: string) => {
    const res = await fetch('/api/safety/override/emergency-stop', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({operatorId, reason})
    });
    if (!res.ok) throw new Error(`Failed to emergency stop: ${res.statusText}`);
    return res.json();
  },
  
  // Health
  getHealthStatus: async (): Promise<HealthStatus> => {
    const res = await fetch('/api/safety/health');
    if (!res.ok) throw new Error(`Failed to get health: ${res.statusText}`);
    return res.json();
  },
  
  // Overrides
  getActiveOverrides: async (): Promise<ManualOverride[]> => {
    const res = await fetch('/api/safety/overrides');
    if (!res.ok) throw new Error(`Failed to get overrides: ${res.statusText}`);
    return res.json();
  },
  
  cancelOverride: async (overrideId: string, operatorId: string) => {
    const res = await fetch(`/api/safety/override/${overrideId}`, {
      method: 'DELETE',
      headers: {'X-Operator-ID': operatorId}
    });
    if (!res.ok) throw new Error(`Failed to cancel override: ${res.statusText}`);
    return res.json();
  }
};

// WebSocket event listeners
export const setupSafetyListeners = (socket: any, callbacks: {
  onModeChanged?: (data: any) => void;
  onFailSafeTriggered?: (data: any) => void;
  onFailSafeExited?: (data: any) => void;
  onOverrideCreated?: (data: any) => void;
  onHealthAlert?: (data: any) => void;
  onSignalConflict?: (data: any) => void;
}) => {
  if (callbacks.onModeChanged) {
    socket.on('safety:mode_changed', callbacks.onModeChanged);
  }
  if (callbacks.onFailSafeTriggered) {
    socket.on('safety:failsafe_triggered', callbacks.onFailSafeTriggered);
  }
  if (callbacks.onFailSafeExited) {
    socket.on('safety:failsafe_exited', callbacks.onFailSafeExited);
  }
  if (callbacks.onOverrideCreated) {
    socket.on('safety:override_created', callbacks.onOverrideCreated);
  }
  if (callbacks.onHealthAlert) {
    socket.on('safety:health_alert', callbacks.onHealthAlert);
  }
  if (callbacks.onSignalConflict) {
    socket.on('safety:signal_conflict', callbacks.onSignalConflict);
  }
};

