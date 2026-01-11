/**
 * Settings Page
 * 
 * System configuration and preferences
 */

import React, { useState } from 'react';
import { 
  Settings, 
  Save, 
  RotateCcw, 
  Monitor,
  Wifi,
  Database,
  Zap,
  Clock,
  Bell,
  Shield,
  Palette,
  Globe,
  HardDrive,
  CheckCircle
} from 'lucide-react';

interface SettingsSection {
  title: string;
  icon: React.ElementType;
  settings: Setting[];
}

interface Setting {
  key: string;
  label: string;
  description: string;
  type: 'toggle' | 'select' | 'input' | 'range';
  value: any;
  options?: { value: string; label: string }[];
  min?: number;
  max?: number;
}

export const SettingsPage: React.FC = () => {
  const [settings, setSettings] = useState<Record<string, any>>({
    autoReconnect: true,
    wsUrl: 'ws://localhost:8000',
    apiUrl: 'http://localhost:8000/api',
    defaultSpeed: 1,
    autoStartSimulation: false,
    enableNotifications: true,
    notificationSound: true,
    emergencyAlerts: true,
    theme: 'dark',
    animationQuality: 'high',
    showGrid: true,
    showLabels: true,
    refreshInterval: 2000,
    dataRetention: 100,
    enableLogging: true,
    agentStrategy: 'RL',
    failSafeThreshold: 5,
  });

  const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'saved'>('idle');

  const handleSettingChange = (key: string, value: any) => {
    setSettings(prev => ({ ...prev, [key]: value }));
  };

  const handleSave = async () => {
    setSaveStatus('saving');
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 1000));
    localStorage.setItem('appSettings', JSON.stringify(settings));
    setSaveStatus('saved');
    setTimeout(() => setSaveStatus('idle'), 2000);
  };

  const handleReset = () => {
    if (!confirm('Reset all settings to defaults?')) return;
    setSettings({
      autoReconnect: true,
      wsUrl: 'ws://localhost:8000',
      apiUrl: 'http://localhost:8000/api',
      defaultSpeed: 1,
      autoStartSimulation: false,
      enableNotifications: true,
      notificationSound: true,
      emergencyAlerts: true,
      theme: 'dark',
      animationQuality: 'high',
      showGrid: true,
      showLabels: true,
      refreshInterval: 2000,
      dataRetention: 100,
      enableLogging: true,
      agentStrategy: 'RL',
      failSafeThreshold: 5,
    });
  };

  const sections: SettingsSection[] = [
    {
      title: 'Connection',
      icon: Wifi,
      settings: [
        {
          key: 'autoReconnect',
          label: 'Auto Reconnect',
          description: 'Automatically reconnect when connection is lost',
          type: 'toggle',
          value: settings.autoReconnect,
        },
        {
          key: 'wsUrl',
          label: 'WebSocket URL',
          description: 'Backend WebSocket server address',
          type: 'input',
          value: settings.wsUrl,
        },
        {
          key: 'apiUrl',
          label: 'API URL',
          description: 'Backend REST API address',
          type: 'input',
          value: settings.apiUrl,
        },
      ],
    },
    {
      title: 'Simulation',
      icon: Zap,
      settings: [
        {
          key: 'defaultSpeed',
          label: 'Default Speed',
          description: 'Initial simulation speed multiplier',
          type: 'select',
          value: settings.defaultSpeed,
          options: [
            { value: '1', label: '1x (Normal)' },
            { value: '2', label: '2x (Fast)' },
            { value: '5', label: '5x (Very Fast)' },
            { value: '10', label: '10x (Maximum)' },
          ],
        },
        {
          key: 'autoStartSimulation',
          label: 'Auto Start',
          description: 'Automatically start simulation on page load',
          type: 'toggle',
          value: settings.autoStartSimulation,
        },
        {
          key: 'agentStrategy',
          label: 'Default Agent Strategy',
          description: 'Initial RL agent decision strategy',
          type: 'select',
          value: settings.agentStrategy,
          options: [
            { value: 'RL', label: 'Reinforcement Learning' },
            { value: 'RULE_BASED', label: 'Rule-Based' },
          ],
        },
      ],
    },
    {
      title: 'Notifications',
      icon: Bell,
      settings: [
        {
          key: 'enableNotifications',
          label: 'Enable Notifications',
          description: 'Show system notifications',
          type: 'toggle',
          value: settings.enableNotifications,
        },
        {
          key: 'notificationSound',
          label: 'Notification Sound',
          description: 'Play sound for notifications',
          type: 'toggle',
          value: settings.notificationSound,
        },
        {
          key: 'emergencyAlerts',
          label: 'Emergency Alerts',
          description: 'Show prominent alerts for emergencies',
          type: 'toggle',
          value: settings.emergencyAlerts,
        },
      ],
    },
    {
      title: 'Display',
      icon: Monitor,
      settings: [
        {
          key: 'theme',
          label: 'Theme',
          description: 'Application color theme',
          type: 'select',
          value: settings.theme,
          options: [
            { value: 'dark', label: 'Dark' },
            { value: 'light', label: 'Light' },
            { value: 'system', label: 'System' },
          ],
        },
        {
          key: 'animationQuality',
          label: 'Animation Quality',
          description: 'Canvas rendering quality',
          type: 'select',
          value: settings.animationQuality,
          options: [
            { value: 'low', label: 'Low (Better Performance)' },
            { value: 'medium', label: 'Medium' },
            { value: 'high', label: 'High (Best Quality)' },
          ],
        },
        {
          key: 'showGrid',
          label: 'Show Grid',
          description: 'Display grid overlay on city map',
          type: 'toggle',
          value: settings.showGrid,
        },
        {
          key: 'showLabels',
          label: 'Show Labels',
          description: 'Display junction and vehicle labels',
          type: 'toggle',
          value: settings.showLabels,
        },
      ],
    },
    {
      title: 'Data & Performance',
      icon: Database,
      settings: [
        {
          key: 'refreshInterval',
          label: 'Refresh Interval (ms)',
          description: 'Statistics refresh rate',
          type: 'select',
          value: settings.refreshInterval,
          options: [
            { value: '1000', label: '1 second' },
            { value: '2000', label: '2 seconds' },
            { value: '5000', label: '5 seconds' },
            { value: '10000', label: '10 seconds' },
          ],
        },
        {
          key: 'dataRetention',
          label: 'Data Retention',
          description: 'Max items to keep in history',
          type: 'select',
          value: settings.dataRetention,
          options: [
            { value: '50', label: '50 items' },
            { value: '100', label: '100 items' },
            { value: '200', label: '200 items' },
            { value: '500', label: '500 items' },
          ],
        },
        {
          key: 'enableLogging',
          label: 'Enable Logging',
          description: 'Log debug information to console',
          type: 'toggle',
          value: settings.enableLogging,
        },
      ],
    },
    {
      title: 'Safety',
      icon: Shield,
      settings: [
        {
          key: 'failSafeThreshold',
          label: 'Fail-Safe Threshold',
          description: 'Seconds before entering fail-safe mode',
          type: 'select',
          value: settings.failSafeThreshold,
          options: [
            { value: '3', label: '3 seconds' },
            { value: '5', label: '5 seconds' },
            { value: '10', label: '10 seconds' },
            { value: '30', label: '30 seconds' },
          ],
        },
      ],
    },
  ];

  return (
    <div className="p-6 space-y-6 min-h-full">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <Settings className="w-7 h-7 text-slate-400" />
            Settings
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Configure system preferences and behavior
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={handleReset}
            className="flex items-center gap-2 px-4 py-2 bg-slate-700/50 text-slate-300 rounded-lg hover:bg-slate-700 transition-all"
          >
            <RotateCcw className="w-4 h-4" />
            Reset
          </button>
          <button
            onClick={handleSave}
            disabled={saveStatus === 'saving'}
            className="flex items-center gap-2 px-4 py-2 bg-cyan-500 text-white rounded-lg hover:bg-cyan-600 transition-all disabled:opacity-50"
          >
            {saveStatus === 'saving' ? (
              <>
                <RotateCcw className="w-4 h-4 animate-spin" />
                Saving...
              </>
            ) : saveStatus === 'saved' ? (
              <>
                <CheckCircle className="w-4 h-4" />
                Saved!
              </>
            ) : (
              <>
                <Save className="w-4 h-4" />
                Save Changes
              </>
            )}
          </button>
        </div>
      </div>

      {/* Settings Sections */}
      <div className="space-y-6">
        {sections.map((section) => (
          <div 
            key={section.title}
            className="bg-slate-800/50 backdrop-blur-sm rounded-2xl border border-slate-700/50 overflow-hidden"
          >
            <div className="px-6 py-4 bg-slate-900/50 border-b border-slate-700/50">
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                <section.icon className="w-5 h-5 text-cyan-400" />
                {section.title}
              </h2>
            </div>
            <div className="divide-y divide-slate-700/30">
              {section.settings.map((setting) => (
                <div key={setting.key} className="px-6 py-4 flex items-center justify-between">
                  <div>
                    <label className="font-medium text-white">{setting.label}</label>
                    <p className="text-sm text-slate-400 mt-0.5">{setting.description}</p>
                  </div>
                  <div className="ml-4">
                    {setting.type === 'toggle' && (
                      <button
                        onClick={() => handleSettingChange(setting.key, !setting.value)}
                        className={`w-12 h-6 rounded-full transition-all duration-200 ${
                          setting.value 
                            ? 'bg-cyan-500' 
                            : 'bg-slate-600'
                        }`}
                      >
                        <div className={`w-5 h-5 bg-white rounded-full shadow-md transform transition-transform duration-200 ${
                          setting.value ? 'translate-x-6' : 'translate-x-0.5'
                        }`}></div>
                      </button>
                    )}
                    {setting.type === 'select' && (
                      <select
                        value={String(setting.value)}
                        onChange={(e) => handleSettingChange(setting.key, e.target.value)}
                        className="bg-slate-700/50 border border-slate-600/50 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-cyan-500/50"
                      >
                        {setting.options?.map(opt => (
                          <option key={opt.value} value={opt.value}>{opt.label}</option>
                        ))}
                      </select>
                    )}
                    {setting.type === 'input' && (
                      <input
                        type="text"
                        value={setting.value}
                        onChange={(e) => handleSettingChange(setting.key, e.target.value)}
                        className="w-64 bg-slate-700/50 border border-slate-600/50 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-cyan-500/50"
                      />
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* System Info */}
      <div className="bg-slate-800/50 backdrop-blur-sm rounded-2xl border border-slate-700/50 p-6">
        <h2 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
          <HardDrive className="w-5 h-5 text-cyan-400" />
          System Information
        </h2>
        <div className="grid grid-cols-3 gap-4">
          <div className="bg-slate-900/50 rounded-lg p-4">
            <p className="text-xs text-slate-500 uppercase tracking-wider">Version</p>
            <p className="text-lg font-mono text-white mt-1">v2.0.0</p>
          </div>
          <div className="bg-slate-900/50 rounded-lg p-4">
            <p className="text-xs text-slate-500 uppercase tracking-wider">Build</p>
            <p className="text-lg font-mono text-white mt-1">AutonomousHacks 2026</p>
          </div>
          <div className="bg-slate-900/50 rounded-lg p-4">
            <p className="text-xs text-slate-500 uppercase tracking-wider">Environment</p>
            <p className="text-lg font-mono text-white mt-1">Development</p>
          </div>
        </div>
      </div>
    </div>
  );
};

