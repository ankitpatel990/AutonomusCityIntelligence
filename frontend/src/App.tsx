/**
 * Main Application Component
 * 
 * Autonomous City Traffic Intelligence System
 * Digital Twin Visualization Dashboard
 */

import { useEffect, useState } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { api } from './services/api';
import { setupWebSocketListeners } from './services/websocketIntegration';
import { useSystemStore } from './store/useSystemStore';
import { Navbar } from './components/Navbar';
import { Sidebar } from './components/Sidebar';
import { 
  Dashboard, 
  Analytics, 
  SafetyPage, 
  IncidentsPage, 
  ChallansPage, 
  EmergencyPage, 
  SettingsPage 
} from './pages';
import 'leaflet/dist/leaflet.css';
import './App.css';

function App() {
  const [loading, setLoading] = useState(true);
  const [demoMode, setDemoMode] = useState(false);
  
  const { setWsConnected } = useSystemStore();

  // Initialize WebSocket and fetch initial state
  useEffect(() => {
    let cleanupWs: (() => void) | undefined;
    
    const initialize = async () => {
      try {
        // Check backend health
        await api.healthCheck();
        
        // Backend is available - setup WebSocket
        cleanupWs = setupWebSocketListeners();
        setWsConnected(true);
        
        // Fetch initial state
        try {
          const state = await api.getSystemState();
          useSystemStore.getState().setMode(state.mode as any);
          useSystemStore.getState().setAgentStatus(state.agent.status as any);
          useSystemStore.getState().setAgentStrategy(state.agent.strategy as any);
          useSystemStore.getState().updatePerformance({
            vehicleCount: state.performance.vehicleCount,
            avgDensity: state.performance.avgDensity,
            fps: state.performance.fps,
          });
        } catch (stateError) {
          console.warn('Could not fetch initial state:', stateError);
        }
        
        setDemoMode(false);
        setLoading(false);
      } catch (err) {
        console.warn('Backend not available, starting in Demo Mode');
        setDemoMode(true);
        setWsConnected(false);
        setLoading(false);
      }
    };
    
    initialize();
    
    return () => {
      if (cleanupWs) {
        cleanupWs();
      }
    };
  }, [setWsConnected]);

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center">
        <div className="text-center">
          <div className="relative">
            <div className="w-20 h-20 border-4 border-cyan-500/30 rounded-full"></div>
            <div className="absolute inset-0 w-20 h-20 border-4 border-transparent border-t-cyan-500 rounded-full animate-spin"></div>
          </div>
          <p className="text-lg text-slate-400 mt-6">Connecting to Traffic Intelligence System...</p>
          <p className="text-sm text-slate-500 mt-2">Initializing Digital Twin</p>
        </div>
      </div>
    );
  }

  return (
    <BrowserRouter>
      <div className="h-screen flex flex-col bg-slate-900">
        {/* Demo Mode Banner */}
        {demoMode && (
          <div className="bg-gradient-to-r from-amber-500/20 via-amber-500/10 to-amber-500/20 border-b border-amber-500/30 px-4 py-2">
            <div className="flex items-center justify-center gap-3">
              <span className="text-amber-400 text-sm font-medium flex items-center gap-2">
                <span className="w-2 h-2 bg-amber-400 rounded-full animate-pulse"></span>
                🎬 Demo Mode Active
              </span>
              <span className="text-slate-400 text-sm">
                Backend not connected. Showing simulated data.
              </span>
              <button
                onClick={() => window.location.reload()}
                className="text-xs px-3 py-1 bg-amber-500/20 text-amber-400 border border-amber-500/30 rounded hover:bg-amber-500/30 transition-all"
              >
                Retry Connection
              </button>
            </div>
          </div>
        )}
        
        {/* Top Navbar */}
        <Navbar />
        
        <div className="flex-1 flex overflow-hidden">
          {/* Left Sidebar */}
          <Sidebar />
          
          {/* Main Content */}
          <main className="flex-1 overflow-auto bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/map" element={<Dashboard />} />
              <Route path="/vehicles" element={<Dashboard />} />
              <Route path="/safety" element={<SafetyPage />} />
              <Route path="/analytics" element={<Analytics />} />
              <Route path="/incidents" element={<IncidentsPage />} />
              <Route path="/challans" element={<ChallansPage />} />
              <Route path="/emergency" element={<EmergencyPage />} />
              <Route path="/settings" element={<SettingsPage />} />
            </Routes>
          </main>
        </div>
      </div>
    </BrowserRouter>
  );
}

export default App;
