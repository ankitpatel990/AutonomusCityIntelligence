/**
 * Emergency & Safety Panel Component
 * 
 * Displays emergency status, safety mode, and health indicators with visual alerts.
 */

import React, { useEffect, useState } from 'react';
import { 
  AlertCircle, 
  Shield, 
  CheckCircle, 
  XCircle,
  Radio,
  Siren,
  Heart,
  Activity,
  MapPin
} from 'lucide-react';
import { useSystemStore } from '../store/useSystemStore';
import { api } from '../services/api';

interface HealthCheck {
  name: string;
  healthy: boolean;
  latency?: number;
  message?: string;
}

export const EmergencySafetyPanel: React.FC = () => {
  const { 
    mode, 
    activeEmergencies,
    wsConnected,
    agentStatus,
  } = useSystemStore();

  const [healthChecks, setHealthChecks] = useState<HealthCheck[]>([
    { name: 'Backend API', healthy: true },
    { name: 'WebSocket', healthy: wsConnected },
    { name: 'RL Agent', healthy: agentStatus !== 'STOPPED' },
    { name: 'Database', healthy: true },
  ]);

  useEffect(() => {
    setHealthChecks(prev => prev.map(check => {
      if (check.name === 'WebSocket') return { ...check, healthy: wsConnected };
      if (check.name === 'RL Agent') return { ...check, healthy: agentStatus !== 'STOPPED' };
      return check;
    }));
  }, [wsConnected, agentStatus]);

  const getModeConfig = () => {
    switch (mode) {
      case 'EMERGENCY':
        return {
          color: 'red',
          bgColor: 'bg-red-500/10',
          borderColor: 'border-red-500/30',
          textColor: 'text-red-400',
          icon: Siren,
          description: 'Emergency protocol active. Green corridor enabled.',
          pulse: true,
        };
      case 'INCIDENT':
        return {
          color: 'amber',
          bgColor: 'bg-amber-500/10',
          borderColor: 'border-amber-500/30',
          textColor: 'text-amber-400',
          icon: AlertCircle,
          description: 'Incident detected. Investigation in progress.',
          pulse: false,
        };
      case 'FAIL_SAFE':
        return {
          color: 'gray',
          bgColor: 'bg-gray-500/10',
          borderColor: 'border-gray-500/30',
          textColor: 'text-gray-400',
          icon: Shield,
          description: 'Fail-safe mode. All signals on fixed timing.',
          pulse: false,
        };
      default:
        return {
          color: 'emerald',
          bgColor: 'bg-emerald-500/10',
          borderColor: 'border-emerald-500/30',
          textColor: 'text-emerald-400',
          icon: CheckCircle,
          description: 'All systems operational. AI optimization active.',
          pulse: false,
        };
    }
  };

  const modeConfig = getModeConfig();
  const ModeIcon = modeConfig.icon;

  const handleEmergencyTrigger = async () => {
    if (activeEmergencies.length > 0) {
      alert('Emergency already active!');
      return;
    }
    
    try {
      // Trigger emergency using correct junction IDs (J-0 to J-8 for demo)
      const response = await api.triggerEmergency('J-0', 'J-8', 'AMBULANCE');
      console.log('Emergency triggered:', response);
    } catch (error) {
      console.error('Failed to trigger emergency:', error);
    }
  };

  return (
    <div className="space-y-4">
      {/* Emergency Alert Banner */}
      {activeEmergencies.length > 0 && (
        <div className="bg-red-500/10 border-2 border-red-500/50 rounded-xl p-4 animate-pulse">
          <div className="flex items-center gap-3">
            <div className="relative">
              <Siren className="w-8 h-8 text-red-500" />
              <div className="absolute -top-1 -right-1 w-3 h-3 bg-red-500 rounded-full animate-ping"></div>
            </div>
            <div>
              <h3 className="font-bold text-red-400 text-lg">EMERGENCY ACTIVE</h3>
              <p className="text-sm text-red-300">
                {activeEmergencies.length} emergency vehicle(s) in transit
              </p>
            </div>
          </div>
          
          {/* Emergency Details */}
          <div className="mt-4 space-y-2">
            {activeEmergencies.map((emergency) => (
              <div 
                key={emergency.vehicleId}
                className="bg-red-500/20 rounded-lg p-3 flex items-center justify-between"
              >
                <div className="flex items-center gap-2">
                  <Heart className="w-4 h-4 text-red-400" />
                  <span className="text-sm text-white font-medium">
                    {emergency.type}
                  </span>
                </div>
                <div className="flex items-center gap-2 text-xs text-red-300">
                  <MapPin className="w-3 h-3" />
                  <span>{emergency.destination}</span>
                  {emergency.eta && (
                    <span className="ml-2 font-mono">ETA: {emergency.eta}s</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* System Mode Card */}
      <div className={`${modeConfig.bgColor} border-2 ${modeConfig.borderColor} rounded-xl p-4 ${modeConfig.pulse ? 'animate-pulse' : ''}`}>
        <div className="flex items-center gap-3">
          <div className={`p-2 ${modeConfig.bgColor} rounded-lg`}>
            <ModeIcon className={`w-6 h-6 ${modeConfig.textColor}`} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-sm text-slate-400">System Mode:</span>
              <span className={`font-bold ${modeConfig.textColor}`}>{mode}</span>
            </div>
            <p className="text-xs text-slate-500 mt-1">{modeConfig.description}</p>
          </div>
        </div>
      </div>

      {/* Emergency Trigger Button (for demo) */}
      <button
        onClick={handleEmergencyTrigger}
        disabled={activeEmergencies.length > 0}
        className={`w-full flex items-center justify-center gap-2 px-4 py-3 rounded-xl font-medium transition-all ${
          activeEmergencies.length > 0
            ? 'bg-slate-700/50 text-slate-500 cursor-not-allowed'
            : 'bg-red-500/20 text-red-400 border border-red-500/30 hover:bg-red-500/30'
        }`}
      >
        <Radio className="w-5 h-5" />
        {activeEmergencies.length > 0 ? 'Emergency In Progress' : 'Trigger Emergency Demo'}
      </button>

      {/* Health Status */}
      <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl border border-slate-700/50 p-4">
        <div className="flex items-center gap-2 mb-4">
          <Activity className="w-5 h-5 text-cyan-400" />
          <h4 className="font-bold text-white">System Health</h4>
        </div>
        
        <div className="space-y-2">
          {healthChecks.map((check, index) => (
            <div 
              key={index}
              className="flex items-center justify-between py-2 px-3 bg-slate-900/30 rounded-lg"
            >
              <span className="text-sm text-slate-400">{check.name}</span>
              <div className="flex items-center gap-2">
                {check.latency && (
                  <span className="text-xs text-slate-500 font-mono">{check.latency}ms</span>
                )}
                {check.healthy ? (
                  <CheckCircle className="w-5 h-5 text-emerald-400" />
                ) : (
                  <XCircle className="w-5 h-5 text-red-400" />
                )}
              </div>
            </div>
          ))}
        </div>

        {/* Overall Health Score */}
        <div className="mt-4 pt-4 border-t border-slate-700/50">
          <div className="flex items-center justify-between">
            <span className="text-sm text-slate-400">Overall Health</span>
            <div className="flex items-center gap-2">
              <div className="w-20 h-2 bg-slate-700/50 rounded-full overflow-hidden">
                <div 
                  className="h-full bg-gradient-to-r from-emerald-500 to-cyan-400 rounded-full"
                  style={{ 
                    width: `${(healthChecks.filter(c => c.healthy).length / healthChecks.length) * 100}%` 
                  }}
                ></div>
              </div>
              <span className="text-xs font-bold text-emerald-400">
                {Math.round((healthChecks.filter(c => c.healthy).length / healthChecks.length) * 100)}%
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Safety Features Status */}
      <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl border border-slate-700/50 p-4">
        <div className="flex items-center gap-2 mb-4">
          <Shield className="w-5 h-5 text-cyan-400" />
          <h4 className="font-bold text-white">Safety Features</h4>
        </div>
        
        <div className="grid grid-cols-2 gap-3">
          {[
            { name: 'Signal Conflict Prevention', active: true },
            { name: 'Emergency Override', active: mode === 'EMERGENCY' },
            { name: 'Fail-Safe Mode', active: mode === 'FAIL_SAFE' },
            { name: 'Violation Detection', active: true },
          ].map((feature, index) => (
            <div 
              key={index}
              className={`px-3 py-2 rounded-lg text-xs font-medium flex items-center gap-2 ${
                feature.active 
                  ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' 
                  : 'bg-slate-700/30 text-slate-500'
              }`}
            >
              <div className={`w-2 h-2 rounded-full ${feature.active ? 'bg-emerald-400' : 'bg-slate-500'}`}></div>
              {feature.name}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

