/**
 * Emergency Overlay Component
 * 
 * Displays emergency vehicle status, corridor visualization, and controls.
 * Implements FRD-07 FR-07.6: Emergency visualization.
 */

import React, { useEffect, useState, useCallback } from 'react';
import {
  Siren,
  MapPin,
  Clock,
  Route,
  XCircle,
  TrendingUp,
  AlertTriangle,
  Ambulance,
  CheckCircle
} from 'lucide-react';
import { api } from '../services/api';
import type { 
  EmergencyStatus, 
  EmergencyStatistics,
  EmergencyProgressUpdate 
} from '../types/emergency';

interface EmergencyOverlayProps {
  socket?: any;  // Socket.IO instance for real-time updates
  onCorridorUpdate?: (junctions: string[]) => void;
}

export const EmergencyOverlay: React.FC<EmergencyOverlayProps> = ({ 
  socket,
  onCorridorUpdate 
}) => {
  const [emergency, setEmergency] = useState<EmergencyStatus | null>(null);
  const [stats, setStats] = useState<EmergencyStatistics | null>(null);
  const [loading, setLoading] = useState(false);
  const [expanded, setExpanded] = useState(true);
  const [cancelling, setCancelling] = useState(false);

  // Fetch emergency status
  const fetchStatus = useCallback(async () => {
    try {
      const status = await api.getEmergencyStatus();
      setEmergency(status);
      
      if (status.active && status.corridorPath && onCorridorUpdate) {
        onCorridorUpdate(status.corridorPath);
      }
    } catch (error) {
      console.error('Failed to fetch emergency status:', error);
    }
  }, [onCorridorUpdate]);

  // Fetch statistics
  const fetchStats = useCallback(async () => {
    try {
      const statistics = await api.getEmergencyStatistics();
      setStats(statistics);
    } catch (error) {
      console.error('Failed to fetch emergency statistics:', error);
    }
  }, []);

  // Initial fetch and polling
  useEffect(() => {
    fetchStatus();
    fetchStats();

    // Poll every 2 seconds when emergency is active
    const pollInterval = setInterval(() => {
      if (emergency?.active) {
        fetchStatus();
      }
    }, 2000);

    return () => clearInterval(pollInterval);
  }, [fetchStatus, fetchStats, emergency?.active]);

  // Setup WebSocket listeners
  useEffect(() => {
    if (!socket) return;

    const handleActivated = (data: any) => {
      console.log('🚨 Emergency activated:', data);
      fetchStatus();
      fetchStats();
    };

    const handleProgress = (data: EmergencyProgressUpdate) => {
      setEmergency(prev => prev ? {
        ...prev,
        currentJunction: data.currentJunction,
        progress: data.progress,
        estimatedArrival: data.estimatedArrival
      } : null);
    };

    const handleCompleted = (data: any) => {
      console.log('✅ Emergency completed:', data);
      fetchStatus();
      fetchStats();
    };

    socket.on('emergency:activated', handleActivated);
    socket.on('emergency:progress', handleProgress);
    socket.on('emergency:completed', handleCompleted);
    socket.on('emergency:deactivated', handleCompleted);

    return () => {
      socket.off('emergency:activated', handleActivated);
      socket.off('emergency:progress', handleProgress);
      socket.off('emergency:completed', handleCompleted);
      socket.off('emergency:deactivated', handleCompleted);
    };
  }, [socket, fetchStatus, fetchStats]);

  // Cancel emergency
  const handleCancel = async () => {
    if (!emergency?.sessionId) return;
    
    if (!confirm('Cancel the active emergency?')) return;
    
    setCancelling(true);
    try {
      await api.cancelEmergency(emergency.sessionId, 'Manual cancellation');
      fetchStatus();
      fetchStats();
    } catch (error) {
      console.error('Failed to cancel emergency:', error);
    } finally {
      setCancelling(false);
    }
  };

  // Don't render if no emergency active
  if (!emergency || !emergency.active) {
    return null;
  }

  const progress = emergency.progress || 0;
  const etaSeconds = emergency.estimatedArrival 
    ? Math.max(0, Math.round(emergency.estimatedArrival - Date.now() / 1000))
    : null;

  return (
    <div className="fixed top-4 right-4 z-50 max-w-sm">
      {/* Main Emergency Card */}
      <div 
        className="bg-gradient-to-br from-red-900/95 to-red-800/95 backdrop-blur-lg 
                   rounded-2xl border-2 border-red-500/50 shadow-2xl shadow-red-500/20
                   overflow-hidden animate-pulse-slow"
      >
        {/* Header with Siren Animation */}
        <div 
          className="px-4 py-3 bg-red-500/20 flex items-center justify-between cursor-pointer"
          onClick={() => setExpanded(!expanded)}
        >
          <div className="flex items-center gap-3">
            <div className="relative">
              <Siren className="w-8 h-8 text-red-400 animate-bounce" />
              <div className="absolute -top-1 -right-1 w-3 h-3 bg-red-400 rounded-full animate-ping"></div>
            </div>
            <div>
              <h3 className="font-bold text-red-100 text-lg tracking-wide">
                EMERGENCY ACTIVE
              </h3>
              <p className="text-xs text-red-300">
                {emergency.vehicleType || 'AMBULANCE'} • {emergency.numberPlate}
              </p>
            </div>
          </div>
          <Ambulance className="w-6 h-6 text-red-300" />
        </div>

        {/* Expanded Content */}
        {expanded && (
          <div className="p-4 space-y-4">
            {/* Progress Bar */}
            <div>
              <div className="flex justify-between text-xs text-red-200 mb-2">
                <span>Corridor Progress</span>
                <span className="font-mono font-bold">{progress.toFixed(1)}%</span>
              </div>
              <div className="h-3 bg-red-950/50 rounded-full overflow-hidden">
                <div 
                  className="h-full bg-gradient-to-r from-red-500 via-orange-500 to-green-500 
                             rounded-full transition-all duration-500 relative"
                  style={{ width: `${progress}%` }}
                >
                  <div className="absolute right-0 top-0 h-full w-4 bg-white/30 
                                  rounded-full animate-pulse"></div>
                </div>
              </div>
            </div>

            {/* Stats Grid */}
            <div className="grid grid-cols-2 gap-3">
              {/* Current Junction */}
              <div className="bg-red-950/40 rounded-lg p-3">
                <div className="flex items-center gap-2 text-xs text-red-300 mb-1">
                  <MapPin className="w-3 h-3" />
                  <span>Location</span>
                </div>
                <p className="text-white font-mono font-bold text-sm">
                  {emergency.currentJunction || 'Starting...'}
                </p>
              </div>

              {/* ETA */}
              <div className="bg-red-950/40 rounded-lg p-3">
                <div className="flex items-center gap-2 text-xs text-red-300 mb-1">
                  <Clock className="w-3 h-3" />
                  <span>ETA</span>
                </div>
                <p className="text-white font-mono font-bold text-sm">
                  {etaSeconds !== null ? `${etaSeconds}s` : 'Calculating...'}
                </p>
              </div>

              {/* Route */}
              <div className="bg-red-950/40 rounded-lg p-3">
                <div className="flex items-center gap-2 text-xs text-red-300 mb-1">
                  <Route className="w-3 h-3" />
                  <span>Route</span>
                </div>
                <p className="text-white font-mono font-bold text-sm">
                  {emergency.corridorPath?.length || 0} junctions
                </p>
              </div>

              {/* Destination */}
              <div className="bg-red-950/40 rounded-lg p-3">
                <div className="flex items-center gap-2 text-xs text-red-300 mb-1">
                  <TrendingUp className="w-3 h-3" />
                  <span>Destination</span>
                </div>
                <p className="text-white font-mono font-bold text-sm truncate">
                  {emergency.corridor?.junctionPath?.slice(-1)[0] || 'N/A'}
                </p>
              </div>
            </div>

            {/* Corridor Junctions */}
            {emergency.corridor?.signalOverrides && (
              <div className="bg-red-950/40 rounded-lg p-3">
                <div className="flex items-center gap-2 text-xs text-red-300 mb-2">
                  <AlertTriangle className="w-3 h-3" />
                  <span>Active Signals (GREEN)</span>
                </div>
                <div className="flex flex-wrap gap-1">
                  {Object.entries(emergency.corridor.signalOverrides).map(([junction, direction]) => (
                    <span 
                      key={junction}
                      className="px-2 py-1 bg-green-500/20 text-green-400 text-xs rounded-full 
                                 border border-green-500/30 font-mono"
                    >
                      {junction}→{direction.charAt(0).toUpperCase()}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Cancel Button */}
            <button
              onClick={handleCancel}
              disabled={cancelling}
              className="w-full flex items-center justify-center gap-2 px-4 py-2 
                        bg-red-950/50 hover:bg-red-900/70 border border-red-500/30
                        text-red-200 hover:text-white rounded-lg 
                        transition-all duration-200 text-sm font-medium
                        disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <XCircle className="w-4 h-4" />
              {cancelling ? 'Cancelling...' : 'Cancel Emergency'}
            </button>
          </div>
        )}
      </div>

      {/* Statistics Mini Card (if emergency active) */}
      {stats && stats.totalEmergencies > 0 && (
        <div className="mt-2 bg-slate-800/90 backdrop-blur-sm rounded-lg border border-slate-700/50 
                        p-3 flex items-center justify-between text-xs">
          <div className="flex items-center gap-2 text-slate-400">
            <CheckCircle className="w-4 h-4 text-emerald-400" />
            <span>{stats.completedEmergencies} completed</span>
          </div>
          <div className="text-emerald-400 font-mono font-bold">
            {stats.totalTimeSaved.toFixed(0)}s saved
          </div>
        </div>
      )}

      <style>{`
        @keyframes pulse-slow {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.95; }
        }
        .animate-pulse-slow {
          animation: pulse-slow 2s ease-in-out infinite;
        }
      `}</style>
    </div>
  );
};

export default EmergencyOverlay;


