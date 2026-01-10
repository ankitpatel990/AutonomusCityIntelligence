/**
 * Navbar Component
 * 
 * Top navigation bar with system status, mode indicator, and branding
 */

import React from 'react';
import { Activity, Zap, Clock, AlertCircle, Wifi, WifiOff } from 'lucide-react';
import { useSystemStore } from '../store/useSystemStore';

export const Navbar: React.FC = () => {
  const { 
    mode, 
    wsConnected, 
    simulationTime, 
    isRunning,
    agentStatus 
  } = useSystemStore();

  const formatTime = (seconds: number) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const getModeStyle = () => {
    switch (mode) {
      case 'EMERGENCY':
        return 'bg-red-500/20 text-red-400 border-red-500/50 animate-pulse';
      case 'INCIDENT':
        return 'bg-amber-500/20 text-amber-400 border-amber-500/50';
      case 'FAIL_SAFE':
        return 'bg-gray-500/20 text-gray-400 border-gray-500/50';
      default:
        return 'bg-emerald-500/20 text-emerald-400 border-emerald-500/50';
    }
  };

  return (
    <nav className="bg-gradient-to-r from-slate-900 via-slate-800 to-slate-900 border-b border-cyan-500/20 px-6 py-3 shadow-lg shadow-cyan-500/5">
      <div className="flex items-center justify-between">
        {/* Branding */}
        <div className="flex items-center gap-4">
          <div className="relative">
            <div className="absolute inset-0 bg-cyan-500/20 rounded-lg blur-md"></div>
            <div className="relative bg-gradient-to-br from-cyan-500 to-blue-600 p-2 rounded-lg">
              <Activity className="w-6 h-6 text-white" />
            </div>
          </div>
          <div>
            <h1 className="text-xl font-bold bg-gradient-to-r from-cyan-400 via-blue-400 to-purple-400 bg-clip-text text-transparent">
              Autonomous City Traffic Intelligence
            </h1>
            <p className="text-xs text-slate-400 tracking-wider uppercase">
              Digital Twin Simulation • Gandhinagar
            </p>
          </div>
        </div>

        {/* Center: Time & Status */}
        <div className="flex items-center gap-6">
          {/* Simulation Time */}
          <div className="flex items-center gap-2 bg-slate-800/50 px-4 py-2 rounded-lg border border-slate-700">
            <Clock className="w-4 h-4 text-cyan-400" />
            <span className="font-mono text-lg text-white tracking-wider">
              {formatTime(simulationTime)}
            </span>
            {isRunning && (
              <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
            )}
          </div>

          {/* Agent Status */}
          <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border ${
            agentStatus === 'RUNNING' ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400' :
            agentStatus === 'PAUSED' ? 'bg-amber-500/10 border-amber-500/30 text-amber-400' :
            'bg-slate-500/10 border-slate-500/30 text-slate-400'
          }`}>
            <Zap className="w-4 h-4" />
            <span className="text-sm font-medium">RL Agent: {agentStatus}</span>
          </div>
        </div>

        {/* Right: Connection & Mode */}
        <div className="flex items-center gap-4">
          {/* Connection Status */}
          <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg ${
            wsConnected 
              ? 'bg-emerald-500/10 border border-emerald-500/30' 
              : 'bg-red-500/10 border border-red-500/30'
          }`}>
            {wsConnected ? (
              <>
                <Wifi className="w-4 h-4 text-emerald-400" />
                <span className="text-sm text-emerald-400">Live</span>
              </>
            ) : (
              <>
                <WifiOff className="w-4 h-4 text-red-400" />
                <span className="text-sm text-red-400">Offline</span>
              </>
            )}
          </div>

          {/* Mode Badge */}
          <div className={`flex items-center gap-2 px-4 py-1.5 rounded-lg border ${getModeStyle()}`}>
            {mode === 'EMERGENCY' && <AlertCircle className="w-4 h-4" />}
            <span className="text-sm font-bold tracking-wide">{mode}</span>
          </div>
        </div>
      </div>
    </nav>
  );
};

