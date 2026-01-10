/**
 * Demo Mode Hook
 * 
 * Provides animated mock data for demonstration when backend is unavailable
 */

import { useEffect, useRef, useCallback } from 'react';
import { useSystemStore } from '../store/useSystemStore';
import { mockJunctions, mockRoads, mockVehicles, animateMockVehicles } from '../data/mockData';
import type { Vehicle } from '../types/models';

interface UseDemoModeOptions {
  enabled: boolean;
  animationInterval?: number;
}

export function useDemoMode({ enabled, animationInterval = 50 }: UseDemoModeOptions) {
  const vehiclesRef = useRef<Vehicle[]>(mockVehicles);
  const timeRef = useRef<number>(0);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  
  const { 
    updateVehicles, 
    updateJunctions, 
    updateRoads, 
    setIsRunning,
    setSimulationTime,
    updatePerformance,
  } = useSystemStore();

  // Initialize demo data
  const initializeDemoData = useCallback(() => {
    updateJunctions(mockJunctions);
    updateRoads(mockRoads);
    updateVehicles(vehiclesRef.current);
    updatePerformance({
      vehicleCount: vehiclesRef.current.length,
      avgDensity: 42,
      congestionPoints: 2,
      throughput: 850,
      fps: 60,
    });
  }, [updateJunctions, updateRoads, updateVehicles, updatePerformance]);

  // Animation tick
  const tick = useCallback(() => {
    // Animate vehicles
    vehiclesRef.current = animateMockVehicles(vehiclesRef.current);
    updateVehicles(vehiclesRef.current);
    
    // Update simulation time
    timeRef.current += 1;
    setSimulationTime(timeRef.current);
    
    // Randomly update density
    if (timeRef.current % 20 === 0) {
      updatePerformance({
        avgDensity: 35 + Math.random() * 25,
        congestionPoints: Math.floor(Math.random() * 4),
        throughput: 800 + Math.floor(Math.random() * 200),
      });
    }
    
    // Randomly change signals
    if (timeRef.current % 30 === 0) {
      const junctions = useSystemStore.getState().junctions;
      const updatedJunctions = junctions.map(junction => {
        const shouldChange = Math.random() > 0.7;
        if (!shouldChange) return junction;
        
        // Toggle between N-S and E-W green
        const nsGreen = junction.signals.north.current === 'GREEN';
        return {
          ...junction,
          signals: {
            north: { ...junction.signals.north, current: nsGreen ? 'RED' : 'GREEN' as const },
            south: { ...junction.signals.south, current: nsGreen ? 'RED' : 'GREEN' as const },
            east: { ...junction.signals.east, current: nsGreen ? 'GREEN' : 'RED' as const },
            west: { ...junction.signals.west, current: nsGreen ? 'GREEN' : 'RED' as const },
          },
          lastSignalChange: Date.now() / 1000,
        };
      });
      updateJunctions(updatedJunctions);
    }
  }, [updateVehicles, setSimulationTime, updatePerformance, updateJunctions]);

  // Start/stop demo animation
  useEffect(() => {
    if (enabled) {
      initializeDemoData();
      setIsRunning(true);
      
      intervalRef.current = setInterval(tick, animationInterval);
      
      return () => {
        if (intervalRef.current) {
          clearInterval(intervalRef.current);
          intervalRef.current = null;
        }
      };
    }
  }, [enabled, animationInterval, initializeDemoData, tick, setIsRunning]);

  return {
    initializeDemoData,
    isDemo: enabled,
  };
}

