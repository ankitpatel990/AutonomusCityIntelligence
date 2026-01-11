/**
 * GandhinagarMap Component
 * 
 * Real geographic map of Gandhinagar, Gujarat using Leaflet and OpenStreetMap
 * Shows real-time traffic data, vehicles, junctions, and incidents
 */

import React, { useEffect, useRef, useState } from 'react';
import { MapContainer, TileLayer, Marker, Popup, Circle, useMap, Polyline } from 'react-leaflet';
import L from 'leaflet';
import { useSystemStore } from '../store/useSystemStore';
import type { Vehicle, Junction, RoadSegment } from '../types/models';
import 'leaflet/dist/leaflet.css';

interface GandhinagarMapProps {
  height?: string;
  showVehicles?: boolean;
  showJunctions?: boolean;
  showRoads?: boolean;
  showTrafficDensity?: boolean;
}

// Gandhinagar GPS coordinates (center of the city)
const GANDHINAGAR_CENTER: [number, number] = [23.2156, 72.6369];
const DEFAULT_ZOOM = 13;

// Fix for default marker icons in Leaflet with Webpack/Vite
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

// Custom icons for different vehicle types
const createVehicleIcon = (type: string, isEmergency: boolean) => {
  const colors = {
    car: '#3b82f6',
    bike: '#a855f7',
    ambulance: '#ef4444',
    bus: '#f59e0b',
    truck: '#22c55e',
  };
  
  const color = isEmergency ? '#ef4444' : colors[type as keyof typeof colors] || '#3b82f6';
  const size = type === 'bike' ? 8 : type === 'bus' || type === 'truck' ? 14 : 10;
  
  return L.divIcon({
    html: `<div style="
      width: ${size}px;
      height: ${size}px;
      background: ${color};
      border: 2px solid white;
      border-radius: 50%;
      box-shadow: 0 0 ${isEmergency ? '10px rgba(239, 68, 68, 0.6)' : '4px rgba(0,0,0,0.3)'};
      ${isEmergency ? 'animation: pulse 1s infinite;' : ''}
    "></div>`,
    className: 'vehicle-marker',
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  });
};

const createJunctionIcon = (signalState?: string) => {
  const color = 
    signalState === 'GREEN' ? '#22c55e' :
    signalState === 'YELLOW' ? '#f59e0b' :
    signalState === 'RED' ? '#ef4444' : '#64748b';
    
  return L.divIcon({
    html: `<div style="
      width: 16px;
      height: 16px;
      background: ${color};
      border: 3px solid white;
      border-radius: 50%;
      box-shadow: 0 0 8px rgba(0,0,0,0.4);
      animation: glow 2s ease-in-out infinite;
    "></div>`,
    className: 'junction-marker',
    iconSize: [16, 16],
    iconAnchor: [8, 8],
  });
};

// Component to update map view dynamically
const MapUpdater: React.FC<{ center: [number, number]; zoom: number }> = ({ center, zoom }) => {
  const map = useMap();
  useEffect(() => {
    map.setView(center, zoom);
  }, [center, zoom, map]);
  return null;
};

// Convert canvas coordinates to GPS (simplified conversion)
const canvasToGPS = (x: number, y: number, canvasWidth = 800, canvasHeight = 600): [number, number] => {
  // Map bounds for Gandhinagar area
  const bounds = {
    north: 23.2500,
    south: 23.1800,
    east: 72.6800,
    west: 72.6000,
  };
  
  const lat = bounds.south + (1 - y / canvasHeight) * (bounds.north - bounds.south);
  const lng = bounds.west + (x / canvasWidth) * (bounds.east - bounds.west);
  
  return [lat, lng];
};

export const GandhinagarMap: React.FC<GandhinagarMapProps> = ({
  height = '600px',
  showVehicles = true,
  showJunctions = true,
  showRoads = true,
  showTrafficDensity = true,
}) => {
  const { vehicles, junctions, roads } = useSystemStore();
  const [mapCenter, setMapCenter] = useState<[number, number]>(GANDHINAGAR_CENTER);
  const [mapZoom, setMapZoom] = useState(DEFAULT_ZOOM);

  // Debug: Log roads when they change
  useEffect(() => {
    if (roads.length > 0) {
      console.log('GandhinagarMap: Roads loaded:', roads.length, roads);
    } else {
      console.log('GandhinagarMap: No roads available');
    }
  }, [roads]);

  // Add custom CSS for animations
  useEffect(() => {
    const style = document.createElement('style');
    style.textContent = `
      @keyframes pulse {
        0%, 100% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.7; transform: scale(1.2); }
      }
      @keyframes glow {
        0%, 100% { box-shadow: 0 0 8px rgba(0,0,0,0.4); }
        50% { box-shadow: 0 0 15px currentColor; }
      }
      .leaflet-container {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
      }
      .vehicle-marker {
        background: transparent;
        border: none;
      }
      .junction-marker {
        background: transparent;
        border: none;
      }
    `;
    document.head.appendChild(style);
    return () => {
      document.head.removeChild(style);
    };
  }, []);

  return (
    <div className="relative w-full" style={{ height }}>
      {/* Map Info Overlay */}
      <div className="absolute top-4 left-4 z-[1000] bg-slate-900/90 backdrop-blur-sm rounded-lg p-3 border border-slate-700/50 shadow-lg">
        <p className="text-xs font-semibold text-cyan-400 mb-2">📍 Gandhinagar, Gujarat</p>
        <div className="space-y-1 text-xs font-mono">
          <p className="text-slate-400">Vehicles: <span className="text-cyan-400">{vehicles.length}</span></p>
          <p className="text-slate-400">Junctions: <span className="text-cyan-400">{junctions.length}</span></p>
          <p className="text-slate-400">Roads: <span className="text-cyan-400">{roads.length}</span></p>
        </div>
      </div>

      {/* Legend */}
      <div className="absolute bottom-4 left-4 z-[1000] bg-slate-900/90 backdrop-blur-sm rounded-lg p-3 border border-slate-700/50 shadow-lg">
        <p className="text-xs text-slate-400 mb-2 font-semibold">Legend</p>
        <div className="space-y-1.5 text-xs">
          {showVehicles && (
            <>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-blue-500 border-2 border-white"></div>
                <span className="text-slate-400">Car</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-purple-500 border-2 border-white"></div>
                <span className="text-slate-400">Bike</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-red-500 border-2 border-white"></div>
                <span className="text-slate-400">Emergency</span>
              </div>
            </>
          )}
          {showJunctions && (
            <div className="flex items-center gap-2 pt-1 border-t border-slate-700 mt-1">
              <div className="w-3 h-3 rounded-full bg-emerald-500 border-2 border-white"></div>
              <span className="text-slate-400">Junction/Signal</span>
            </div>
          )}
        </div>
      </div>

      {/* Map Container */}
      <MapContainer
        center={GANDHINAGAR_CENTER}
        zoom={DEFAULT_ZOOM}
        style={{ height: '100%', width: '100%', borderRadius: '12px' }}
        className="shadow-2xl shadow-cyan-500/10 border border-slate-700/50"
      >
        <MapUpdater center={mapCenter} zoom={mapZoom} />
        
        {/* Base Map Tile Layer */}
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {/* Dark mode alternative (commented out) */}
        {/* <TileLayer
          attribution='&copy; <a href="https://stadiamaps.com/">Stadia Maps</a>'
          url="https://tiles.stadiamaps.com/tiles/alidade_smooth_dark/{z}/{x}/{y}{r}.png"
        /> */}

        {/* Render Roads with Traffic Density */}
        {showRoads && roads.length > 0 && roads.map((road: any) => {
          // Use GPS coordinates if available, otherwise convert from canvas
          let start: [number, number] = [0, 0];
          let end: [number, number] = [0, 0];
          
          // Priority 1: Use startLat/startLon and endLat/endLon if available
          if (road.startLat && road.startLon && road.endLat && road.endLon) {
            start = [road.startLat, road.startLon];
            end = [road.endLat, road.endLon];
          }
          // Priority 2: Use geometry.startPos/endPos (backend stores lon as x, lat as y)
          else if (road.geometry?.startPos && road.geometry?.endPos) {
            // Check if coordinates are GPS (lon ~72, lat ~23) or canvas pixels
            if (road.geometry.startPos.x > 70 && road.geometry.startPos.x < 80 && 
                road.geometry.startPos.y > 20 && road.geometry.startPos.y < 30) {
              // GPS coordinates: x is lon, y is lat
              start = [road.geometry.startPos.y, road.geometry.startPos.x];
              end = [road.geometry.endPos.y, road.geometry.endPos.x];
            } else {
              // Canvas coordinates, convert to GPS
              start = canvasToGPS(road.geometry.startPos.x, road.geometry.startPos.y);
              end = canvasToGPS(road.geometry.endPos.x, road.geometry.endPos.y);
            }
          }
          
          // Skip if coordinates are invalid
          if (!start || !end || start[0] === 0 || end[0] === 0) {
            console.warn('Invalid road coordinates:', road.id, road);
            return null;
          }
          
          const densityColors: Record<string, string> = {
            LOW: '#22c55e',
            MEDIUM: '#f59e0b',
            HIGH: '#ef4444',
          };
          
          const density = road.traffic?.density || 'LOW';
          
          const roadColor = showTrafficDensity ? (densityColors[density] || '#475569') : '#475569';
          
          // Debug: Log first road coordinates
          if (road.id === roads[0]?.id) {
            console.log('First road coordinates:', {
              id: road.id,
              start,
              end,
              startLat: road.startLat,
              startLon: road.startLon,
              endLat: road.endLat,
              endLon: road.endLon,
            });
          }
          
          return (
            <Polyline
              key={road.id}
              positions={[start, end]}
              pathOptions={{
                color: roadColor,
                weight: 10,
                opacity: 1.0,
                lineCap: 'round',
                lineJoin: 'round',
              }}
            >
              <Popup>
                <div className="text-sm">
                  <p className="font-bold text-slate-900">{road.name || `Road ${road.id}`}</p>
                  <p className="text-xs text-slate-600">
                    Density: <span className="font-semibold">{density}</span>
                  </p>
                  <p className="text-xs text-slate-600">
                    Speed: {road.traffic?.avgSpeed?.toFixed(1) || 0} km/h
                  </p>
                  <p className="text-xs text-slate-600">
                    Vehicles: {road.traffic?.vehicleCount || 0}
                  </p>
                </div>
              </Popup>
            </Polyline>
          );
        })}

        {/* Render Junctions */}
        {showJunctions && junctions.map((junction) => {
          // Use GPS coordinates if available, otherwise convert from canvas
          const position: [number, number] = (junction.lat && junction.lon)
            ? [junction.lat, junction.lon]
            : canvasToGPS(junction.position.x, junction.position.y);
          
          // Get main signal state (from north direction or first available)
          const mainSignal = junction.signals?.north?.current || 
                            junction.signals?.east?.current ||
                            junction.signals?.south?.current ||
                            junction.signalState ||  // fallback for hardcoded junctions
                            junction.signals?.west?.current;
          
          return (
            <Marker
              key={junction.id}
              position={position}
              icon={createJunctionIcon(mainSignal)}
            >
              <Popup>
                <div className="text-sm">
                  <p className="font-bold text-slate-900">{junction.name || `Junction ${junction.id}`}</p>
                  <p className="text-xs text-slate-500">{junction.id}</p>
                  <div className="mt-2 space-y-1 text-xs">
                    {junction.signals && Object.entries(junction.signals).map(([dir, signal]) => (
                      signal && (
                        <div key={dir} className="flex items-center justify-between">
                          <span className="text-slate-600 capitalize">{dir}:</span>
                          <span className={`font-semibold px-2 py-0.5 rounded ${
                            signal.current === 'GREEN' ? 'bg-emerald-100 text-emerald-700' :
                            signal.current === 'YELLOW' ? 'bg-amber-100 text-amber-700' :
                            'bg-red-100 text-red-700'
                          }`}>
                            {signal.current}
                          </span>
                        </div>
                      )
                    ))}
                  </div>
                  {junction.metrics && (
                    <div className="mt-2 pt-2 border-t border-slate-200 text-xs">
                      <p className="text-slate-600">Vehicles: {junction.metrics.vehicleCount || 0}</p>
                      <p className="text-slate-600">Wait Time: {(junction.metrics.avgWaitTime || 0).toFixed(1)}s</p>
                    </div>
                  )}
                </div>
              </Popup>
            </Marker>
          );
        })}

        {/* Render Vehicles */}
        {showVehicles && vehicles.map((vehicle) => {
          // Use GPS coordinates if available, otherwise convert from canvas
          const position: [number, number] = (vehicle.lat && vehicle.lon)
            ? [vehicle.lat, vehicle.lon]
            : canvasToGPS(vehicle.position.x, vehicle.position.y);
          
          return (
            <Marker
              key={vehicle.id}
              position={position}
              icon={createVehicleIcon(vehicle.type, vehicle.isEmergency || false)}
            >
              <Popup>
                <div className="text-sm">
                  <p className="font-bold text-slate-900">
                    {vehicle.type.charAt(0).toUpperCase() + vehicle.type.slice(1)} {vehicle.id}
                  </p>
                  <div className="mt-2 space-y-1 text-xs text-slate-600">
                    <p>Speed: <span className="font-semibold">{vehicle.speed.toFixed(1)} km/h</span></p>
                    <p>Heading: <span className="font-semibold">{vehicle.heading.toFixed(0)}°</span></p>
                    {vehicle.currentRoad && (
                      <p>Road: <span className="font-semibold">{vehicle.currentRoad}</span></p>
                    )}
                    {vehicle.route && (
                      <p>Route: {vehicle.route.start} → {vehicle.route.end}</p>
                    )}
                    {vehicle.isEmergency && (
                      <p className="text-red-600 font-semibold">🚨 EMERGENCY VEHICLE</p>
                    )}
                  </div>
                </div>
              </Popup>
            </Marker>
          );
        })}

        {/* Add traffic density circles for high congestion areas */}
        {showTrafficDensity && roads
          .filter((road: any) => road.traffic?.density === 'HIGH')
          .map((road: any, index: number) => {
            // Use GPS coordinates if available
            const center: [number, number] = (road.startLat && road.startLon && road.endLat && road.endLon)
              ? [(road.startLat + road.endLat) / 2, (road.startLon + road.endLon) / 2]
              : canvasToGPS(
                  (road.geometry.startPos.x + road.geometry.endPos.x) / 2,
                  (road.geometry.startPos.y + road.geometry.endPos.y) / 2
                );
            
            return (
              <Circle
                key={`density-${road.id}-${index}`}
                center={center}
                radius={100}
                pathOptions={{
                  color: '#ef4444',
                  fillColor: '#ef4444',
                  fillOpacity: 0.2,
                  weight: 2,
                }}
              >
                <Popup>
                  <div className="text-sm">
                    <p className="font-bold text-red-600">⚠️ High Congestion</p>
                    <p className="text-xs text-slate-600 mt-1">{road.name}</p>
                  </div>
                </Popup>
              </Circle>
            );
          })
        }
      </MapContainer>
    </div>
  );
};

