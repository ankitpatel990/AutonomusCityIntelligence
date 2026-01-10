"""
Density History Module

Time-series storage for density history with trend analysis.
Implements FRD-02 FR-02.5, FR-02.6 requirements.

Features:
- Circular buffer for bounded memory
- 10-minute retention (configurable)
- Trend analysis with linear regression
- Rate of change calculation
"""

from collections import deque
from dataclasses import dataclass
from typing import List, Dict, Optional
from enum import Enum
import time

from app.density.density_tracker import DensityLevel


@dataclass
class DensitySnapshot:
    """Single density measurement at a point in time"""
    timestamp: float
    road_id: str
    vehicle_count: int
    density_score: float
    classification: DensityLevel
    
    def to_dict(self) -> dict:
        """Convert to dictionary for API responses"""
        return {
            'timestamp': self.timestamp,
            'roadId': self.road_id,
            'vehicleCount': self.vehicle_count,
            'densityScore': round(self.density_score, 2),
            'classification': self.classification.value
        }


class DensityTrend(str, Enum):
    """Density trend direction"""
    DECREASING = "DECREASING"
    STABLE = "STABLE"
    INCREASING = "INCREASING"


class DensityHistory:
    """
    Store and manage historical density data
    
    Uses circular buffers (deque with maxlen) for bounded memory.
    Default retention: 10 minutes (600 seconds @ 1Hz = 600 entries/road)
    
    Usage:
        history = DensityHistory(retention_seconds=600)
        history.add_snapshot(snapshot)
        recent = history.get_history("R-1", duration_seconds=300)
    """
    
    def __init__(self, retention_seconds: int = 600):
        """
        Initialize density history
        
        Args:
            retention_seconds: How long to keep history (default 10 minutes)
        """
        self.retention_seconds = retention_seconds
        
        # Per-road history using circular buffers
        # Max entries = retention_seconds (at 1 snapshot/second)
        self._max_entries = retention_seconds
        self.road_history: Dict[str, deque] = {}
    
    def add_snapshot(self, snapshot: DensitySnapshot):
        """
        Add density snapshot to history
        
        Args:
            snapshot: DensitySnapshot to add
        """
        road_id = snapshot.road_id
        
        if road_id not in self.road_history:
            self.road_history[road_id] = deque(maxlen=self._max_entries)
        
        self.road_history[road_id].append(snapshot)
        
        # Clean old data (beyond retention period)
        self._cleanup_old_data(road_id, snapshot.timestamp)
    
    def _cleanup_old_data(self, road_id: str, current_time: float):
        """
        Remove snapshots older than retention period
        
        Args:
            road_id: Road to clean up
            current_time: Current timestamp
        """
        if road_id not in self.road_history:
            return
        
        history = self.road_history[road_id]
        cutoff_time = current_time - self.retention_seconds
        
        # Remove old entries from the left (oldest)
        while history and history[0].timestamp < cutoff_time:
            history.popleft()
    
    def get_history(
        self,
        road_id: str,
        duration_seconds: int = 300
    ) -> List[DensitySnapshot]:
        """
        Get density history for last N seconds
        
        Args:
            road_id: Road to get history for
            duration_seconds: How far back to look (default 5 minutes)
        
        Returns:
            List of density snapshots (chronological order)
        """
        if road_id not in self.road_history:
            return []
        
        history = self.road_history[road_id]
        cutoff_time = time.time() - duration_seconds
        
        return [s for s in history if s.timestamp >= cutoff_time]
    
    def get_all_roads_history(self) -> Dict[str, List[DensitySnapshot]]:
        """
        Get history for all roads
        
        Returns:
            Dictionary mapping road_id to list of snapshots
        """
        return {
            road_id: list(history)
            for road_id, history in self.road_history.items()
        }
    
    def get_latest(self, road_id: str) -> Optional[DensitySnapshot]:
        """
        Get the latest snapshot for a road
        
        Args:
            road_id: Road identifier
            
        Returns:
            Latest DensitySnapshot or None
        """
        if road_id not in self.road_history or not self.road_history[road_id]:
            return None
        return self.road_history[road_id][-1]
    
    def get_average_density(
        self,
        road_id: str,
        duration_seconds: int = 60
    ) -> float:
        """
        Get average density score over a period
        
        Args:
            road_id: Road identifier
            duration_seconds: Period to average over
            
        Returns:
            Average density score (0-100)
        """
        history = self.get_history(road_id, duration_seconds)
        if not history:
            return 0.0
        return sum(s.density_score for s in history) / len(history)
    
    def get_stats(self) -> dict:
        """Get history statistics"""
        total_entries = sum(len(h) for h in self.road_history.values())
        
        return {
            'totalRoads': len(self.road_history),
            'totalEntries': total_entries,
            'retentionSeconds': self.retention_seconds,
            'maxEntriesPerRoad': self._max_entries
        }
    
    def clear(self):
        """Clear all history data"""
        self.road_history.clear()


class TrendAnalyzer:
    """
    Analyze density trends over time
    
    Uses linear regression to determine if density is
    increasing, decreasing, or stable.
    """
    
    def __init__(self, slope_threshold: float = 5.0):
        """
        Initialize trend analyzer
        
        Args:
            slope_threshold: Minimum slope magnitude to consider a trend
        """
        self.slope_threshold = slope_threshold
    
    def calculate_trend(
        self,
        history: List[DensitySnapshot],
        window_seconds: int = 60
    ) -> DensityTrend:
        """
        Calculate density trend over time window
        
        Uses linear regression on density scores:
        - Positive slope > threshold → INCREASING
        - Negative slope < -threshold → DECREASING
        - Otherwise → STABLE
        
        Args:
            history: List of DensitySnapshot (chronological)
            window_seconds: Time window for trend analysis
            
        Returns:
            DensityTrend enum value
        """
        if len(history) < 2:
            return DensityTrend.STABLE
        
        # Get recent snapshots within window
        current_time = history[-1].timestamp
        cutoff_time = current_time - window_seconds
        recent = [s for s in history if s.timestamp >= cutoff_time]
        
        if len(recent) < 2:
            return DensityTrend.STABLE
        
        # Simple linear regression without numpy
        times = [s.timestamp for s in recent]
        densities = [s.density_score for s in recent]
        
        n = len(times)
        
        # Normalize time to start at 0
        t_min = min(times)
        t_max = max(times)
        t_range = t_max - t_min
        
        if t_range == 0:
            return DensityTrend.STABLE
        
        times_norm = [(t - t_min) / t_range for t in times]
        
        # Calculate slope using least squares
        sum_t = sum(times_norm)
        sum_d = sum(densities)
        sum_td = sum(t * d for t, d in zip(times_norm, densities))
        sum_t2 = sum(t * t for t in times_norm)
        
        denominator = n * sum_t2 - sum_t * sum_t
        if denominator == 0:
            return DensityTrend.STABLE
        
        slope = (n * sum_td - sum_t * sum_d) / denominator
        
        # Classify trend based on slope
        if slope > self.slope_threshold:
            return DensityTrend.INCREASING
        elif slope < -self.slope_threshold:
            return DensityTrend.DECREASING
        else:
            return DensityTrend.STABLE
    
    def calculate_rate_of_change(
        self,
        history: List[DensitySnapshot]
    ) -> float:
        """
        Calculate vehicles/second change rate
        
        Args:
            history: List of DensitySnapshot (chronological)
            
        Returns:
            Rate of change (vehicles/second)
        """
        if len(history) < 2:
            return 0.0
        
        time_diff = history[-1].timestamp - history[0].timestamp
        if time_diff == 0:
            return 0.0
        
        count_diff = history[-1].vehicle_count - history[0].vehicle_count
        return count_diff / time_diff
    
    def calculate_volatility(
        self,
        history: List[DensitySnapshot]
    ) -> float:
        """
        Calculate density volatility (standard deviation)
        
        Higher values indicate more fluctuation.
        
        Args:
            history: List of DensitySnapshot
            
        Returns:
            Volatility score (standard deviation of density)
        """
        if len(history) < 2:
            return 0.0
        
        densities = [s.density_score for s in history]
        avg = sum(densities) / len(densities)
        variance = sum((d - avg) ** 2 for d in densities) / len(densities)
        
        return variance ** 0.5
    
    def predict_time_to_threshold(
        self,
        history: List[DensitySnapshot],
        threshold: float = 70.0
    ) -> Optional[float]:
        """
        Predict time until density reaches threshold
        
        Args:
            history: List of DensitySnapshot
            threshold: Target density threshold
            
        Returns:
            Predicted seconds until threshold, or None if not predictable
        """
        if len(history) < 2:
            return None
        
        current = history[-1].density_score
        
        # If already at or above threshold
        if current >= threshold:
            return 0.0
        
        # Calculate rate of change
        rate = self.calculate_rate_of_change(history)
        
        # If decreasing or stable, won't reach threshold
        if rate <= 0:
            return None
        
        # Calculate time to threshold
        density_to_go = threshold - current
        # Convert vehicle rate to density rate (approximate)
        # Assuming linear relationship
        time_to_threshold = density_to_go / (rate * 10)  # Rough estimate
        
        return max(0, time_to_threshold)

