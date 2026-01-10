/**
 * Control Panel Component
 * 
 * Simulation controls: play/pause, reset, speed control, agent management
 */

import React, { useState } from 'react';
import { 
  Play, 
  Pause, 
  RotateCcw, 
  Zap, 
  Clock, 
  Gauge, 
  Brain,
  Settings,
  RefreshCw
} from 'lucide-react';
import { useSystemStore } from '../store/useSystemStore';
import { api } from '../services/api';

export const ControlPanel: React.FC = () => {
  const { 
    isRunning, 
    isPaused, 
    simulationTime, 
    timeMultiplier,
    agentStatus,
    agentStrategy,
    setIsRunning,
    setIsPaused,
    setTimeMultiplier,
    setAgentStatus,
    setAgentStrategy,
  } = useSystemStore();

  const [loading, setLoading] = useState<string | null>(null);

  const formatTime = (seconds: number) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const handlePlayPause = async () => {
    setLoading('playPause');
    try {
      if (!isRunning) {
        await api.startSimulation();
        setIsRunning(true);
        setIsPaused(false);
      } else if (isPaused) {
        await api.resumeSimulation();
        setIsPaused(false);
      } else {
        await api.pauseSimulation();
        setIsPaused(true);
      }
    } catch (error) {
      console.error('Failed to toggle simulation:', error);
    }
    setLoading(null);
  };

  const handleReset = async () => {
    if (!confirm('Reset simulation? This will clear all vehicles and reset time.')) return;
    setLoading('reset');
    try {
      await api.resetSimulation();
      useSystemStore.getState().resetState();
    } catch (error) {
      console.error('Failed to reset simulation:', error);
    }
    setLoading(null);
  };

  const handleSpeedChange = async (speed: number) => {
    setLoading('speed');
    try {
      await api.setSimulationSpeed(speed as 1 | 5 | 10);
      setTimeMultiplier(speed);
    } catch (error) {
      console.error('Failed to change speed:', error);
    }
    setLoading(null);
  };

  const handleAgentToggle = async () => {
    setLoading('agent');
    try {
      if (agentStatus === 'STOPPED') {
        await api.startAgent(agentStrategy);
        setAgentStatus('RUNNING');
      } else if (agentStatus === 'RUNNING') {
        await api.pauseAgent();
        setAgentStatus('PAUSED');
      } else {
        await api.resumeAgent();
        setAgentStatus('RUNNING');
      }
    } catch (error) {
      console.error('Failed to toggle agent:', error);
    }
    setLoading(null);
  };

  const handleStopAgent = async () => {
    setLoading('stopAgent');
    try {
      await api.stopAgent();
      setAgentStatus('STOPPED');
    } catch (error) {
      console.error('Failed to stop agent:', error);
    }
    setLoading(null);
  };

  const handleStrategyChange = (strategy: 'RL' | 'RULE_BASED') => {
    setAgentStrategy(strategy);
  };

  return (
    <div className="bg-slate-800/50 backdrop-blur-sm rounded-2xl border border-slate-700/50 p-5 space-y-5">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="p-2 bg-cyan-500/20 rounded-lg">
          <Settings className="w-5 h-5 text-cyan-400" />
        </div>
        <h3 className="text-lg font-bold text-white">Control Panel</h3>
      </div>

      {/* Time Display */}
      <div className="bg-slate-900/50 rounded-xl p-4 border border-slate-700/30">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Clock className="w-5 h-5 text-cyan-400" />
            <span className="text-sm text-slate-400">Simulation Time</span>
          </div>
          {isRunning && !isPaused && (
            <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
          )}
        </div>
        <p className="text-3xl font-mono font-bold text-white mt-2 tracking-wider">
          {formatTime(simulationTime)}
        </p>
        <p className="text-xs text-slate-500 mt-1">
          Speed: {timeMultiplier}x • {isRunning ? (isPaused ? 'Paused' : 'Running') : 'Stopped'}
        </p>
      </div>

      {/* Simulation Controls */}
      <div className="space-y-3">
        <h4 className="text-sm font-semibold text-slate-400 flex items-center gap-2">
          <Gauge className="w-4 h-4" />
          Simulation
        </h4>
        <div className="flex gap-2">
          <button
            onClick={handlePlayPause}
            disabled={loading === 'playPause'}
            className={`flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-xl font-medium transition-all duration-200 ${
              isRunning && !isPaused
                ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30 hover:bg-amber-500/30'
                : 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 hover:bg-emerald-500/30'
            } ${loading === 'playPause' ? 'opacity-50 cursor-wait' : ''}`}
          >
            {loading === 'playPause' ? (
              <RefreshCw className="w-5 h-5 animate-spin" />
            ) : isRunning && !isPaused ? (
              <>
                <Pause className="w-5 h-5" />
                Pause
              </>
            ) : (
              <>
                <Play className="w-5 h-5" />
                {isPaused ? 'Resume' : 'Start'}
              </>
            )}
          </button>
          <button
            onClick={handleReset}
            disabled={loading === 'reset'}
            className={`px-4 py-3 bg-slate-700/50 hover:bg-slate-700 text-slate-300 rounded-xl transition-all ${
              loading === 'reset' ? 'opacity-50 cursor-wait' : ''
            }`}
            title="Reset Simulation"
          >
            {loading === 'reset' ? (
              <RefreshCw className="w-5 h-5 animate-spin" />
            ) : (
              <RotateCcw className="w-5 h-5" />
            )}
          </button>
        </div>
      </div>

      {/* Speed Control */}
      <div className="space-y-3">
        <h4 className="text-sm font-semibold text-slate-400">Speed Control</h4>
        <div className="flex gap-2">
          {[1, 2, 5, 10].map((speed) => (
            <button
              key={speed}
              onClick={() => handleSpeedChange(speed)}
              disabled={loading === 'speed'}
              className={`flex-1 px-3 py-2 rounded-lg font-medium text-sm transition-all ${
                timeMultiplier === speed
                  ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30'
                  : 'bg-slate-700/50 text-slate-400 hover:bg-slate-700 hover:text-white'
              }`}
            >
              {speed}x
            </button>
          ))}
        </div>
      </div>

      {/* Agent Controls */}
      <div className="space-y-3 pt-3 border-t border-slate-700/50">
        <h4 className="text-sm font-semibold text-slate-400 flex items-center gap-2">
          <Brain className="w-4 h-4" />
          RL Agent Control
        </h4>
        
        {/* Strategy Selection */}
        <div className="flex gap-2">
          {(['RL', 'RULE_BASED'] as const).map((strategy) => (
            <button
              key={strategy}
              onClick={() => handleStrategyChange(strategy)}
              disabled={agentStatus === 'RUNNING'}
              className={`flex-1 px-3 py-2 rounded-lg text-sm font-medium transition-all ${
                agentStrategy === strategy
                  ? 'bg-purple-500/20 text-purple-400 border border-purple-500/30'
                  : 'bg-slate-700/50 text-slate-400 hover:bg-slate-700'
              } ${agentStatus === 'RUNNING' ? 'opacity-50 cursor-not-allowed' : ''}`}
            >
              {strategy === 'RL' ? '🤖 RL' : '📋 Rules'}
            </button>
          ))}
        </div>

        {/* Agent Status & Controls */}
        <div className="flex gap-2">
          <button
            onClick={handleAgentToggle}
            disabled={loading === 'agent'}
            className={`flex-1 flex items-center justify-center gap-2 px-4 py-3 rounded-xl font-medium transition-all ${
              agentStatus === 'RUNNING'
                ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30 hover:bg-amber-500/30'
                : agentStatus === 'PAUSED'
                ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 hover:bg-emerald-500/30'
                : 'bg-purple-500/20 text-purple-400 border border-purple-500/30 hover:bg-purple-500/30'
            } ${loading === 'agent' ? 'opacity-50 cursor-wait' : ''}`}
          >
            {loading === 'agent' ? (
              <RefreshCw className="w-5 h-5 animate-spin" />
            ) : (
              <>
                <Zap className="w-5 h-5" />
                {agentStatus === 'RUNNING' ? 'Pause' : agentStatus === 'PAUSED' ? 'Resume' : 'Start'} Agent
              </>
            )}
          </button>
          {agentStatus !== 'STOPPED' && (
            <button
              onClick={handleStopAgent}
              disabled={loading === 'stopAgent'}
              className={`px-4 py-3 bg-red-500/20 hover:bg-red-500/30 text-red-400 rounded-xl transition-all ${
                loading === 'stopAgent' ? 'opacity-50 cursor-wait' : ''
              }`}
              title="Stop Agent"
            >
              {loading === 'stopAgent' ? (
                <RefreshCw className="w-5 h-5 animate-spin" />
              ) : (
                <span className="text-sm font-medium">Stop</span>
              )}
            </button>
          )}
        </div>

        {/* Agent Status Indicator */}
        <div className={`flex items-center gap-2 px-3 py-2 rounded-lg ${
          agentStatus === 'RUNNING' ? 'bg-emerald-500/10' :
          agentStatus === 'PAUSED' ? 'bg-amber-500/10' :
          'bg-slate-700/30'
        }`}>
          <div className={`w-2 h-2 rounded-full ${
            agentStatus === 'RUNNING' ? 'bg-emerald-400 animate-pulse' :
            agentStatus === 'PAUSED' ? 'bg-amber-400' :
            'bg-slate-500'
          }`}></div>
          <span className="text-xs text-slate-400">
            Agent: <span className={`font-semibold ${
              agentStatus === 'RUNNING' ? 'text-emerald-400' :
              agentStatus === 'PAUSED' ? 'text-amber-400' :
              'text-slate-500'
            }`}>{agentStatus}</span>
            {agentStatus !== 'STOPPED' && (
              <span className="ml-2 text-slate-500">({agentStrategy})</span>
            )}
          </span>
        </div>
      </div>
    </div>
  );
};

