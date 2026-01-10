/**
 * Analytics Page
 * 
 * Displays detailed analytics, charts, and historical data
 */

import React, { useState, useEffect } from 'react';
import { 
  BarChart3, 
  TrendingUp, 
  Clock, 
  Calendar,
  Activity,
  Zap,
  Target,
  RefreshCw
} from 'lucide-react';
import { useSystemStore } from '../store/useSystemStore';

interface ChartData {
  label: string;
  value: number;
  color: string;
}

export const Analytics: React.FC = () => {
  const { avgDensity, throughput, vehicleCount, agentLoopCount } = useSystemStore();
  const [timeRange, setTimeRange] = useState<'1h' | '6h' | '24h'>('1h');
  const [isLoading, setIsLoading] = useState(false);

  // Simulated historical data for demo
  const densityHistory: ChartData[] = [
    { label: '00:00', value: 25, color: '#22c55e' },
    { label: '04:00', value: 15, color: '#22c55e' },
    { label: '08:00', value: 75, color: '#ef4444' },
    { label: '12:00', value: 55, color: '#f59e0b' },
    { label: '16:00', value: 85, color: '#ef4444' },
    { label: '20:00', value: 45, color: '#f59e0b' },
  ];

  const junctionPerformance = [
    { id: 'J-001', efficiency: 92, waitTime: 12 },
    { id: 'J-002', efficiency: 78, waitTime: 28 },
    { id: 'J-003', efficiency: 85, waitTime: 18 },
    { id: 'J-004', efficiency: 95, waitTime: 8 },
    { id: 'J-005', efficiency: 72, waitTime: 35 },
  ];

  const handleRefresh = () => {
    setIsLoading(true);
    setTimeout(() => setIsLoading(false), 1000);
  };

  return (
    <div className="p-6 space-y-6 min-h-full">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <BarChart3 className="w-7 h-7 text-cyan-400" />
            Analytics Dashboard
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Historical data and performance metrics
          </p>
        </div>
        <div className="flex items-center gap-3">
          {/* Time Range Selector */}
          <div className="flex bg-slate-800/50 rounded-lg p-1">
            {(['1h', '6h', '24h'] as const).map((range) => (
              <button
                key={range}
                onClick={() => setTimeRange(range)}
                className={`px-3 py-1.5 rounded-md text-sm font-medium transition-all ${
                  timeRange === range
                    ? 'bg-cyan-500/20 text-cyan-400'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                {range}
              </button>
            ))}
          </div>
          <button
            onClick={handleRefresh}
            className="p-2 bg-slate-700/50 hover:bg-slate-700 rounded-lg transition-all"
          >
            <RefreshCw className={`w-5 h-5 text-slate-400 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Key Metrics Cards */}
      <div className="grid grid-cols-4 gap-4">
        {[
          { title: 'Avg Response Time', value: '1.2s', change: '-15%', positive: true, icon: Clock },
          { title: 'Traffic Throughput', value: `${throughput}/hr`, change: '+8%', positive: true, icon: TrendingUp },
          { title: 'Agent Efficiency', value: '94%', change: '+2%', positive: true, icon: Zap },
          { title: 'Congestion Events', value: '12', change: '-25%', positive: true, icon: Activity },
        ].map((metric, index) => (
          <div key={index} className="bg-slate-800/50 backdrop-blur-sm rounded-xl border border-slate-700/50 p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-slate-400">{metric.title}</span>
              <metric.icon className="w-4 h-4 text-cyan-400" />
            </div>
            <p className="text-2xl font-bold text-white">{metric.value}</p>
            <p className={`text-xs mt-1 ${metric.positive ? 'text-emerald-400' : 'text-red-400'}`}>
              {metric.change} from last period
            </p>
          </div>
        ))}
      </div>

      {/* Charts Grid */}
      <div className="grid grid-cols-2 gap-6">
        {/* Density Over Time */}
        <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl border border-slate-700/50 p-5">
          <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
            <Activity className="w-5 h-5 text-cyan-400" />
            Traffic Density Over Time
          </h3>
          <div className="h-64 flex items-end gap-4 px-4">
            {densityHistory.map((data, index) => (
              <div key={index} className="flex-1 flex flex-col items-center gap-2">
                <div 
                  className="w-full rounded-t-lg transition-all duration-500"
                  style={{ 
                    height: `${data.value * 2}px`, 
                    backgroundColor: data.color,
                    opacity: 0.8,
                  }}
                ></div>
                <span className="text-xs text-slate-500">{data.label}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Junction Performance */}
        <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl border border-slate-700/50 p-5">
          <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
            <Target className="w-5 h-5 text-cyan-400" />
            Junction Performance
          </h3>
          <div className="space-y-3">
            {junctionPerformance.map((junction) => (
              <div key={junction.id} className="flex items-center gap-4">
                <span className="w-16 text-sm text-slate-400 font-mono">{junction.id}</span>
                <div className="flex-1">
                  <div className="h-3 bg-slate-700/50 rounded-full overflow-hidden">
                    <div 
                      className={`h-full rounded-full transition-all duration-500 ${
                        junction.efficiency >= 90 ? 'bg-emerald-500' :
                        junction.efficiency >= 75 ? 'bg-amber-500' :
                        'bg-red-500'
                      }`}
                      style={{ width: `${junction.efficiency}%` }}
                    ></div>
                  </div>
                </div>
                <span className={`text-sm font-bold w-12 text-right ${
                  junction.efficiency >= 90 ? 'text-emerald-400' :
                  junction.efficiency >= 75 ? 'text-amber-400' :
                  'text-red-400'
                }`}>
                  {junction.efficiency}%
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* RL Agent Performance */}
      <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl border border-slate-700/50 p-5">
        <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
          <Zap className="w-5 h-5 text-purple-400" />
          RL Agent Performance
        </h3>
        <div className="grid grid-cols-4 gap-6">
          <div className="text-center">
            <p className="text-3xl font-bold text-purple-400">{agentLoopCount}</p>
            <p className="text-sm text-slate-400 mt-1">Decision Cycles</p>
          </div>
          <div className="text-center">
            <p className="text-3xl font-bold text-cyan-400">1.8ms</p>
            <p className="text-sm text-slate-400 mt-1">Avg Latency</p>
          </div>
          <div className="text-center">
            <p className="text-3xl font-bold text-emerald-400">32%</p>
            <p className="text-sm text-slate-400 mt-1">Improvement</p>
          </div>
          <div className="text-center">
            <p className="text-3xl font-bold text-amber-400">0</p>
            <p className="text-sm text-slate-400 mt-1">Signal Conflicts</p>
          </div>
        </div>
      </div>
    </div>
  );
};

