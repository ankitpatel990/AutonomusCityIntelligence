/**
 * PredictionTimeline Component
 * FRD-06: AI-Based Congestion Prediction
 * 
 * Visualizes congestion predictions for a road segment with:
 * - Timeline chart showing predicted density
 * - Color-coded congestion levels
 * - Confidence indicator
 * - Algorithm display
 */

import React, { useEffect, useState } from 'react';
import { useRoadPrediction } from '../hooks/usePrediction';
import {
  RoadPrediction,
  CongestionLevel,
  getCongestionColor,
  getCongestionClass,
  formatPredictionTime,
  formatConfidence,
  getAlgorithmName
} from '../types/prediction';

interface PredictionTimelineProps {
  roadId: string;
  showChart?: boolean;
  compact?: boolean;
  className?: string;
}

export const PredictionTimeline: React.FC<PredictionTimelineProps> = ({
  roadId,
  showChart = true,
  compact = false,
  className = ''
}) => {
  const { prediction, loading, error, refresh } = useRoadPrediction(roadId);
  
  if (loading) {
    return (
      <div className={`prediction-timeline ${className}`}>
        <div className="animate-pulse">
          <div className="h-4 bg-gray-700 rounded w-3/4 mb-2"></div>
          <div className="h-24 bg-gray-700 rounded"></div>
        </div>
      </div>
    );
  }
  
  if (error) {
    return (
      <div className={`prediction-timeline ${className}`}>
        <div className="text-red-400 text-sm">
          Failed to load prediction: {error.message}
        </div>
        <button 
          onClick={refresh}
          className="mt-2 text-xs text-blue-400 hover:underline"
        >
          Retry
        </button>
      </div>
    );
  }
  
  if (!prediction) {
    return (
      <div className={`prediction-timeline ${className}`}>
        <div className="text-gray-500 text-sm italic">
          No prediction available (insufficient data)
        </div>
      </div>
    );
  }
  
  if (compact) {
    return <CompactView prediction={prediction} className={className} />;
  }
  
  return <FullView prediction={prediction} showChart={showChart} className={className} />;
};

// Compact view for list displays
const CompactView: React.FC<{ prediction: RoadPrediction; className?: string }> = ({
  prediction,
  className = ''
}) => {
  const maxLevel = prediction.maxCongestionLevel as CongestionLevel;
  
  return (
    <div className={`flex items-center gap-3 ${className}`}>
      {/* Current density */}
      <div className="text-lg font-bold">
        {prediction.currentDensity.toFixed(0)}%
      </div>
      
      {/* Max predicted level badge */}
      <span className={`px-2 py-0.5 rounded text-xs font-medium ${getCongestionClass(maxLevel)}`}>
        {maxLevel}
      </span>
      
      {/* Mini prediction bars */}
      <div className="flex gap-0.5">
        {prediction.predictions.slice(0, 5).map((p, i) => {
          const level = p.congestionLevel as CongestionLevel;
          return (
            <div
              key={i}
              className="w-2 h-4 rounded-sm"
              style={{ backgroundColor: getCongestionColor(level) }}
              title={`+${p.minutesAhead}min: ${p.predictedDensity.toFixed(0)}%`}
            />
          );
        })}
      </div>
      
      {/* Confidence */}
      <span className="text-xs text-gray-400">
        {formatConfidence(prediction.confidence)}
      </span>
    </div>
  );
};

// Full detailed view
const FullView: React.FC<{
  prediction: RoadPrediction;
  showChart: boolean;
  className?: string;
}> = ({ prediction, showChart, className = '' }) => {
  const maxLevel = prediction.maxCongestionLevel as CongestionLevel;
  
  return (
    <div className={`prediction-timeline bg-gray-800 rounded-lg p-4 ${className}`}>
      {/* Header */}
      <div className="flex justify-between items-start mb-4">
        <div>
          <h3 className="text-lg font-semibold text-white">{prediction.roadId}</h3>
          <div className="text-sm text-gray-400">
            {getAlgorithmName(prediction.algorithm)} • {formatConfidence(prediction.confidence)} confidence
          </div>
        </div>
        
        <span className={`px-3 py-1 rounded-full text-sm font-medium ${getCongestionClass(maxLevel)}`}>
          {maxLevel}
        </span>
      </div>
      
      {/* Current density */}
      <div className="mb-4">
        <div className="flex justify-between text-sm text-gray-400 mb-1">
          <span>Current Density</span>
          <span>{prediction.currentDensity.toFixed(1)}%</span>
        </div>
        <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
          <div
            className="h-full transition-all duration-500"
            style={{
              width: `${prediction.currentDensity}%`,
              backgroundColor: getCongestionColor(
                prediction.predictions[0]?.congestionLevel as CongestionLevel || CongestionLevel.LOW
              )
            }}
          />
        </div>
      </div>
      
      {/* Chart */}
      {showChart && (
        <div className="mb-4">
          <PredictionChart prediction={prediction} />
        </div>
      )}
      
      {/* Timeline grid */}
      <div className="grid grid-cols-5 gap-2">
        {prediction.predictions.slice(0, 5).map((p, i) => {
          const level = p.congestionLevel as CongestionLevel;
          return (
            <div
              key={i}
              className="text-center p-2 rounded"
              style={{ backgroundColor: getCongestionColor(level) + '20' }}
            >
              <div className="text-xs font-bold text-gray-300">
                {formatPredictionTime(p.minutesAhead)}
              </div>
              <div className="text-lg font-bold" style={{ color: getCongestionColor(level) }}>
                {p.predictedDensity.toFixed(0)}%
              </div>
              <div className="text-xs" style={{ color: getCongestionColor(level) }}>
                {level}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

// Simple chart visualization (no external library needed)
const PredictionChart: React.FC<{ prediction: RoadPrediction }> = ({ prediction }) => {
  const maxDensity = 100;
  const chartHeight = 80;
  
  // Include current as first point
  const points = [
    { minutesAhead: 0, predictedDensity: prediction.currentDensity, congestionLevel: CongestionLevel.LOW },
    ...prediction.predictions.slice(0, 10)
  ];
  
  // Create SVG path
  const xStep = 100 / (points.length - 1);
  const pathPoints = points.map((p, i) => {
    const x = i * xStep;
    const y = chartHeight - (p.predictedDensity / maxDensity) * chartHeight;
    return `${x},${y}`;
  });
  
  const linePath = `M ${pathPoints.join(' L ')}`;
  const areaPath = `${linePath} L ${100},${chartHeight} L 0,${chartHeight} Z`;
  
  return (
    <div className="relative">
      <svg
        viewBox={`0 0 100 ${chartHeight}`}
        className="w-full h-20"
        preserveAspectRatio="none"
      >
        {/* Grid lines */}
        {[25, 50, 75].map(y => (
          <line
            key={y}
            x1="0"
            y1={chartHeight - (y / maxDensity) * chartHeight}
            x2="100"
            y2={chartHeight - (y / maxDensity) * chartHeight}
            stroke="#374151"
            strokeWidth="0.5"
          />
        ))}
        
        {/* Area fill */}
        <path
          d={areaPath}
          fill="url(#gradient)"
          opacity="0.3"
        />
        
        {/* Line */}
        <path
          d={linePath}
          fill="none"
          stroke="#3b82f6"
          strokeWidth="2"
          vectorEffect="non-scaling-stroke"
        />
        
        {/* Points */}
        {points.map((p, i) => {
          const x = i * xStep;
          const y = chartHeight - (p.predictedDensity / maxDensity) * chartHeight;
          const level = p.congestionLevel as CongestionLevel;
          
          return (
            <circle
              key={i}
              cx={x}
              cy={y}
              r="3"
              fill={getCongestionColor(level)}
              stroke="#1f2937"
              strokeWidth="1"
            />
          );
        })}
        
        {/* Gradient definition */}
        <defs>
          <linearGradient id="gradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#3b82f6" stopOpacity="0.5" />
            <stop offset="100%" stopColor="#3b82f6" stopOpacity="0" />
          </linearGradient>
        </defs>
      </svg>
      
      {/* Y-axis labels */}
      <div className="absolute left-0 top-0 h-full flex flex-col justify-between text-xs text-gray-500 -ml-6">
        <span>100</span>
        <span>50</span>
        <span>0</span>
      </div>
      
      {/* X-axis labels */}
      <div className="flex justify-between text-xs text-gray-500 mt-1">
        <span>Now</span>
        <span>+5min</span>
        <span>+10min</span>
      </div>
    </div>
  );
};

export default PredictionTimeline;

