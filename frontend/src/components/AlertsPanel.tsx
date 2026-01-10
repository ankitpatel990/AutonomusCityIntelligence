/**
 * AlertsPanel Component
 * FRD-06: AI-Based Congestion Prediction
 * 
 * Displays congestion prediction alerts with:
 * - Real-time alert updates
 * - Severity color coding
 * - Alert dismissal
 * - Alert history
 */

import React from 'react';
import { usePredictionAlerts } from '../hooks/usePrediction';
import {
  CongestionAlert,
  AlertSeverity,
  CongestionLevel,
  getSeverityColor,
  getCongestionColor
} from '../types/prediction';

interface AlertsPanelProps {
  roadId?: string;
  maxAlerts?: number;
  showDismiss?: boolean;
  className?: string;
}

export const AlertsPanel: React.FC<AlertsPanelProps> = ({
  roadId,
  maxAlerts = 10,
  showDismiss = true,
  className = ''
}) => {
  const { alerts, loading, error, resolveAlert, refresh } = usePredictionAlerts({
    roadId,
    activeOnly: true,
    showNotifications: true
  });
  
  if (loading) {
    return (
      <div className={`alerts-panel ${className}`}>
        <div className="animate-pulse space-y-2">
          {[1, 2, 3].map(i => (
            <div key={i} className="h-16 bg-gray-700 rounded"></div>
          ))}
        </div>
      </div>
    );
  }
  
  if (error) {
    return (
      <div className={`alerts-panel ${className}`}>
        <div className="text-red-400 text-sm">
          Failed to load alerts: {error.message}
        </div>
      </div>
    );
  }
  
  if (alerts.length === 0) {
    return (
      <div className={`alerts-panel ${className}`}>
        <div className="text-center py-8 text-gray-500">
          <svg className="w-12 h-12 mx-auto mb-2 opacity-50" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <p>No active congestion alerts</p>
        </div>
      </div>
    );
  }
  
  return (
    <div className={`alerts-panel space-y-2 ${className}`}>
      {alerts.slice(0, maxAlerts).map(alert => (
        <AlertCard
          key={alert.alertId}
          alert={alert}
          onDismiss={showDismiss ? () => resolveAlert(alert.alertId) : undefined}
        />
      ))}
      
      {alerts.length > maxAlerts && (
        <div className="text-center text-sm text-gray-500">
          +{alerts.length - maxAlerts} more alerts
        </div>
      )}
    </div>
  );
};

// Individual alert card
interface AlertCardProps {
  alert: CongestionAlert;
  onDismiss?: () => void;
}

const AlertCard: React.FC<AlertCardProps> = ({ alert, onDismiss }) => {
  const severityColor = getSeverityColor(alert.severity as AlertSeverity);
  const levelColor = getCongestionColor(alert.predictedLevel as CongestionLevel);
  
  // Icon based on severity
  const SeverityIcon = () => {
    if (alert.severity === 'CRITICAL') {
      return (
        <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
        </svg>
      );
    }
    if (alert.severity === 'WARNING') {
      return (
        <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
          <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
        </svg>
      );
    }
    return (
      <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
        <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
      </svg>
    );
  };
  
  return (
    <div
      className="alert-card bg-gray-800 rounded-lg p-3 border-l-4 transition-all hover:bg-gray-750"
      style={{ borderColor: severityColor }}
    >
      <div className="flex items-start gap-3">
        {/* Icon */}
        <div className="flex-shrink-0 mt-0.5" style={{ color: severityColor }}>
          <SeverityIcon />
        </div>
        
        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="font-semibold text-white">{alert.roadId}</span>
            <span
              className="px-1.5 py-0.5 rounded text-xs font-medium"
              style={{
                backgroundColor: levelColor + '30',
                color: levelColor
              }}
            >
              {alert.predictedLevel}
            </span>
          </div>
          
          <p className="text-sm text-gray-300">{alert.message}</p>
          
          <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
            <span>In {alert.minutesAhead} minutes</span>
            <span>{(alert.confidence * 100).toFixed(0)}% confidence</span>
          </div>
        </div>
        
        {/* Dismiss button */}
        {onDismiss && (
          <button
            onClick={onDismiss}
            className="flex-shrink-0 p-1 text-gray-500 hover:text-white transition-colors"
            title="Dismiss alert"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        )}
      </div>
    </div>
  );
};

// Alert badge for header/navbar
interface AlertBadgeProps {
  className?: string;
}

export const AlertBadge: React.FC<AlertBadgeProps> = ({ className = '' }) => {
  const { alerts } = usePredictionAlerts({ activeOnly: true });
  
  const criticalCount = alerts.filter(a => a.severity === 'CRITICAL').length;
  const warningCount = alerts.filter(a => a.severity === 'WARNING').length;
  const totalCount = alerts.length;
  
  if (totalCount === 0) {
    return null;
  }
  
  const bgColor = criticalCount > 0 ? 'bg-red-500' : warningCount > 0 ? 'bg-orange-500' : 'bg-blue-500';
  
  return (
    <span className={`inline-flex items-center justify-center min-w-5 h-5 px-1.5 rounded-full text-xs font-medium text-white ${bgColor} ${className}`}>
      {totalCount}
    </span>
  );
};

export default AlertsPanel;

