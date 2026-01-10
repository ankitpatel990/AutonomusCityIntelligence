/**
 * Statistics Panel Component
 * 
 * Displays real-time statistics including traffic density, violations,
 * RL agent performance, and system health metrics.
 */

import React, { useEffect, useState } from 'react';
import { 
  Car, 
  AlertTriangle, 
  Activity, 
  TrendingUp,
  Zap,
  Clock,
  Gauge,
  Target,
  BarChart3,
  RefreshCw
} from 'lucide-react';
import { useSystemStore } from '../store/useSystemStore';
import { api } from '../services/api';

interface StatCard {
  title: string;
  value: string | number;
  unit?: string;
  icon: React.ElementType;
  color: string;
  bgColor: string;
  trend?: 'up' | 'down' | 'neutral';
  trendValue?: string;
}

export const StatisticsPanel: React.FC = () => {
  const {
    vehicleCount,
    avgDensity,
    congestionPoints,
    throughput,
    agentLoopCount,
    avgDecisionLatency,
    violations,
    fps,
  } = useSystemStore();

  const [isRefreshing, setIsRefreshing] = useState(false);
  const [additionalStats, setAdditionalStats] = useState({
    totalViolations: violations.length,
    challansIssued: 0,
    finesCollected: 0,
  });

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const challanStats = await api.getChallanStats();
        setAdditionalStats({
          totalViolations: violations.length,
          challansIssued: challanStats.total,
          finesCollected: challanStats.collectedFines,
        });
      } catch (error) {
        console.error('Failed to fetch stats:', error);
      }
    };

    fetchStats();
    const interval = setInterval(fetchStats, 5000);
    return () => clearInterval(interval);
  }, [violations.length]);

  const handleRefresh = async () => {
    setIsRefreshing(true);
    try {
      const state = await api.getSystemState();
      useSystemStore.getState().updatePerformance({
        vehicleCount: state.performance.vehicleCount,
        avgDensity: state.performance.avgDensity,
        congestionPoints: state.performance.congestionPoints,
        throughput: state.performance.throughput,
        fps: state.performance.fps,
      });
    } catch (error) {
      console.error('Failed to refresh:', error);
    }
    setIsRefreshing(false);
  };

  const statCards: StatCard[] = [
    {
      title: 'Active Vehicles',
      value: vehicleCount,
      icon: Car,
      color: 'text-blue-400',
      bgColor: 'bg-blue-500/10',
      trend: 'up',
      trendValue: '+12%',
    },
    {
      title: 'Avg Density',
      value: avgDensity.toFixed(1),
      unit: '%',
      icon: Activity,
      color: avgDensity > 70 ? 'text-red-400' : avgDensity > 40 ? 'text-amber-400' : 'text-emerald-400',
      bgColor: avgDensity > 70 ? 'bg-red-500/10' : avgDensity > 40 ? 'bg-amber-500/10' : 'bg-emerald-500/10',
    },
    {
      title: 'Violations',
      value: additionalStats.totalViolations,
      icon: AlertTriangle,
      color: 'text-red-400',
      bgColor: 'bg-red-500/10',
    },
    {
      title: 'Agent Cycles',
      value: agentLoopCount,
      icon: TrendingUp,
      color: 'text-purple-400',
      bgColor: 'bg-purple-500/10',
    },
  ];

  const performanceCards: StatCard[] = [
    {
      title: 'Throughput',
      value: throughput,
      unit: '/hr',
      icon: Gauge,
      color: 'text-cyan-400',
      bgColor: 'bg-cyan-500/10',
    },
    {
      title: 'Congestion Points',
      value: congestionPoints,
      icon: Target,
      color: congestionPoints > 5 ? 'text-red-400' : 'text-emerald-400',
      bgColor: congestionPoints > 5 ? 'bg-red-500/10' : 'bg-emerald-500/10',
    },
    {
      title: 'Agent Latency',
      value: avgDecisionLatency.toFixed(0),
      unit: 'ms',
      icon: Zap,
      color: avgDecisionLatency > 100 ? 'text-amber-400' : 'text-emerald-400',
      bgColor: avgDecisionLatency > 100 ? 'bg-amber-500/10' : 'bg-emerald-500/10',
    },
    {
      title: 'FPS',
      value: fps,
      icon: Clock,
      color: fps < 30 ? 'text-red-400' : 'text-emerald-400',
      bgColor: fps < 30 ? 'bg-red-500/10' : 'bg-emerald-500/10',
    },
  ];

  const StatCardComponent: React.FC<{ card: StatCard }> = ({ card }) => {
    const Icon = card.icon;
    return (
      <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl border border-slate-700/50 p-4 hover:border-slate-600/50 transition-all duration-200">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-sm text-slate-400 mb-1">{card.title}</p>
            <div className="flex items-baseline gap-1">
              <span className={`text-2xl font-bold ${card.color}`}>
                {card.value}
              </span>
              {card.unit && (
                <span className="text-sm text-slate-500">{card.unit}</span>
              )}
            </div>
            {card.trend && card.trendValue && (
              <div className={`text-xs mt-1 ${
                card.trend === 'up' ? 'text-emerald-400' : 
                card.trend === 'down' ? 'text-red-400' : 
                'text-slate-400'
              }`}>
                {card.trend === 'up' ? '↑' : card.trend === 'down' ? '↓' : '→'} {card.trendValue}
              </div>
            )}
          </div>
          <div className={`${card.bgColor} p-2.5 rounded-lg`}>
            <Icon className={`w-5 h-5 ${card.color}`} />
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-cyan-500/20 rounded-lg">
            <BarChart3 className="w-5 h-5 text-cyan-400" />
          </div>
          <h3 className="text-lg font-bold text-white">Statistics</h3>
        </div>
        <button
          onClick={handleRefresh}
          disabled={isRefreshing}
          className="p-2 bg-slate-700/50 hover:bg-slate-700 rounded-lg transition-all"
        >
          <RefreshCw className={`w-4 h-4 text-slate-400 ${isRefreshing ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Main Stats Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {statCards.map((card, index) => (
          <StatCardComponent key={index} card={card} />
        ))}
      </div>

      {/* Performance Metrics */}
      <div>
        <h4 className="text-sm font-semibold text-slate-400 mb-3 flex items-center gap-2">
          <Gauge className="w-4 h-4" />
          Performance Metrics
        </h4>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {performanceCards.map((card, index) => (
            <StatCardComponent key={index} card={card} />
          ))}
        </div>
      </div>

      {/* Density Distribution Bar */}
      <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl border border-slate-700/50 p-4">
        <h4 className="text-sm font-semibold text-slate-400 mb-3">Traffic Density Distribution</h4>
        <div className="space-y-2">
          <div className="flex items-center gap-3">
            <span className="text-xs text-slate-500 w-16">Low</span>
            <div className="flex-1 h-3 bg-slate-700/50 rounded-full overflow-hidden">
              <div 
                className="h-full bg-gradient-to-r from-emerald-500 to-emerald-400 rounded-full transition-all duration-500"
                style={{ width: `${Math.max(10, 100 - avgDensity)}%` }}
              ></div>
            </div>
            <span className="text-xs text-slate-400 w-12 text-right">{(100 - avgDensity).toFixed(0)}%</span>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-xs text-slate-500 w-16">Medium</span>
            <div className="flex-1 h-3 bg-slate-700/50 rounded-full overflow-hidden">
              <div 
                className="h-full bg-gradient-to-r from-amber-500 to-amber-400 rounded-full transition-all duration-500"
                style={{ width: `${Math.min(30, avgDensity * 0.5)}%` }}
              ></div>
            </div>
            <span className="text-xs text-slate-400 w-12 text-right">{Math.min(30, avgDensity * 0.5).toFixed(0)}%</span>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-xs text-slate-500 w-16">High</span>
            <div className="flex-1 h-3 bg-slate-700/50 rounded-full overflow-hidden">
              <div 
                className="h-full bg-gradient-to-r from-red-500 to-red-400 rounded-full transition-all duration-500"
                style={{ width: `${Math.min(40, avgDensity * 0.4)}%` }}
              ></div>
            </div>
            <span className="text-xs text-slate-400 w-12 text-right">{Math.min(40, avgDensity * 0.4).toFixed(0)}%</span>
          </div>
        </div>
      </div>
    </div>
  );
};

