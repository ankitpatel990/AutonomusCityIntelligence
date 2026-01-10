/**
 * Violations Panel Component
 * 
 * Displays recent traffic violations and challans with filtering options.
 */

import React, { useState } from 'react';
import { 
  AlertTriangle, 
  FileText, 
  Clock,
  MapPin,
  Car,
  Ban,
  Gauge,
  Filter
} from 'lucide-react';
import { useSystemStore } from '../store/useSystemStore';
import type { Violation, Challan } from '../types/models';

type TabType = 'violations' | 'challans';

export const ViolationsPanel: React.FC = () => {
  const { violations, challans } = useSystemStore();
  const [activeTab, setActiveTab] = useState<TabType>('violations');
  const [filter, setFilter] = useState<string>('all');

  const filteredViolations = filter === 'all' 
    ? violations 
    : violations.filter(v => v.violationType === filter);

  const filteredChallans = filter === 'all'
    ? challans
    : challans.filter(c => c.violationType === filter);

  return (
    <div className="bg-slate-800/50 backdrop-blur-sm rounded-2xl border border-slate-700/50 p-5">
      {/* Header with Tabs */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex gap-2">
          <button
            onClick={() => setActiveTab('violations')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all flex items-center gap-2 ${
              activeTab === 'violations'
                ? 'bg-red-500/20 text-red-400 border border-red-500/30'
                : 'text-slate-400 hover:bg-slate-700/50'
            }`}
          >
            <AlertTriangle className="w-4 h-4" />
            Violations
            {violations.length > 0 && (
              <span className="px-1.5 py-0.5 bg-red-500/30 rounded text-xs">
                {violations.length}
              </span>
            )}
          </button>
          <button
            onClick={() => setActiveTab('challans')}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all flex items-center gap-2 ${
              activeTab === 'challans'
                ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30'
                : 'text-slate-400 hover:bg-slate-700/50'
            }`}
          >
            <FileText className="w-4 h-4" />
            Challans
            {challans.length > 0 && (
              <span className="px-1.5 py-0.5 bg-blue-500/30 rounded text-xs">
                {challans.length}
              </span>
            )}
          </button>
        </div>

        {/* Filter */}
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-slate-500" />
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="bg-slate-700/50 border border-slate-600/50 rounded-lg px-3 py-1.5 text-sm text-slate-300 focus:outline-none focus:border-cyan-500/50"
          >
            <option value="all">All Types</option>
            <option value="RED_LIGHT">Red Light</option>
            <option value="SPEEDING">Speeding</option>
            <option value="WRONG_DIRECTION">Wrong Direction</option>
          </select>
        </div>
      </div>

      {/* Content */}
      <div className="space-y-2 max-h-[400px] overflow-y-auto pr-2 custom-scrollbar">
        {activeTab === 'violations' ? (
          filteredViolations.length > 0 ? (
            filteredViolations.map((violation) => (
              <ViolationCard key={violation.id} violation={violation} />
            ))
          ) : (
            <EmptyState type="violations" />
          )
        ) : (
          filteredChallans.length > 0 ? (
            filteredChallans.map((challan) => (
              <ChallanCard key={challan.challanId} challan={challan} />
            ))
          ) : (
            <EmptyState type="challans" />
          )
        )}
      </div>
    </div>
  );
};

const ViolationCard: React.FC<{ violation: Violation }> = ({ violation }) => {
  const formatTime = (timestamp: number) => {
    const date = new Date(timestamp * 1000);
    return date.toLocaleTimeString();
  };

  const getViolationIcon = (type: string) => {
    switch (type) {
      case 'RED_LIGHT':
        return <Ban className="w-4 h-4" />;
      case 'SPEEDING':
        return <Gauge className="w-4 h-4" />;
      default:
        return <AlertTriangle className="w-4 h-4" />;
    }
  };

  return (
    <div className="bg-slate-900/50 rounded-xl p-4 border border-slate-700/30 hover:border-slate-600/50 transition-all">
      <div className="flex items-start justify-between">
        <div className="flex items-start gap-3">
          <div className={`p-2 rounded-lg ${
            violation.violationType === 'RED_LIGHT' ? 'bg-red-500/20 text-red-400' :
            violation.violationType === 'SPEEDING' ? 'bg-amber-500/20 text-amber-400' :
            'bg-orange-500/20 text-orange-400'
          }`}>
            {getViolationIcon(violation.violationType)}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-white">{violation.numberPlate}</span>
              <span className={`text-xs px-2 py-0.5 rounded border ${
                violation.severity === 'HIGH' ? 'bg-red-500/10 border-red-500/30 text-red-400' :
                violation.severity === 'MEDIUM' ? 'bg-amber-500/10 border-amber-500/30 text-amber-400' :
                'bg-blue-500/10 border-blue-500/30 text-blue-400'
              }`}>
                {violation.severity}
              </span>
            </div>
            <p className="text-sm text-slate-400 mt-1">
              {violation.violationType.replace('_', ' ')}
            </p>
            <div className="flex items-center gap-4 mt-2 text-xs text-slate-500">
              <div className="flex items-center gap-1">
                <MapPin className="w-3 h-3" />
                {violation.location}
              </div>
              <div className="flex items-center gap-1">
                <Clock className="w-3 h-3" />
                {formatTime(violation.timestamp)}
              </div>
            </div>
          </div>
        </div>
        <div className={`w-2 h-2 rounded-full ${
          violation.processed ? 'bg-emerald-400' : 'bg-amber-400 animate-pulse'
        }`}></div>
      </div>
    </div>
  );
};

const ChallanCard: React.FC<{ challan: Challan }> = ({ challan }) => {
  const formatTime = (timestamp: number) => {
    const date = new Date(timestamp * 1000);
    return date.toLocaleString();
  };

  return (
    <div className="bg-slate-900/50 rounded-xl p-4 border border-slate-700/30 hover:border-slate-600/50 transition-all">
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2">
            <FileText className="w-4 h-4 text-blue-400" />
            <span className="font-mono text-sm text-blue-400">{challan.challanId}</span>
          </div>
          <div className="flex items-center gap-2 mt-2">
            <Car className="w-4 h-4 text-slate-400" />
            <span className="font-bold text-white">{challan.numberPlate}</span>
          </div>
          <p className="text-sm text-slate-400 mt-1">
            {challan.violationType.replace('_', ' ')}
          </p>
          <div className="flex items-center gap-4 mt-2 text-xs text-slate-500">
            <div className="flex items-center gap-1">
              <MapPin className="w-3 h-3" />
              {challan.location}
            </div>
            <div className="flex items-center gap-1">
              <Clock className="w-3 h-3" />
              {formatTime(challan.timestamp)}
            </div>
          </div>
        </div>
        <div className="text-right">
          <p className="text-lg font-bold text-emerald-400">₹{challan.fineAmount}</p>
          <span className={`text-xs px-2 py-0.5 rounded ${
            challan.status === 'PAID' ? 'bg-emerald-500/20 text-emerald-400' :
            challan.status === 'PENDING' ? 'bg-amber-500/20 text-amber-400' :
            challan.status === 'CANCELLED' ? 'bg-slate-500/20 text-slate-400' :
            'bg-blue-500/20 text-blue-400'
          }`}>
            {challan.status}
          </span>
        </div>
      </div>
    </div>
  );
};

const EmptyState: React.FC<{ type: 'violations' | 'challans' }> = ({ type }) => (
  <div className="flex flex-col items-center justify-center py-8 text-center">
    <div className="p-4 bg-slate-700/30 rounded-full mb-4">
      {type === 'violations' ? (
        <AlertTriangle className="w-8 h-8 text-slate-500" />
      ) : (
        <FileText className="w-8 h-8 text-slate-500" />
      )}
    </div>
    <p className="text-slate-400 font-medium">No {type} recorded</p>
    <p className="text-sm text-slate-500 mt-1">
      {type === 'violations' 
        ? 'Traffic monitoring is active'
        : 'All violations processed'
      }
    </p>
  </div>
);

