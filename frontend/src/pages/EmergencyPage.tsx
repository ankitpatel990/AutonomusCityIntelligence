/**
 * Emergency Page
 * 
 * Dedicated page for emergency vehicle management and corridor control
 * Includes emergency triggers, corridor visualization, and history
 */

import React, { useState, useEffect } from 'react';
import { 
  Siren, 
  Radio, 
  MapPin, 
  Clock, 
  Activity,
  AlertTriangle,
  CheckCircle,
  XCircle,
  RefreshCw,
  Play,
  ArrowRight,
  Target,
  Navigation,
  Heart,
  Flame,
  Shield,
  Truck,
  History
} from 'lucide-react';
import { api } from '../services/api';
import { useSystemStore } from '../store/useSystemStore';

interface EmergencySession {
  sessionId: string;
  vehicleType: 'AMBULANCE' | 'FIRE_TRUCK' | 'POLICE';
  startJunction: string;
  endJunction: string;
  status: 'ACTIVE' | 'COMPLETED' | 'CANCELLED';
  startTime: number;
  endTime?: number;
  corridorPath: string[];
  eta?: number;
}

interface EmergencyStats {
  totalEmergencies: number;
  activeNow: number;
  avgResponseTime: number;
  avgCorridorLength: number;
}

export const EmergencyPage: React.FC = () => {
  const { activeEmergencies, mode } = useSystemStore();
  const [sessions, setSessions] = useState<EmergencySession[]>([]);
  const [stats, setStats] = useState<EmergencyStats | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [showTriggerModal, setShowTriggerModal] = useState(false);

  useEffect(() => {
    fetchEmergencyData();
    const interval = setInterval(fetchEmergencyData, 3000);
    return () => clearInterval(interval);
  }, []);

  const fetchEmergencyData = async () => {
    try {
      const [statusData, historyData, statsData] = await Promise.all([
        api.getEmergencyStatus(),
        api.getEmergencyHistory(10),
        api.getEmergencyStatistics(),
      ]);
      
      if (statusData.activeSessions) {
        setSessions([...statusData.activeSessions, ...(historyData.sessions || [])]);
      } else if (historyData.sessions) {
        setSessions(historyData.sessions);
      }
      
      if (statsData) {
        setStats(statsData);
      }
    } catch (error) {
      console.error('Failed to fetch emergency data:', error);
      // Use mock data
      setSessions(mockSessions);
      setStats(mockStats);
    }
  };

  const handleCancelEmergency = async (sessionId: string) => {
    if (!confirm('Are you sure you want to cancel this emergency?')) return;
    
    try {
      await api.cancelEmergency(sessionId, 'Cancelled by operator');
      fetchEmergencyData();
    } catch (error) {
      console.error('Failed to cancel emergency:', error);
    }
  };

  const getVehicleIcon = (type: string) => {
    switch (type) {
      case 'AMBULANCE':
        return <Heart className="w-5 h-5" />;
      case 'FIRE_TRUCK':
        return <Flame className="w-5 h-5" />;
      case 'POLICE':
        return <Shield className="w-5 h-5" />;
      default:
        return <Truck className="w-5 h-5" />;
    }
  };

  const getVehicleColor = (type: string) => {
    switch (type) {
      case 'AMBULANCE':
        return 'text-red-400 bg-red-500/20';
      case 'FIRE_TRUCK':
        return 'text-orange-400 bg-orange-500/20';
      case 'POLICE':
        return 'text-blue-400 bg-blue-500/20';
      default:
        return 'text-slate-400 bg-slate-500/20';
    }
  };

  const activeSessions = sessions.filter(s => s.status === 'ACTIVE');
  const historySessions = sessions.filter(s => s.status !== 'ACTIVE').slice(0, 5);

  return (
    <div className="p-6 space-y-6 min-h-full">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <Siren className="w-7 h-7 text-red-400" />
            Emergency Control Center
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Manage emergency vehicles and green corridors
          </p>
        </div>
        <div className="flex items-center gap-3">
          {mode === 'EMERGENCY' && (
            <div className="flex items-center gap-2 px-4 py-2 bg-red-500/20 text-red-400 border border-red-500/30 rounded-lg animate-pulse">
              <AlertTriangle className="w-4 h-4" />
              Emergency Mode Active
            </div>
          )}
          <button
            onClick={() => setShowTriggerModal(true)}
            className="flex items-center gap-2 px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 transition-all"
          >
            <Radio className="w-4 h-4" />
            Trigger Emergency
          </button>
        </div>
      </div>

      {/* Statistics */}
      <div className="grid grid-cols-4 gap-4">
        {[
          { 
            title: 'Total Emergencies', 
            value: stats?.totalEmergencies || 0, 
            icon: Siren,
            color: 'text-red-400',
            bgColor: 'bg-red-500/10'
          },
          { 
            title: 'Active Now', 
            value: stats?.activeNow || activeSessions.length, 
            icon: Activity,
            color: 'text-amber-400',
            bgColor: 'bg-amber-500/10'
          },
          { 
            title: 'Avg Response Time', 
            value: stats?.avgResponseTime ? `${stats.avgResponseTime.toFixed(0)}s` : 'N/A', 
            icon: Clock,
            color: 'text-cyan-400',
            bgColor: 'bg-cyan-500/10'
          },
          { 
            title: 'Avg Corridor Length', 
            value: stats?.avgCorridorLength ? `${stats.avgCorridorLength.toFixed(0)} junctions` : 'N/A', 
            icon: Navigation,
            color: 'text-purple-400',
            bgColor: 'bg-purple-500/10'
          },
        ].map((stat, index) => (
          <div key={index} className="bg-slate-800/50 backdrop-blur-sm rounded-xl border border-slate-700/50 p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-400">{stat.title}</p>
                <p className={`text-2xl font-bold mt-1 ${stat.color}`}>{stat.value}</p>
              </div>
              <div className={`${stat.bgColor} p-2.5 rounded-lg`}>
                <stat.icon className={`w-5 h-5 ${stat.color}`} />
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Active Emergencies */}
      <div className="bg-slate-800/50 backdrop-blur-sm rounded-2xl border border-slate-700/50 p-5">
        <h2 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
          <Activity className="w-5 h-5 text-red-400" />
          Active Emergencies
        </h2>
        
        {activeSessions.length > 0 ? (
          <div className="space-y-4">
            {activeSessions.map((session) => (
              <div 
                key={session.sessionId}
                className="bg-red-500/10 border-2 border-red-500/30 rounded-xl p-4 animate-pulse"
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-4">
                    <div className={`p-3 rounded-xl ${getVehicleColor(session.vehicleType)}`}>
                      {getVehicleIcon(session.vehicleType)}
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-white text-lg">
                          {session.vehicleType.replace('_', ' ')}
                        </span>
                        <span className="text-xs font-mono text-slate-400">
                          {session.sessionId}
                        </span>
                      </div>
                      
                      {/* Route */}
                      <div className="flex items-center gap-3 mt-2 text-sm">
                        <div className="flex items-center gap-1 text-emerald-400">
                          <MapPin className="w-4 h-4" />
                          {session.startJunction}
                        </div>
                        <ArrowRight className="w-4 h-4 text-slate-500" />
                        <div className="flex items-center gap-1 text-red-400">
                          <Target className="w-4 h-4" />
                          {session.endJunction}
                        </div>
                      </div>
                      
                      {/* Corridor Path */}
                      {session.corridorPath && session.corridorPath.length > 0 && (
                        <div className="mt-3">
                          <p className="text-xs text-slate-500 mb-1">Corridor Path:</p>
                          <div className="flex items-center gap-1 flex-wrap">
                            {session.corridorPath.map((junction, idx) => (
                              <React.Fragment key={junction}>
                                <span className="px-2 py-0.5 bg-red-500/20 text-red-400 rounded text-xs font-mono">
                                  {junction}
                                </span>
                                {idx < session.corridorPath.length - 1 && (
                                  <ArrowRight className="w-3 h-3 text-slate-600" />
                                )}
                              </React.Fragment>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                  
                  <div className="flex flex-col items-end gap-2">
                    {session.eta && (
                      <div className="flex items-center gap-1 text-cyan-400 font-mono">
                        <Clock className="w-4 h-4" />
                        ETA: {session.eta}s
                      </div>
                    )}
                    <button
                      onClick={() => handleCancelEmergency(session.sessionId)}
                      className="px-3 py-1.5 bg-slate-700/50 hover:bg-slate-700 text-slate-300 rounded-lg text-sm transition-all"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <div className="p-4 bg-slate-700/30 rounded-full mb-4">
              <Siren className="w-10 h-10 text-slate-500" />
            </div>
            <p className="text-lg text-slate-400 font-medium">No Active Emergencies</p>
            <p className="text-sm text-slate-500 mt-1">
              All clear. System operating in normal mode.
            </p>
          </div>
        )}
      </div>

      {/* Emergency History */}
      <div className="bg-slate-800/50 backdrop-blur-sm rounded-2xl border border-slate-700/50 p-5">
        <h2 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
          <History className="w-5 h-5 text-cyan-400" />
          Recent History
        </h2>
        
        {historySessions.length > 0 ? (
          <div className="space-y-3">
            {historySessions.map((session) => (
              <div 
                key={session.sessionId}
                className="bg-slate-900/50 rounded-xl p-4 border border-slate-700/30"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className={`p-2.5 rounded-lg ${getVehicleColor(session.vehicleType)}`}>
                      {getVehicleIcon(session.vehicleType)}
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-white">
                          {session.vehicleType.replace('_', ' ')}
                        </span>
                        <span className={`text-xs px-2 py-0.5 rounded border ${
                          session.status === 'COMPLETED' 
                            ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30'
                            : 'bg-slate-500/20 text-slate-400 border-slate-500/30'
                        }`}>
                          {session.status}
                        </span>
                      </div>
                      <div className="flex items-center gap-3 mt-1 text-xs text-slate-500">
                        <span>{session.startJunction} → {session.endJunction}</span>
                        <span>•</span>
                        <span>{new Date(session.startTime * 1000).toLocaleString()}</span>
                      </div>
                    </div>
                  </div>
                  
                  {session.endTime && session.startTime && (
                    <div className="text-right">
                      <p className="text-sm text-emerald-400 font-bold">
                        {Math.round(session.endTime - session.startTime)}s
                      </p>
                      <p className="text-xs text-slate-500">Response Time</p>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-8">
            <p className="text-slate-400">No emergency history available</p>
          </div>
        )}
      </div>

      {/* Trigger Emergency Modal */}
      {showTriggerModal && (
        <TriggerEmergencyModal
          onClose={() => setShowTriggerModal(false)}
          onTrigger={fetchEmergencyData}
        />
      )}
    </div>
  );
};

// Trigger Emergency Modal
const TriggerEmergencyModal: React.FC<{
  onClose: () => void;
  onTrigger: () => void;
}> = ({ onClose, onTrigger }) => {
  const [vehicleType, setVehicleType] = useState<'AMBULANCE' | 'FIRE_TRUCK' | 'POLICE'>('AMBULANCE');
  const [startJunction, setStartJunction] = useState('J-001');
  const [endJunction, setEndJunction] = useState('J-009');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const junctions = [
    'J-001', 'J-002', 'J-003', 
    'J-004', 'J-005', 'J-006', 
    'J-007', 'J-008', 'J-009'
  ];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    
    try {
      await api.triggerEmergency(startJunction, endJunction, vehicleType);
      onTrigger();
      onClose();
    } catch (error) {
      console.error('Failed to trigger emergency:', error);
      alert('Failed to trigger emergency. Please try again.');
    }
    
    setIsSubmitting(false);
  };

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-6">
      <div className="bg-slate-800 rounded-2xl border border-slate-700 max-w-md w-full">
        <div className="p-6 border-b border-slate-700">
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <Siren className="w-5 h-5 text-red-400" />
            Trigger Emergency
          </h2>
          <p className="text-sm text-slate-400 mt-1">
            Create a green corridor for emergency vehicle
          </p>
        </div>
        
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {/* Vehicle Type Selection */}
          <div>
            <label className="block text-sm font-medium text-slate-400 mb-2">
              Emergency Vehicle Type
            </label>
            <div className="grid grid-cols-3 gap-2">
              {[
                { type: 'AMBULANCE', icon: Heart, label: 'Ambulance', color: 'red' },
                { type: 'FIRE_TRUCK', icon: Flame, label: 'Fire Truck', color: 'orange' },
                { type: 'POLICE', icon: Shield, label: 'Police', color: 'blue' },
              ].map((v) => (
                <button
                  key={v.type}
                  type="button"
                  onClick={() => setVehicleType(v.type as any)}
                  className={`p-3 rounded-xl border-2 transition-all ${
                    vehicleType === v.type
                      ? `bg-${v.color}-500/20 border-${v.color}-500/50 text-${v.color}-400`
                      : 'bg-slate-700/30 border-slate-600/50 text-slate-400 hover:border-slate-500'
                  }`}
                >
                  <v.icon className="w-6 h-6 mx-auto mb-1" />
                  <span className="text-xs">{v.label}</span>
                </button>
              ))}
            </div>
          </div>
          
          {/* Start Junction */}
          <div>
            <label className="block text-sm font-medium text-slate-400 mb-1">
              Start Junction (Spawn Point)
            </label>
            <select
              value={startJunction}
              onChange={(e) => setStartJunction(e.target.value)}
              className="w-full px-4 py-2 bg-slate-900/50 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-cyan-500/50"
            >
              {junctions.map(j => (
                <option key={j} value={j}>{j}</option>
              ))}
            </select>
          </div>
          
          {/* End Junction */}
          <div>
            <label className="block text-sm font-medium text-slate-400 mb-1">
              Destination Junction
            </label>
            <select
              value={endJunction}
              onChange={(e) => setEndJunction(e.target.value)}
              className="w-full px-4 py-2 bg-slate-900/50 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-cyan-500/50"
            >
              {junctions.filter(j => j !== startJunction).map(j => (
                <option key={j} value={j}>{j}</option>
              ))}
            </select>
          </div>
          
          {/* Route Preview */}
          <div className="bg-slate-900/50 rounded-lg p-3">
            <div className="flex items-center justify-center gap-3 text-sm">
              <div className="flex items-center gap-1 text-emerald-400">
                <MapPin className="w-4 h-4" />
                {startJunction}
              </div>
              <ArrowRight className="w-4 h-4 text-slate-500" />
              <div className="flex items-center gap-1 text-red-400">
                <Target className="w-4 h-4" />
                {endJunction}
              </div>
            </div>
          </div>
          
          <div className="flex gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-all"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting || startJunction === endJunction}
              className="flex-1 px-4 py-2 bg-red-500 hover:bg-red-600 text-white rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {isSubmitting ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  Triggering...
                </>
              ) : (
                <>
                  <Play className="w-4 h-4" />
                  Trigger Emergency
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

// Mock data
const mockSessions: EmergencySession[] = [
  {
    sessionId: 'EM-2026-001',
    vehicleType: 'AMBULANCE',
    startJunction: 'J-001',
    endJunction: 'J-009',
    status: 'COMPLETED',
    startTime: Date.now() / 1000 - 7200,
    endTime: Date.now() / 1000 - 7100,
    corridorPath: ['J-001', 'J-004', 'J-005', 'J-008', 'J-009'],
  },
  {
    sessionId: 'EM-2026-002',
    vehicleType: 'FIRE_TRUCK',
    startJunction: 'J-003',
    endJunction: 'J-007',
    status: 'COMPLETED',
    startTime: Date.now() / 1000 - 14400,
    endTime: Date.now() / 1000 - 14300,
    corridorPath: ['J-003', 'J-002', 'J-001', 'J-004', 'J-007'],
  },
];

const mockStats: EmergencyStats = {
  totalEmergencies: 42,
  activeNow: 0,
  avgResponseTime: 85,
  avgCorridorLength: 4.5,
};

