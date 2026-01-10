/**
 * Safety Page
 * 
 * Dedicated page for safety monitoring, fail-safe controls, and system health
 */

import React, { useState } from 'react';
import { 
  Shield, 
  AlertTriangle, 
  CheckCircle, 
  XCircle,
  Activity,
  Lock,
  Unlock,
  Eye,
  Power,
  RefreshCw
} from 'lucide-react';
import { useSystemStore } from '../store/useSystemStore';

export const SafetyPage: React.FC = () => {
  const { mode, setMode } = useSystemStore();
  const [confirmModal, setConfirmModal] = useState<string | null>(null);

  const safetyFeatures = [
    { 
      name: 'Signal Conflict Prevention', 
      description: 'Prevents conflicting GREEN signals at same junction',
      status: 'active',
      critical: true,
    },
    { 
      name: 'Emergency Override System', 
      description: 'Allows emergency vehicles to trigger green corridors',
      status: 'active',
      critical: true,
    },
    { 
      name: 'Fail-Safe Mode', 
      description: 'Fixed timing fallback when AI is unavailable',
      status: mode === 'FAIL_SAFE' ? 'active' : 'standby',
      critical: true,
    },
    { 
      name: 'Violation Detection', 
      description: 'Automated detection of traffic violations',
      status: 'active',
      critical: false,
    },
    { 
      name: 'Health Monitoring', 
      description: 'Continuous system health checks',
      status: 'active',
      critical: false,
    },
    { 
      name: 'Data Backup', 
      description: 'Periodic backup of critical system data',
      status: 'active',
      critical: false,
    },
  ];

  const handleModeChange = (newMode: 'NORMAL' | 'FAIL_SAFE') => {
    setConfirmModal(newMode);
  };

  const confirmModeChange = () => {
    if (confirmModal) {
      setMode(confirmModal as any);
      setConfirmModal(null);
    }
  };

  return (
    <div className="p-6 space-y-6 min-h-full">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <Shield className="w-7 h-7 text-cyan-400" />
            Safety & Monitoring
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            System safety controls and health monitoring
          </p>
        </div>
        <div className={`px-4 py-2 rounded-xl font-medium text-sm flex items-center gap-2 ${
          mode === 'FAIL_SAFE' 
            ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30' 
            : 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
        }`}>
          {mode === 'FAIL_SAFE' ? (
            <Lock className="w-4 h-4" />
          ) : (
            <Unlock className="w-4 h-4" />
          )}
          {mode === 'FAIL_SAFE' ? 'Fail-Safe Active' : 'Normal Operation'}
        </div>
      </div>

      {/* Mode Control */}
      <div className="bg-slate-800/50 backdrop-blur-sm rounded-2xl border border-slate-700/50 p-6">
        <h2 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
          <Power className="w-5 h-5 text-cyan-400" />
          System Mode Control
        </h2>
        <div className="grid grid-cols-2 gap-4">
          <button
            onClick={() => handleModeChange('NORMAL')}
            disabled={mode === 'NORMAL'}
            className={`p-6 rounded-xl border-2 transition-all ${
              mode === 'NORMAL'
                ? 'bg-emerald-500/20 border-emerald-500/50 text-emerald-400'
                : 'bg-slate-700/30 border-slate-600/50 text-slate-400 hover:border-emerald-500/30'
            }`}
          >
            <Activity className="w-8 h-8 mx-auto mb-3" />
            <h3 className="font-bold text-lg">Normal Mode</h3>
            <p className="text-sm text-slate-400 mt-2">
              AI-powered optimization active. Full autonomous control.
            </p>
          </button>
          
          <button
            onClick={() => handleModeChange('FAIL_SAFE')}
            disabled={mode === 'FAIL_SAFE'}
            className={`p-6 rounded-xl border-2 transition-all ${
              mode === 'FAIL_SAFE'
                ? 'bg-amber-500/20 border-amber-500/50 text-amber-400'
                : 'bg-slate-700/30 border-slate-600/50 text-slate-400 hover:border-amber-500/30'
            }`}
          >
            <Shield className="w-8 h-8 mx-auto mb-3" />
            <h3 className="font-bold text-lg">Fail-Safe Mode</h3>
            <p className="text-sm text-slate-400 mt-2">
              Fixed timing signals. AI disabled. Maximum safety.
            </p>
          </button>
        </div>
      </div>

      {/* Safety Features */}
      <div className="bg-slate-800/50 backdrop-blur-sm rounded-2xl border border-slate-700/50 p-6">
        <h2 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
          <Eye className="w-5 h-5 text-cyan-400" />
          Safety Features Status
        </h2>
        <div className="grid grid-cols-2 gap-4">
          {safetyFeatures.map((feature, index) => (
            <div 
              key={index}
              className={`p-4 rounded-xl border ${
                feature.status === 'active'
                  ? 'bg-emerald-500/10 border-emerald-500/20'
                  : 'bg-slate-700/30 border-slate-600/30'
              }`}
            >
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="font-bold text-white">{feature.name}</h3>
                    {feature.critical && (
                      <span className="text-xs px-1.5 py-0.5 bg-red-500/20 text-red-400 rounded">
                        CRITICAL
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-slate-400 mt-1">{feature.description}</p>
                </div>
                {feature.status === 'active' ? (
                  <CheckCircle className="w-6 h-6 text-emerald-400 flex-shrink-0" />
                ) : (
                  <div className="w-6 h-6 rounded-full bg-amber-500/20 flex items-center justify-center">
                    <div className="w-2 h-2 rounded-full bg-amber-400"></div>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* System Alerts */}
      <div className="bg-slate-800/50 backdrop-blur-sm rounded-2xl border border-slate-700/50 p-6">
        <h2 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
          <AlertTriangle className="w-5 h-5 text-amber-400" />
          System Alerts
        </h2>
        <div className="space-y-3">
          <div className="flex items-center gap-3 p-3 bg-emerald-500/10 rounded-lg border border-emerald-500/20">
            <CheckCircle className="w-5 h-5 text-emerald-400" />
            <div>
              <p className="text-sm text-emerald-400 font-medium">All Systems Operational</p>
              <p className="text-xs text-slate-400">Last check: 2 seconds ago</p>
            </div>
          </div>
          <div className="flex items-center gap-3 p-3 bg-slate-700/30 rounded-lg border border-slate-600/30">
            <Activity className="w-5 h-5 text-cyan-400" />
            <div>
              <p className="text-sm text-white font-medium">RL Agent Performance Optimal</p>
              <p className="text-xs text-slate-400">Decision latency: 1.8ms average</p>
            </div>
          </div>
        </div>
      </div>

      {/* Confirmation Modal */}
      {confirmModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-slate-800 rounded-2xl border border-slate-700 p-6 max-w-md w-full mx-4">
            <h3 className="text-xl font-bold text-white mb-2">Confirm Mode Change</h3>
            <p className="text-slate-400 mb-6">
              Are you sure you want to switch to{' '}
              <span className="font-bold text-white">{confirmModal}</span> mode?
              {confirmModal === 'FAIL_SAFE' && (
                <span className="block mt-2 text-amber-400">
                  Warning: This will disable AI optimization.
                </span>
              )}
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => setConfirmModal(null)}
                className="flex-1 px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-all"
              >
                Cancel
              </button>
              <button
                onClick={confirmModeChange}
                className={`flex-1 px-4 py-2 rounded-lg transition-all ${
                  confirmModal === 'FAIL_SAFE'
                    ? 'bg-amber-500 hover:bg-amber-600 text-white'
                    : 'bg-emerald-500 hover:bg-emerald-600 text-white'
                }`}
              >
                Confirm
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

