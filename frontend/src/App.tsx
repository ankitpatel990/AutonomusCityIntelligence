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
import { Dashboard } from './pages/Dashboard';
import { Analytics } from './pages/Analytics';
import { SafetyPage } from './pages/SafetyPage';
import './App.css';

function App() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const { wsConnected } = useSystemStore();

  // Initialize WebSocket and fetch initial state
  useEffect(() => {
    const cleanup = setupWebSocketListeners();
    
    const initialize = async () => {
      try {
        // Check backend health
        await api.healthCheck();
        
        // Fetch initial state
        const state = await api.getSystemState();
        useSystemStore.getState().setMode(state.mode as any);
        useSystemStore.getState().setAgentStatus(state.agent.status as any);
        useSystemStore.getState().setAgentStrategy(state.agent.strategy as any);
        useSystemStore.getState().updatePerformance({
          vehicleCount: state.performance.vehicleCount,
          avgDensity: state.performance.avgDensity,
          fps: state.performance.fps,
        });
        
        setLoading(false);
      } catch (err) {
        console.error('Failed to connect to backend:', err);
        setError('Failed to connect to backend. Is the server running?');
        setLoading(false);
      }
    };
    
    initialize();
    
    return cleanup;
  }, []);

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

  if (error) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center p-6">
        <div className="max-w-lg w-full bg-slate-800/50 backdrop-blur-sm rounded-2xl border border-red-500/30 p-8 text-center">
          <div className="w-16 h-16 bg-red-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
          <h2 className="text-xl font-bold text-red-400 mb-2">Connection Failed</h2>
          <p className="text-slate-400 mb-6">{error}</p>
          
          <div className="bg-slate-900/50 rounded-lg p-4 text-left mb-6">
            <p className="text-sm text-slate-500 mb-2">Start the backend server:</p>
            <code className="block text-sm text-cyan-400 font-mono bg-slate-800 p-3 rounded">
              cd backend && python -m uvicorn app.main:sio_app --reload
            </code>
          </div>
          
          <button 
            onClick={() => window.location.reload()}
            className="px-6 py-2 bg-cyan-500/20 text-cyan-400 border border-cyan-500/30 rounded-lg hover:bg-cyan-500/30 transition-all"
          >
            Retry Connection
          </button>
        </div>
      </div>
    );
  }

  return (
    <BrowserRouter>
      <div className="h-screen flex flex-col bg-slate-900">
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
              <Route path="/incidents" element={<Dashboard />} />
              <Route path="/challans" element={<Dashboard />} />
              <Route path="/emergency" element={<Dashboard />} />
              <Route path="/settings" element={<SettingsPlaceholder />} />
            </Routes>
          </main>
        </div>
      </div>
    </BrowserRouter>
  );
}

// Placeholder for settings page
const SettingsPlaceholder = () => (
  <div className="p-6 flex items-center justify-center min-h-full">
    <div className="text-center">
      <div className="w-20 h-20 bg-slate-800/50 rounded-full flex items-center justify-center mx-auto mb-4">
        <svg className="w-10 h-10 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
        </svg>
      </div>
      <h2 className="text-xl font-bold text-white mb-2">Settings</h2>
      <p className="text-slate-400">Configuration options coming soon</p>
    </div>
  </div>
);

export default App;
