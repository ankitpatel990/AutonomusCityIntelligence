/**
 * Mock Data for Digital Twin Visualization
 * 
 * Provides demo data for visualization when backend is not available
 */

import type { Vehicle, Junction, RoadSegment, SignalState } from '../types/models';

// Helper function to create signal state
const createSignalState = (current: 'RED' | 'GREEN' | 'YELLOW', duration: number): SignalState => ({
  current,
  duration,
  lastChange: Date.now() / 1000,
  timeSinceGreen: current === 'GREEN' ? 0 : duration,
});

// Mock Junctions - 3x3 Grid Layout
export const mockJunctions: Junction[] = [
  {
    id: 'J-001',
    position: { x: 150, y: 150 },
    signals: {
      north: createSignalState('RED', 30),
      south: createSignalState('RED', 30),
      east: createSignalState('GREEN', 25),
      west: createSignalState('GREEN', 25),
    },
    connectedRoads: { north: 'R-001', south: 'R-004', east: 'R-007', west: null },
    metrics: { vehicleCount: 12, avgWaitTime: 15, density: 35 },
    lastSignalChange: Date.now() / 1000,
  },
  {
    id: 'J-002',
    position: { x: 375, y: 150 },
    signals: {
      north: createSignalState('GREEN', 20),
      south: createSignalState('GREEN', 20),
      east: createSignalState('RED', 35),
      west: createSignalState('RED', 35),
    },
    connectedRoads: { north: 'R-002', south: 'R-005', east: 'R-008', west: 'R-007' },
    metrics: { vehicleCount: 8, avgWaitTime: 12, density: 28 },
    lastSignalChange: Date.now() / 1000,
  },
  {
    id: 'J-003',
    position: { x: 600, y: 150 },
    signals: {
      north: createSignalState('RED', 30),
      south: createSignalState('RED', 30),
      east: createSignalState('GREEN', 25),
      west: createSignalState('GREEN', 25),
    },
    connectedRoads: { north: 'R-003', south: 'R-006', east: null, west: 'R-008' },
    metrics: { vehicleCount: 15, avgWaitTime: 18, density: 45 },
    lastSignalChange: Date.now() / 1000,
  },
  {
    id: 'J-004',
    position: { x: 150, y: 300 },
    signals: {
      north: createSignalState('GREEN', 25),
      south: createSignalState('GREEN', 25),
      east: createSignalState('RED', 30),
      west: createSignalState('RED', 30),
    },
    connectedRoads: { north: 'R-004', south: 'R-010', east: 'R-009', west: null },
    metrics: { vehicleCount: 10, avgWaitTime: 14, density: 32 },
    lastSignalChange: Date.now() / 1000,
  },
  {
    id: 'J-005',
    position: { x: 375, y: 300 },
    signals: {
      north: createSignalState('RED', 35),
      south: createSignalState('RED', 35),
      east: createSignalState('GREEN', 20),
      west: createSignalState('GREEN', 20),
    },
    connectedRoads: { north: 'R-005', south: 'R-011', east: 'R-012', west: 'R-009' },
    metrics: { vehicleCount: 20, avgWaitTime: 22, density: 55 },
    lastSignalChange: Date.now() / 1000,
  },
  {
    id: 'J-006',
    position: { x: 600, y: 300 },
    signals: {
      north: createSignalState('GREEN', 25),
      south: createSignalState('GREEN', 25),
      east: createSignalState('RED', 30),
      west: createSignalState('RED', 30),
    },
    connectedRoads: { north: 'R-006', south: 'R-013', east: null, west: 'R-012' },
    metrics: { vehicleCount: 6, avgWaitTime: 10, density: 22 },
    lastSignalChange: Date.now() / 1000,
  },
  {
    id: 'J-007',
    position: { x: 150, y: 450 },
    signals: {
      north: createSignalState('RED', 30),
      south: createSignalState('RED', 30),
      east: createSignalState('GREEN', 25),
      west: createSignalState('GREEN', 25),
    },
    connectedRoads: { north: 'R-010', south: null, east: 'R-014', west: null },
    metrics: { vehicleCount: 8, avgWaitTime: 11, density: 26 },
    lastSignalChange: Date.now() / 1000,
  },
  {
    id: 'J-008',
    position: { x: 375, y: 450 },
    signals: {
      north: createSignalState('GREEN', 20),
      south: createSignalState('GREEN', 20),
      east: createSignalState('RED', 35),
      west: createSignalState('RED', 35),
    },
    connectedRoads: { north: 'R-011', south: null, east: 'R-015', west: 'R-014' },
    metrics: { vehicleCount: 14, avgWaitTime: 16, density: 42 },
    lastSignalChange: Date.now() / 1000,
  },
  {
    id: 'J-009',
    position: { x: 600, y: 450 },
    signals: {
      north: createSignalState('RED', 30),
      south: createSignalState('RED', 30),
      east: createSignalState('GREEN', 25),
      west: createSignalState('GREEN', 25),
    },
    connectedRoads: { north: 'R-013', south: null, east: null, west: 'R-015' },
    metrics: { vehicleCount: 5, avgWaitTime: 8, density: 18 },
    lastSignalChange: Date.now() / 1000,
  },
];

// Mock Roads connecting junctions
export const mockRoads: RoadSegment[] = [
  // Vertical roads (top to bottom, left column)
  {
    id: 'R-001',
    startJunction: 'entry-N1',
    endJunction: 'J-001',
    geometry: { startPos: { x: 150, y: 50 }, endPos: { x: 150, y: 125 }, length: 75, lanes: 2 },
    traffic: { currentVehicles: [], capacity: 20, density: 'LOW', densityScore: 25, speedLimit: 40 },
    lastUpdate: Date.now() / 1000,
  },
  {
    id: 'R-004',
    startJunction: 'J-001',
    endJunction: 'J-004',
    geometry: { startPos: { x: 150, y: 175 }, endPos: { x: 150, y: 275 }, length: 100, lanes: 2 },
    traffic: { currentVehicles: [], capacity: 20, density: 'MEDIUM', densityScore: 45, speedLimit: 40 },
    lastUpdate: Date.now() / 1000,
  },
  {
    id: 'R-010',
    startJunction: 'J-004',
    endJunction: 'J-007',
    geometry: { startPos: { x: 150, y: 325 }, endPos: { x: 150, y: 425 }, length: 100, lanes: 2 },
    traffic: { currentVehicles: [], capacity: 20, density: 'LOW', densityScore: 22, speedLimit: 40 },
    lastUpdate: Date.now() / 1000,
  },
  // Vertical roads (center column)
  {
    id: 'R-002',
    startJunction: 'entry-N2',
    endJunction: 'J-002',
    geometry: { startPos: { x: 375, y: 50 }, endPos: { x: 375, y: 125 }, length: 75, lanes: 2 },
    traffic: { currentVehicles: [], capacity: 20, density: 'LOW', densityScore: 30, speedLimit: 40 },
    lastUpdate: Date.now() / 1000,
  },
  {
    id: 'R-005',
    startJunction: 'J-002',
    endJunction: 'J-005',
    geometry: { startPos: { x: 375, y: 175 }, endPos: { x: 375, y: 275 }, length: 100, lanes: 2 },
    traffic: { currentVehicles: [], capacity: 20, density: 'HIGH', densityScore: 72, speedLimit: 40 },
    lastUpdate: Date.now() / 1000,
  },
  {
    id: 'R-011',
    startJunction: 'J-005',
    endJunction: 'J-008',
    geometry: { startPos: { x: 375, y: 325 }, endPos: { x: 375, y: 425 }, length: 100, lanes: 2 },
    traffic: { currentVehicles: [], capacity: 20, density: 'MEDIUM', densityScore: 48, speedLimit: 40 },
    lastUpdate: Date.now() / 1000,
  },
  // Vertical roads (right column)
  {
    id: 'R-003',
    startJunction: 'entry-N3',
    endJunction: 'J-003',
    geometry: { startPos: { x: 600, y: 50 }, endPos: { x: 600, y: 125 }, length: 75, lanes: 2 },
    traffic: { currentVehicles: [], capacity: 20, density: 'LOW', densityScore: 18, speedLimit: 40 },
    lastUpdate: Date.now() / 1000,
  },
  {
    id: 'R-006',
    startJunction: 'J-003',
    endJunction: 'J-006',
    geometry: { startPos: { x: 600, y: 175 }, endPos: { x: 600, y: 275 }, length: 100, lanes: 2 },
    traffic: { currentVehicles: [], capacity: 20, density: 'LOW', densityScore: 25, speedLimit: 40 },
    lastUpdate: Date.now() / 1000,
  },
  {
    id: 'R-013',
    startJunction: 'J-006',
    endJunction: 'J-009',
    geometry: { startPos: { x: 600, y: 325 }, endPos: { x: 600, y: 425 }, length: 100, lanes: 2 },
    traffic: { currentVehicles: [], capacity: 20, density: 'LOW', densityScore: 15, speedLimit: 40 },
    lastUpdate: Date.now() / 1000,
  },
  // Horizontal roads (top row)
  {
    id: 'R-007',
    startJunction: 'J-001',
    endJunction: 'J-002',
    geometry: { startPos: { x: 175, y: 150 }, endPos: { x: 350, y: 150 }, length: 175, lanes: 2 },
    traffic: { currentVehicles: [], capacity: 25, density: 'MEDIUM', densityScore: 55, speedLimit: 50 },
    lastUpdate: Date.now() / 1000,
  },
  {
    id: 'R-008',
    startJunction: 'J-002',
    endJunction: 'J-003',
    geometry: { startPos: { x: 400, y: 150 }, endPos: { x: 575, y: 150 }, length: 175, lanes: 2 },
    traffic: { currentVehicles: [], capacity: 25, density: 'LOW', densityScore: 32, speedLimit: 50 },
    lastUpdate: Date.now() / 1000,
  },
  // Horizontal roads (middle row)
  {
    id: 'R-009',
    startJunction: 'J-004',
    endJunction: 'J-005',
    geometry: { startPos: { x: 175, y: 300 }, endPos: { x: 350, y: 300 }, length: 175, lanes: 2 },
    traffic: { currentVehicles: [], capacity: 25, density: 'HIGH', densityScore: 68, speedLimit: 50 },
    lastUpdate: Date.now() / 1000,
  },
  {
    id: 'R-012',
    startJunction: 'J-005',
    endJunction: 'J-006',
    geometry: { startPos: { x: 400, y: 300 }, endPos: { x: 575, y: 300 }, length: 175, lanes: 2 },
    traffic: { currentVehicles: [], capacity: 25, density: 'MEDIUM', densityScore: 42, speedLimit: 50 },
    lastUpdate: Date.now() / 1000,
  },
  // Horizontal roads (bottom row)
  {
    id: 'R-014',
    startJunction: 'J-007',
    endJunction: 'J-008',
    geometry: { startPos: { x: 175, y: 450 }, endPos: { x: 350, y: 450 }, length: 175, lanes: 2 },
    traffic: { currentVehicles: [], capacity: 25, density: 'LOW', densityScore: 28, speedLimit: 50 },
    lastUpdate: Date.now() / 1000,
  },
  {
    id: 'R-015',
    startJunction: 'J-008',
    endJunction: 'J-009',
    geometry: { startPos: { x: 400, y: 450 }, endPos: { x: 575, y: 450 }, length: 175, lanes: 2 },
    traffic: { currentVehicles: [], capacity: 25, density: 'LOW', densityScore: 20, speedLimit: 50 },
    lastUpdate: Date.now() / 1000,
  },
];

// Generate random mock vehicles
export function generateMockVehicles(count: number): Vehicle[] {
  const types: Array<'car' | 'bike' | 'ambulance'> = ['car', 'car', 'car', 'car', 'car', 'car', 'car', 'bike', 'bike', 'ambulance'];
  const vehicles: Vehicle[] = [];
  
  for (let i = 0; i < count; i++) {
    const type = types[Math.floor(Math.random() * types.length)];
    const road = mockRoads[Math.floor(Math.random() * mockRoads.length)];
    const progress = Math.random();
    
    const x = road.geometry.startPos.x + (road.geometry.endPos.x - road.geometry.startPos.x) * progress;
    const y = road.geometry.startPos.y + (road.geometry.endPos.y - road.geometry.startPos.y) * progress;
    
    const heading = Math.atan2(
      road.geometry.endPos.y - road.geometry.startPos.y,
      road.geometry.endPos.x - road.geometry.startPos.x
    ) * (180 / Math.PI);
    
    vehicles.push({
      id: `V-${String(i + 1).padStart(3, '0')}`,
      numberPlate: `GJ-01-${String.fromCharCode(65 + Math.floor(Math.random() * 26))}${String.fromCharCode(65 + Math.floor(Math.random() * 26))}-${String(Math.floor(Math.random() * 10000)).padStart(4, '0')}`,
      type,
      position: { x, y },
      speed: 20 + Math.random() * 30,
      acceleration: 0,
      heading,
      currentRoad: road.id,
      currentJunction: null,
      destination: 'exit',
      path: [],
      pathIndex: 0,
      isEmergency: type === 'ambulance',
      isViolating: false,
      waitingTime: 0,
      spawnTime: Date.now() / 1000,
      lastUpdate: Date.now() / 1000,
    });
  }
  
  return vehicles;
}

// Function to animate mock vehicles
export function animateMockVehicles(vehicles: Vehicle[]): Vehicle[] {
  return vehicles.map(vehicle => {
    const road = mockRoads.find(r => r.id === vehicle.currentRoad);
    if (!road) return vehicle;
    
    const headingRad = (vehicle.heading * Math.PI) / 180;
    const speed = vehicle.speed / 100; // Scale down for pixel movement
    
    let newX = vehicle.position.x + Math.cos(headingRad) * speed;
    let newY = vehicle.position.y + Math.sin(headingRad) * speed;
    
    // Check if vehicle has passed the end of the road
    const roadEndX = road.geometry.endPos.x;
    const roadEndY = road.geometry.endPos.y;
    
    // Simple boundary reset
    if (newX < 50 || newX > 700 || newY < 50 || newY > 550) {
      // Respawn at a random road start
      const newRoad = mockRoads[Math.floor(Math.random() * mockRoads.length)];
      newX = newRoad.geometry.startPos.x;
      newY = newRoad.geometry.startPos.y;
      
      const newHeading = Math.atan2(
        newRoad.geometry.endPos.y - newRoad.geometry.startPos.y,
        newRoad.geometry.endPos.x - newRoad.geometry.startPos.x
      ) * (180 / Math.PI);
      
      return {
        ...vehicle,
        position: { x: newX, y: newY },
        heading: newHeading,
        currentRoad: newRoad.id,
        speed: 20 + Math.random() * 30,
      };
    }
    
    return {
      ...vehicle,
      position: { x: newX, y: newY },
      lastUpdate: Date.now() / 1000,
    };
  });
}

// Export initial mock vehicles
export const mockVehicles = generateMockVehicles(35);

