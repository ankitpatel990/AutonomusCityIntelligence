/**
 * Dashboard Page
 * 
 * Main dashboard integrating all components: CityMap, Controls, Statistics, Safety
 */

import React, { useEffect, useState } from 'react';
import { CityMap } from '../components/CityMap';
import { ControlPanel } from '../components/ControlPanel';
import { StatisticsPanel } from '../components/StatisticsPanel';
import { EmergencySafetyPanel } from '../components/EmergencySafetyPanel';
import { ViolationsPanel } from '../components/ViolationsPanel';
import { useSystemStore } from '../store/useSystemStore';
import { useDemoMode } from '../hooks/useDemoMode';
import { api } from '../services/api';

export const Dashboard: React.FC = () => {
  const { isRunning } = useSystemStore();
  const [demoMode, setDemoMode] = useState(false);

  // Use demo mode when backend is not available
  useDemoMode({ enabled: demoMode });

  // Check backend availability and fetch initial data
  useEffect(() => {
    const fetchInitialData = async () => {
      try {
        await api.healthCheck();
        
        const [state, vehicles, junctions, roads] = await Promise.all([
          api.getSystemState(),
          api.getVehicles(),
          api.getJunctions(),
          api.getRoads(),
        ]);

        useSystemStore.getState().updateVehicles(vehicles);
        useSystemStore.getState().updateJunctions(junctions);
        useSystemStore.getState().updateRoads(roads);
        useSystemStore.getState().updatePerformance({
          vehicleCount: state.performance.vehicleCount,
          avgDensity: state.performance.avgDensity,
          congestionPoints: state.performance.congestionPoints,
          throughput: state.performance.throughput,
          fps: state.performance.fps,
        });
      } catch (error) {
        console.error('Backend not available, enabling demo mode:', error);
        setDemoMode(true);
      }
    };

    fetchInitialData();
  }, []);

  return (
    <div className="p-6 space-y-6 min-h-full">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Traffic Dashboard</h1>
          <p className="text-sm text-slate-400 mt-1">
            Real-time monitoring and control of the city traffic system
          </p>
        </div>
        <div className="flex items-center gap-4">
          {demoMode && (
            <div className="px-3 py-1.5 rounded-lg bg-amber-500/20 text-amber-400 border border-amber-500/30 text-xs font-medium">
              🎬 Demo Mode
            </div>
          )}
          <div className={`px-4 py-2 rounded-xl font-medium text-sm flex items-center gap-2 ${
            isRunning 
              ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' 
              : 'bg-slate-700/50 text-slate-400 border border-slate-600/30'
          }`}>
            <div className={`w-2 h-2 rounded-full ${isRunning ? 'bg-emerald-400 animate-pulse' : 'bg-slate-500'}`}></div>
            {isRunning ? 'System Active' : 'System Idle'}
          </div>
        </div>
      </div>

      {/* Statistics Row */}
      <StatisticsPanel />

      {/* Main Content Grid */}
      <div className="grid grid-cols-12 gap-6">
        {/* City Map - Main Area */}
        <div className="col-span-12 xl:col-span-8">
          <div className="bg-slate-800/50 backdrop-blur-sm rounded-2xl border border-slate-700/50 p-5">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-bold text-white">City Traffic Visualization</h2>
              <div className="flex items-center gap-2 text-xs text-slate-400">
                <span className="flex items-center gap-1">
                  <div className="w-2 h-2 rounded-full bg-emerald-400"></div>
                  Live
                </span>
                <span>•</span>
                <span>Gandhinagar Digital Twin</span>
              </div>
            </div>
            <CityMap width={750} height={550} showGrid={true} showLabels={true} />
          </div>
        </div>

        {/* Right Sidebar - Controls & Safety */}
        <div className="col-span-12 xl:col-span-4 space-y-6">
          {/* Control Panel */}
          <ControlPanel />

          {/* Emergency & Safety */}
          <EmergencySafetyPanel />
        </div>
      </div>

      {/* Bottom Row - Violations */}
      <div className="grid grid-cols-12 gap-6">
        <div className="col-span-12">
          <ViolationsPanel />
        </div>
      </div>
    </div>
  );
};

