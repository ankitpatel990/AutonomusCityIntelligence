/**
 * Analytics Page
 * 
 * Displays detailed analytics, charts, and historical data using Chart.js
 */

import React, { useState, useEffect, useMemo } from 'react';
import { 
  BarChart3, 
  TrendingUp, 
  Clock, 
  Calendar,
  Activity,
  Zap,
  Target,
  RefreshCw,
  Car,
  AlertTriangle
} from 'lucide-react';
import { 
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js';
import { Line, Bar, Doughnut } from 'react-chartjs-2';
import { useSystemStore } from '../store/useSystemStore';

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

export const Analytics: React.FC = () => {
  const { avgDensity, throughput, vehicleCount, agentLoopCount, violations } = useSystemStore();
  const [timeRange, setTimeRange] = useState<'1h' | '6h' | '24h'>('1h');
  const [isLoading, setIsLoading] = useState(false);

  // Simulated historical data for charts
  const densityHistory = useMemo(() => ({
    '1h': [35, 42, 58, 72, 65, 48, 55, 62, 70, 58, 45, 52],
    '6h': [25, 35, 45, 65, 75, 85, 78, 55, 45, 55, 62, 48],
    '24h': [15, 25, 45, 75, 82, 65, 55, 48, 58, 72, 85, 68, 52, 45, 55, 65, 72, 58, 48, 35, 25, 18, 12, 18],
  }), []);

  const throughputHistory = useMemo(() => ({
    '1h': [820, 850, 780, 720, 750, 880, 920, 890, 850, 830, 860, 900],
    '6h': [750, 820, 890, 780, 720, 650, 720, 850, 920, 880, 840, 870],
    '24h': [450, 520, 650, 780, 850, 920, 880, 820, 750, 850, 920, 880, 750, 680, 720, 850, 920, 880, 820, 720, 550, 450, 380, 420],
  }), []);

  const handleRefresh = () => {
    setIsLoading(true);
    setTimeout(() => setIsLoading(false), 1000);
  };

  // Chart options and data
  const lineChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: false,
      },
      tooltip: {
        backgroundColor: 'rgba(15, 23, 42, 0.9)',
        borderColor: 'rgba(6, 182, 212, 0.3)',
        borderWidth: 1,
        titleColor: '#fff',
        bodyColor: '#94a3b8',
        padding: 12,
        cornerRadius: 8,
      },
    },
    scales: {
      x: {
        grid: {
          color: 'rgba(51, 65, 85, 0.3)',
        },
        ticks: {
          color: '#64748b',
        },
      },
      y: {
        grid: {
          color: 'rgba(51, 65, 85, 0.3)',
        },
        ticks: {
          color: '#64748b',
        },
      },
    },
    interaction: {
      intersect: false,
      mode: 'index' as const,
    },
  };

  const getTimeLabels = (range: '1h' | '6h' | '24h') => {
    if (range === '1h') return ['0m', '5m', '10m', '15m', '20m', '25m', '30m', '35m', '40m', '45m', '50m', '55m'];
    if (range === '6h') return ['0h', '0.5h', '1h', '1.5h', '2h', '2.5h', '3h', '3.5h', '4h', '4.5h', '5h', '5.5h'];
    return Array.from({ length: 24 }, (_, i) => `${i}:00`);
  };

  const densityChartData = {
    labels: getTimeLabels(timeRange),
    datasets: [
      {
        label: 'Traffic Density',
        data: densityHistory[timeRange],
        borderColor: 'rgb(34, 197, 94)',
        backgroundColor: 'rgba(34, 197, 94, 0.1)',
        fill: true,
        tension: 0.4,
        pointRadius: 0,
        pointHoverRadius: 6,
        pointHoverBackgroundColor: 'rgb(34, 197, 94)',
        pointHoverBorderColor: '#fff',
        pointHoverBorderWidth: 2,
      },
    ],
  };

  const throughputChartData = {
    labels: getTimeLabels(timeRange),
    datasets: [
      {
        label: 'Throughput',
        data: throughputHistory[timeRange],
        borderColor: 'rgb(6, 182, 212)',
        backgroundColor: 'rgba(6, 182, 212, 0.1)',
        fill: true,
        tension: 0.4,
        pointRadius: 0,
        pointHoverRadius: 6,
        pointHoverBackgroundColor: 'rgb(6, 182, 212)',
        pointHoverBorderColor: '#fff',
        pointHoverBorderWidth: 2,
      },
    ],
  };

  // Junction performance bar chart
  const junctionData = {
    labels: ['J-001', 'J-002', 'J-003', 'J-004', 'J-005', 'J-006', 'J-007', 'J-008', 'J-009'],
    datasets: [
      {
        label: 'Efficiency %',
        data: [92, 78, 85, 95, 72, 88, 91, 76, 89],
        backgroundColor: [
          'rgba(34, 197, 94, 0.7)',
          'rgba(245, 158, 11, 0.7)',
          'rgba(34, 197, 94, 0.7)',
          'rgba(34, 197, 94, 0.7)',
          'rgba(239, 68, 68, 0.7)',
          'rgba(34, 197, 94, 0.7)',
          'rgba(34, 197, 94, 0.7)',
          'rgba(245, 158, 11, 0.7)',
          'rgba(34, 197, 94, 0.7)',
        ],
        borderRadius: 6,
      },
    ],
  };

  const barChartOptions = {
    ...lineChartOptions,
    plugins: {
      ...lineChartOptions.plugins,
      legend: {
        display: false,
      },
    },
  };

  // Violation types doughnut chart
  const violationData = {
    labels: ['Red Light', 'Speeding', 'Wrong Direction', 'Other'],
    datasets: [
      {
        data: [35, 28, 22, 15],
        backgroundColor: [
          'rgba(239, 68, 68, 0.8)',
          'rgba(245, 158, 11, 0.8)',
          'rgba(168, 85, 247, 0.8)',
          'rgba(100, 116, 139, 0.8)',
        ],
        borderColor: [
          'rgb(239, 68, 68)',
          'rgb(245, 158, 11)',
          'rgb(168, 85, 247)',
          'rgb(100, 116, 139)',
        ],
        borderWidth: 2,
      },
    ],
  };

  const doughnutOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'right' as const,
        labels: {
          color: '#94a3b8',
          padding: 20,
          usePointStyle: true,
          pointStyle: 'circle',
        },
      },
      tooltip: {
        backgroundColor: 'rgba(15, 23, 42, 0.9)',
        borderColor: 'rgba(6, 182, 212, 0.3)',
        borderWidth: 1,
        titleColor: '#fff',
        bodyColor: '#94a3b8',
        padding: 12,
        cornerRadius: 8,
      },
    },
    cutout: '65%',
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
                className={`px-4 py-2 rounded-md text-sm font-medium transition-all ${
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

      {/* Charts Grid - Row 1 */}
      <div className="grid grid-cols-2 gap-6">
        {/* Traffic Density Over Time */}
        <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl border border-slate-700/50 p-5">
          <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
            <Activity className="w-5 h-5 text-emerald-400" />
            Traffic Density Over Time
          </h3>
          <div className="h-64">
            <Line data={densityChartData} options={lineChartOptions} />
          </div>
        </div>

        {/* Throughput Over Time */}
        <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl border border-slate-700/50 p-5">
          <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-cyan-400" />
            Throughput Over Time
          </h3>
          <div className="h-64">
            <Line data={throughputChartData} options={lineChartOptions} />
          </div>
        </div>
      </div>

      {/* Charts Grid - Row 2 */}
      <div className="grid grid-cols-3 gap-6">
        {/* Junction Performance */}
        <div className="col-span-2 bg-slate-800/50 backdrop-blur-sm rounded-xl border border-slate-700/50 p-5">
          <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
            <Target className="w-5 h-5 text-cyan-400" />
            Junction Efficiency
          </h3>
          <div className="h-64">
            <Bar data={junctionData} options={barChartOptions} />
          </div>
        </div>

        {/* Violation Types */}
        <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl border border-slate-700/50 p-5">
          <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-amber-400" />
            Violation Types
          </h3>
          <div className="h-64">
            <Doughnut data={violationData} options={doughnutOptions} />
          </div>
        </div>
      </div>

      {/* RL Agent Performance */}
      <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl border border-slate-700/50 p-5">
        <h3 className="text-lg font-bold text-white mb-6 flex items-center gap-2">
          <Zap className="w-5 h-5 text-purple-400" />
          RL Agent Performance
        </h3>
        <div className="grid grid-cols-5 gap-6">
          <div className="text-center p-4 bg-slate-900/50 rounded-xl">
            <p className="text-3xl font-bold text-purple-400">{agentLoopCount}</p>
            <p className="text-sm text-slate-400 mt-2">Decision Cycles</p>
          </div>
          <div className="text-center p-4 bg-slate-900/50 rounded-xl">
            <p className="text-3xl font-bold text-cyan-400">1.8ms</p>
            <p className="text-sm text-slate-400 mt-2">Avg Latency</p>
          </div>
          <div className="text-center p-4 bg-slate-900/50 rounded-xl">
            <p className="text-3xl font-bold text-emerald-400">32%</p>
            <p className="text-sm text-slate-400 mt-2">Wait Time Reduction</p>
          </div>
          <div className="text-center p-4 bg-slate-900/50 rounded-xl">
            <p className="text-3xl font-bold text-amber-400">0</p>
            <p className="text-sm text-slate-400 mt-2">Signal Conflicts</p>
          </div>
          <div className="text-center p-4 bg-slate-900/50 rounded-xl">
            <p className="text-3xl font-bold text-blue-400">99.9%</p>
            <p className="text-sm text-slate-400 mt-2">Uptime</p>
          </div>
        </div>
      </div>

      {/* Real-time Stats */}
      <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl border border-slate-700/50 p-5">
        <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
          <Car className="w-5 h-5 text-blue-400" />
          Real-time Traffic Stats
        </h3>
        <div className="grid grid-cols-4 gap-4">
          <div className="bg-slate-900/50 rounded-lg p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-slate-400">Active Vehicles</span>
              <Car className="w-4 h-4 text-blue-400" />
            </div>
            <p className="text-2xl font-bold text-blue-400">{vehicleCount}</p>
            <div className="mt-2 h-1 bg-slate-700 rounded-full overflow-hidden">
              <div className="h-full bg-blue-400 rounded-full" style={{ width: `${Math.min(vehicleCount, 100)}%` }}></div>
            </div>
          </div>
          <div className="bg-slate-900/50 rounded-lg p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-slate-400">Current Density</span>
              <Activity className="w-4 h-4 text-emerald-400" />
            </div>
            <p className="text-2xl font-bold text-emerald-400">{avgDensity.toFixed(1)}%</p>
            <div className="mt-2 h-1 bg-slate-700 rounded-full overflow-hidden">
              <div 
                className={`h-full rounded-full ${avgDensity > 70 ? 'bg-red-400' : avgDensity > 40 ? 'bg-amber-400' : 'bg-emerald-400'}`} 
                style={{ width: `${avgDensity}%` }}
              ></div>
            </div>
          </div>
          <div className="bg-slate-900/50 rounded-lg p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-slate-400">Violations Today</span>
              <AlertTriangle className="w-4 h-4 text-red-400" />
            </div>
            <p className="text-2xl font-bold text-red-400">{violations.length}</p>
            <div className="mt-2 h-1 bg-slate-700 rounded-full overflow-hidden">
              <div className="h-full bg-red-400 rounded-full" style={{ width: `${Math.min(violations.length * 2, 100)}%` }}></div>
            </div>
          </div>
          <div className="bg-slate-900/50 rounded-lg p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-slate-400">Agent Cycles</span>
              <Zap className="w-4 h-4 text-purple-400" />
            </div>
            <p className="text-2xl font-bold text-purple-400">{agentLoopCount}</p>
            <div className="mt-2 h-1 bg-slate-700 rounded-full overflow-hidden">
              <div className="h-full bg-purple-400 rounded-full animate-pulse" style={{ width: '100%' }}></div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
