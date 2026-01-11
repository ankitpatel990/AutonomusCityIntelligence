/**
 * CityMap Component
 * 
 * Canvas-based city map rendering with roads, junctions, signals, and vehicles.
 * Implements 60 FPS animation loop for smooth real-time visualization.
 */

import React, { useRef, useEffect, useCallback, useState } from 'react';
import { useSystemStore } from '../store/useSystemStore';
import type { Vehicle, Junction, RoadSegment } from '../types/models';

interface CityMapProps {
  width?: number;
  height?: number;
  showGrid?: boolean;
  showLabels?: boolean;
}

// Color constants
const COLORS = {
  background: '#0f172a',
  grid: '#1e293b',
  gridAccent: '#334155',
  road: '#475569',
  roadMarkings: '#fbbf24',
  junction: '#1e293b',
  junctionBorder: '#64748b',
  vehicleCar: '#3b82f6',
  vehicleBike: '#a855f7',
  vehicleAmbulance: '#ef4444',
  signalRed: '#ef4444',
  signalYellow: '#f59e0b',
  signalGreen: '#22c55e',
  text: '#94a3b8',
  densityLow: 'rgba(34, 197, 94, 0.3)',
  densityMedium: 'rgba(245, 158, 11, 0.3)',
  densityHigh: 'rgba(239, 68, 68, 0.3)',
};

// Map bounds for Gandhinagar area (same as backend)
const GANDHINAGAR_BOUNDS = {
  north: 23.2500,
  south: 23.1800,
  east: 72.6800,
  west: 72.6000,
};

// Convert GPS coordinates to canvas pixel coordinates
const gpsToCanvas = (
  lat: number,
  lon: number,
  canvasWidth: number,
  canvasHeight: number,
  padding: number = 20
): { x: number; y: number } => {
  const latRange = GANDHINAGAR_BOUNDS.north - GANDHINAGAR_BOUNDS.south;
  const lonRange = GANDHINAGAR_BOUNDS.east - GANDHINAGAR_BOUNDS.west;
  const usableWidth = canvasWidth - 2 * padding;
  const usableHeight = canvasHeight - 2 * padding;

  // Normalize to 0-1 range
  const xNormalized = (lon - GANDHINAGAR_BOUNDS.west) / lonRange;
  // Y is inverted because canvas Y increases downward
  const yNormalized = (GANDHINAGAR_BOUNDS.north - lat) / latRange;

  // Scale to canvas with padding
  const x = padding + xNormalized * usableWidth;
  const y = padding + yNormalized * usableHeight;

  return { x: Math.round(x), y: Math.round(y) };
};

export const CityMap: React.FC<CityMapProps> = ({
  width = 800,
  height = 600,
  showGrid = true,
  showLabels = true,
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationRef = useRef<number>();
  const [hoveredJunction, setHoveredJunction] = useState<string | null>(null);
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });

  const { vehicles, junctions, roads } = useSystemStore();

  // Drawing functions
  const drawGrid = useCallback((ctx: CanvasRenderingContext2D) => {
    if (!showGrid) return;

    const gridSize = 50;
    ctx.strokeStyle = COLORS.grid;
    ctx.lineWidth = 0.5;

    // Vertical lines
    for (let x = 0; x <= width; x += gridSize) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, height);
      ctx.stroke();
    }

    // Horizontal lines
    for (let y = 0; y <= height; y += gridSize) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(width, y);
      ctx.stroke();
    }

    // Major grid lines every 200px
    ctx.strokeStyle = COLORS.gridAccent;
    ctx.lineWidth = 1;
    for (let x = 0; x <= width; x += 200) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, height);
      ctx.stroke();
    }
    for (let y = 0; y <= height; y += 200) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(width, y);
      ctx.stroke();
    }
  }, [width, height, showGrid]);

  const drawRoads = useCallback((ctx: CanvasRenderingContext2D, roadData: RoadSegment[]) => {
    roadData.forEach(road => {
      const { startPos, endPos, lanes } = road.geometry;
      
      // Convert GPS coordinates to canvas coordinates if needed
      // Check if coordinates are GPS (lat/lon range) or canvas pixels
      let startX = startPos.x;
      let startY = startPos.y;
      let endX = endPos.x;
      let endY = endPos.y;
      
      // If coordinates look like GPS (lat ~23, lon ~72), convert them
      if (startPos.x > 70 && startPos.x < 80 && startPos.y > 20 && startPos.y < 30) {
        const startCanvas = gpsToCanvas(startPos.y, startPos.x, width, height);
        const endCanvas = gpsToCanvas(endPos.y, endPos.x, width, height);
        startX = startCanvas.x;
        startY = startCanvas.y;
        endX = endCanvas.x;
        endY = endCanvas.y;
      }
      
      const roadWidth = lanes * 12;

      // Road shadow
      ctx.strokeStyle = 'rgba(0, 0, 0, 0.3)';
      ctx.lineWidth = roadWidth + 4;
      ctx.lineCap = 'round';
      ctx.beginPath();
      ctx.moveTo(startX + 2, startY + 2);
      ctx.lineTo(endX + 2, endY + 2);
      ctx.stroke();

      // Road surface
      ctx.strokeStyle = COLORS.road;
      ctx.lineWidth = roadWidth;
      ctx.lineCap = 'round';
      ctx.beginPath();
      ctx.moveTo(startX, startY);
      ctx.lineTo(endX, endY);
      ctx.stroke();

      // Density overlay
      const densityColor = 
        road.traffic.density === 'HIGH' ? COLORS.densityHigh :
        road.traffic.density === 'MEDIUM' ? COLORS.densityMedium :
        COLORS.densityLow;
      
      ctx.strokeStyle = densityColor;
      ctx.lineWidth = roadWidth - 4;
      ctx.beginPath();
      ctx.moveTo(startX, startY);
      ctx.lineTo(endX, endY);
      ctx.stroke();

      // Road markings (dashed center line)
      ctx.strokeStyle = COLORS.roadMarkings;
      ctx.lineWidth = 2;
      ctx.setLineDash([10, 10]);
      ctx.beginPath();
      ctx.moveTo(startX, startY);
      ctx.lineTo(endX, endY);
      ctx.stroke();
      ctx.setLineDash([]);
    });
  }, []);

  const drawJunctions = useCallback((ctx: CanvasRenderingContext2D, junctionData: Junction[]) => {
    junctionData.forEach(junction => {
      let x: number;
      let y: number;
      
      // Convert GPS coordinates to canvas coordinates if needed
      // Priority: use lat/lon fields if available, otherwise check position
      if (junction.lat !== undefined && junction.lon !== undefined) {
        const canvasPos = gpsToCanvas(junction.lat, junction.lon, width, height);
        x = canvasPos.x;
        y = canvasPos.y;
      } else {
        ({ x, y } = junction.position);
        // Check if coordinates look like GPS (lon ~72, lat ~23)
        if (x > 70 && x < 80 && y > 20 && y < 30) {
          // Backend stores lon as x, lat as y, so convert: gpsToCanvas(lat, lon)
          const canvasPos = gpsToCanvas(y, x, width, height);
          x = canvasPos.x;
          y = canvasPos.y;
        }
      }
      
      const isHovered = hoveredJunction === junction.id;
      const radius = isHovered ? 28 : 24;

      // Junction glow effect
      if (isHovered) {
        const gradient = ctx.createRadialGradient(x, y, 0, x, y, radius + 20);
        gradient.addColorStop(0, 'rgba(6, 182, 212, 0.3)');
        gradient.addColorStop(1, 'rgba(6, 182, 212, 0)');
        ctx.fillStyle = gradient;
        ctx.beginPath();
        ctx.arc(x, y, radius + 20, 0, Math.PI * 2);
        ctx.fill();
      }

      // Junction circle
      ctx.fillStyle = COLORS.junction;
      ctx.strokeStyle = isHovered ? '#06b6d4' : COLORS.junctionBorder;
      ctx.lineWidth = isHovered ? 3 : 2;
      ctx.beginPath();
      ctx.arc(x, y, radius, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();

      // Traffic signals
      if (junction.signals) {
        const signalOffset = 35;
        const directions: Array<{ dir: 'north' | 'east' | 'south' | 'west'; offset: { x: number; y: number } }> = [
          { dir: 'north', offset: { x: 0, y: -signalOffset } },
          { dir: 'east', offset: { x: signalOffset, y: 0 } },
          { dir: 'south', offset: { x: 0, y: signalOffset } },
          { dir: 'west', offset: { x: -signalOffset, y: 0 } },
        ];

        directions.forEach(({ dir, offset }) => {
          const signal = junction.signals![dir];
          if (!signal) return;

          const signalX = x + offset.x;
          const signalY = y + offset.y;
          
          const color = 
            signal.current === 'GREEN' ? COLORS.signalGreen :
            signal.current === 'YELLOW' ? COLORS.signalYellow :
            COLORS.signalRed;

          // Signal glow for GREEN
          if (signal.current === 'GREEN') {
            const glow = ctx.createRadialGradient(signalX, signalY, 0, signalX, signalY, 15);
            glow.addColorStop(0, color);
            glow.addColorStop(1, 'rgba(34, 197, 94, 0)');
            ctx.fillStyle = glow;
            ctx.beginPath();
            ctx.arc(signalX, signalY, 15, 0, Math.PI * 2);
            ctx.fill();
          }

          // Signal circle
          ctx.fillStyle = color;
          ctx.beginPath();
          ctx.arc(signalX, signalY, 8, 0, Math.PI * 2);
          ctx.fill();

          // Signal border
          ctx.strokeStyle = 'rgba(255, 255, 255, 0.3)';
          ctx.lineWidth = 1;
          ctx.stroke();
        });
      }

      // Junction ID label
      if (showLabels) {
        ctx.fillStyle = COLORS.text;
        ctx.font = 'bold 10px "JetBrains Mono", monospace';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(junction.id.substring(0, 4), x, y);
      }
    });
  }, [hoveredJunction, showLabels, width, height]);

  const drawVehicles = useCallback((ctx: CanvasRenderingContext2D, vehicleData: Vehicle[]) => {
    vehicleData.forEach(vehicle => {
      let { x, y } = vehicle.position;
      
      // Convert GPS coordinates to canvas coordinates if needed
      if (vehicle.lat && vehicle.lon) {
        const canvasPos = gpsToCanvas(vehicle.lat, vehicle.lon, width, height);
        x = canvasPos.x;
        y = canvasPos.y;
      } else if (x > 70 && x < 80 && y > 20 && y < 30) {
        // Coordinates look like GPS (lon ~72, lat ~23)
        const canvasPos = gpsToCanvas(y, x, width, height);
        x = canvasPos.x;
        y = canvasPos.y;
      }

      ctx.save();
      ctx.translate(x, y);
      ctx.rotate((vehicle.heading * Math.PI) / 180);

      // Vehicle dimensions based on type
      let vWidth = 16;
      let vHeight = 10;
      let color = COLORS.vehicleCar;

      if (vehicle.type === 'bike') {
        vWidth = 12;
        vHeight = 6;
        color = COLORS.vehicleBike;
      } else if (vehicle.type === 'ambulance') {
        vWidth = 20;
        vHeight = 12;
        color = COLORS.vehicleAmbulance;
      }

      // Emergency vehicle glow
      if (vehicle.isEmergency) {
        const glow = ctx.createRadialGradient(0, 0, 0, 0, 0, 30);
        glow.addColorStop(0, 'rgba(239, 68, 68, 0.5)');
        glow.addColorStop(1, 'rgba(239, 68, 68, 0)');
        ctx.fillStyle = glow;
        ctx.beginPath();
        ctx.arc(0, 0, 30, 0, Math.PI * 2);
        ctx.fill();
      }

      // Vehicle shadow
      ctx.fillStyle = 'rgba(0, 0, 0, 0.3)';
      ctx.fillRect(-vWidth / 2 + 2, -vHeight / 2 + 2, vWidth, vHeight);

      // Vehicle body
      ctx.fillStyle = color;
      ctx.fillRect(-vWidth / 2, -vHeight / 2, vWidth, vHeight);

      // Vehicle front indicator
      ctx.fillStyle = 'rgba(255, 255, 255, 0.8)';
      ctx.fillRect(vWidth / 2 - 3, -vHeight / 4, 3, vHeight / 2);

      // Emergency lights animation
      if (vehicle.isEmergency) {
        const flashOn = Math.floor(Date.now() / 200) % 2 === 0;
        ctx.fillStyle = flashOn ? '#ef4444' : '#3b82f6';
        ctx.fillRect(-vWidth / 2, -vHeight / 2 - 2, vWidth, 2);
      }

      ctx.restore();

      // Speed indicator (small line showing direction)
      if (vehicle.speed > 0) {
        const lineLength = Math.min(vehicle.speed / 2, 20);
        const rad = (vehicle.heading * Math.PI) / 180;
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.3)';
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(x, y);
        ctx.lineTo(
          x + Math.cos(rad) * lineLength,
          y + Math.sin(rad) * lineLength
        );
        ctx.stroke();
      }
    });
  }, [width, height]);

  // Main render loop
  const render = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Clear canvas
    ctx.fillStyle = COLORS.background;
    ctx.fillRect(0, 0, width, height);

    // Draw layers
    drawGrid(ctx);
    drawRoads(ctx, roads);
    drawJunctions(ctx, junctions);
    drawVehicles(ctx, vehicles);

    // Continue animation
    animationRef.current = requestAnimationFrame(render);
  }, [width, height, vehicles, junctions, roads, drawGrid, drawRoads, drawJunctions, drawVehicles]);

  // Start animation loop
  useEffect(() => {
    render();
    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [render]);

  // Mouse interaction for junction hover
  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    setMousePos({ x, y });

    // Check if hovering over a junction
    let found = false;
    for (const junction of junctions) {
      let jx: number;
      let jy: number;
      
      // Convert GPS coordinates to canvas coordinates if needed
      if (junction.lat !== undefined && junction.lon !== undefined) {
        const canvasPos = gpsToCanvas(junction.lat, junction.lon, width, height);
        jx = canvasPos.x;
        jy = canvasPos.y;
      } else {
        jx = junction.position.x;
        jy = junction.position.y;
        // Check if coordinates look like GPS (lon ~72, lat ~23)
        if (jx > 70 && jx < 80 && jy > 20 && jy < 30) {
          const canvasPos = gpsToCanvas(jy, jx, width, height);
          jx = canvasPos.x;
          jy = canvasPos.y;
        }
      }
      
      const dx = x - jx;
      const dy = y - jy;
      if (Math.sqrt(dx * dx + dy * dy) < 30) {
        setHoveredJunction(junction.id);
        found = true;
        break;
      }
    }
    if (!found) {
      setHoveredJunction(null);
    }
  }, [junctions, width, height]);

  return (
    <div className="relative" style={{ width: `${width}px`, height: `${height}px` }}>
      <canvas
        ref={canvasRef}
        width={width}
        height={height}
        className="block rounded-xl shadow-2xl shadow-cyan-500/10 border border-slate-700/50"
        style={{ display: 'block' }}
        onMouseMove={handleMouseMove}
        onMouseLeave={() => setHoveredJunction(null)}
      />

      {/* Hover tooltip */}
      {hoveredJunction && (
        <div 
          className="absolute pointer-events-none bg-slate-800/95 backdrop-blur-sm border border-cyan-500/30 rounded-lg px-3 py-2 shadow-lg"
          style={{
            left: mousePos.x + 15,
            top: mousePos.y + 15,
          }}
        >
          <p className="text-cyan-400 font-bold text-sm">Junction {hoveredJunction}</p>
          {junctions.find(j => j.id === hoveredJunction) && (
            <div className="text-xs text-slate-400 mt-1">
              <p>Vehicles: {junctions.find(j => j.id === hoveredJunction)?.metrics?.vehicleCount || 0}</p>
              <p>Wait Time: {(junctions.find(j => j.id === hoveredJunction)?.metrics?.avgWaitTime || 0).toFixed(1)}s</p>
            </div>
          )}
        </div>
      )}

      {/* Legend */}
      <div className="absolute bottom-4 left-4 bg-slate-900/90 backdrop-blur-sm rounded-lg p-3 border border-slate-700/50">
        <p className="text-xs text-slate-400 mb-2 font-semibold">Legend</p>
        <div className="space-y-1 text-xs">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full" style={{ backgroundColor: COLORS.vehicleCar }}></div>
            <span className="text-slate-400">Car</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full" style={{ backgroundColor: COLORS.vehicleBike }}></div>
            <span className="text-slate-400">Bike</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full" style={{ backgroundColor: COLORS.vehicleAmbulance }}></div>
            <span className="text-slate-400">Ambulance</span>
          </div>
        </div>
      </div>

      {/* Stats overlay */}
      <div className="absolute top-4 right-4 bg-slate-900/90 backdrop-blur-sm rounded-lg p-3 border border-slate-700/50">
        <div className="space-y-1 text-xs font-mono">
          <p className="text-slate-400">Vehicles: <span className="text-cyan-400">{vehicles.length}</span></p>
          <p className="text-slate-400">Junctions: <span className="text-cyan-400">{junctions.length}</span></p>
          <p className="text-slate-400">Roads: <span className="text-cyan-400">{roads.length}</span></p>
        </div>
      </div>
    </div>
  );
};

