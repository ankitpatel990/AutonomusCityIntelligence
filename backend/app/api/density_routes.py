"""
Density API Routes

REST API endpoints for density queries, exports, and WebSocket event support.
Implements FRD-02 Section 4.2 requirements.

Endpoints:
- GET /api/density/ - City-wide density metrics
- GET /api/density/roads - All road densities
- GET /api/density/junctions - All junction densities
- GET /api/density/road/{road_id} - Specific road density
- GET /api/density/junction/{junction_id} - Specific junction density
- GET /api/density/history/{road_id} - Road density history
- GET /api/density/export/csv - Export as CSV
- GET /api/density/export/json - Export as JSON
- GET /api/density/ui-data - UI-formatted data
- POST /api/density/mode - Set data source mode
"""

from fastapi import APIRouter, HTTPException, Query, Response, Depends
from typing import Optional
import time

from app.density.density_tracker import (
    get_density_tracker,
    DensityTracker,
    TrafficDataSource
)
from app.density.density_exporter import DensityExporter
from app.density.density_history import TrendAnalyzer, DensityTrend

router = APIRouter(prefix="/api/density", tags=["density"])


def get_tracker() -> DensityTracker:
    """Dependency to get the density tracker"""
    return get_density_tracker()


@router.get("/")
async def get_city_density(tracker: DensityTracker = Depends(get_tracker)):
    """
    Get city-wide density metrics
    
    Returns complete aggregated statistics including:
    - Total vehicles
    - Average density
    - Congestion points
    - Road breakdown by classification
    - Peak density info
    """
    try:
        metrics = tracker.get_city_metrics()
        return metrics.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/roads")
async def get_all_road_densities(tracker: DensityTracker = Depends(get_tracker)):
    """
    Get density data for all roads
    
    Returns list of road density objects with:
    - Vehicle count
    - Density score
    - Classification
    """
    return tracker.get_all_road_densities()


@router.get("/junctions")
async def get_all_junction_densities(tracker: DensityTracker = Depends(get_tracker)):
    """
    Get aggregated density for all junctions
    
    Returns list of junction density objects with:
    - Per-direction densities
    - Average/max density
    - Total vehicles
    - Congestion level
    """
    return tracker.get_all_junction_densities()


@router.get("/road/{road_id}")
async def get_road_density(
    road_id: str,
    tracker: DensityTracker = Depends(get_tracker)
):
    """
    Get density for specific road
    
    Args:
        road_id: Road identifier (e.g., "R-1-2")
    """
    data = tracker.get_road_density(road_id)
    
    if not data:
        raise HTTPException(status_code=404, detail=f"Road {road_id} not found")
    
    return data.to_dict()


@router.get("/junction/{junction_id}")
async def get_junction_density(
    junction_id: str,
    tracker: DensityTracker = Depends(get_tracker)
):
    """
    Get density for specific junction
    
    Args:
        junction_id: Junction identifier (e.g., "J-5")
    """
    data = tracker.get_junction_density(junction_id)
    
    if not data:
        raise HTTPException(status_code=404, detail=f"Junction {junction_id} not found")
    
    return data.to_dict()


@router.get("/history/{road_id}")
async def get_road_density_history(
    road_id: str,
    duration: int = Query(default=300, description="Duration in seconds", ge=10, le=600),
    tracker: DensityTracker = Depends(get_tracker)
):
    """
    Get historical density for road
    
    Args:
        road_id: Road identifier
        duration: How far back to look (default 5 minutes, max 10 minutes)
    """
    history = tracker.history.get_history(road_id, duration)
    
    if not history:
        return {
            'roadId': road_id,
            'history': [],
            'count': 0
        }
    
    # Calculate trend
    analyzer = TrendAnalyzer()
    trend = analyzer.calculate_trend(history)
    rate = analyzer.calculate_rate_of_change(history)
    
    return {
        'roadId': road_id,
        'history': [s.to_dict() for s in history],
        'count': len(history),
        'trend': trend.value,
        'rateOfChange': round(rate, 4),
        'duration': duration
    }


@router.get("/trend/{road_id}")
async def get_road_trend(
    road_id: str,
    window: int = Query(default=60, description="Analysis window in seconds"),
    tracker: DensityTracker = Depends(get_tracker)
):
    """
    Get density trend analysis for road
    
    Args:
        road_id: Road identifier
        window: Time window for trend analysis
    """
    history = tracker.history.get_history(road_id, window)
    
    if len(history) < 2:
        return {
            'roadId': road_id,
            'trend': 'STABLE',
            'confidence': 'LOW',
            'dataPoints': len(history)
        }
    
    analyzer = TrendAnalyzer()
    trend = analyzer.calculate_trend(history, window)
    rate = analyzer.calculate_rate_of_change(history)
    volatility = analyzer.calculate_volatility(history)
    
    # Determine confidence based on data points
    confidence = 'HIGH' if len(history) > 30 else 'MEDIUM' if len(history) > 10 else 'LOW'
    
    return {
        'roadId': road_id,
        'trend': trend.value,
        'rateOfChange': round(rate, 4),
        'volatility': round(volatility, 2),
        'confidence': confidence,
        'dataPoints': len(history),
        'window': window
    }


@router.get("/export/csv")
async def export_density_csv(tracker: DensityTracker = Depends(get_tracker)):
    """
    Export density data as CSV
    
    Downloads a CSV file with road density data.
    """
    exporter = DensityExporter()
    csv_data = exporter.export_to_csv(tracker.road_densities)
    
    filename = f"density_export_{int(time.time())}.csv"
    
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


@router.get("/export/junctions/csv")
async def export_junctions_csv(tracker: DensityTracker = Depends(get_tracker)):
    """
    Export junction density data as CSV
    """
    exporter = DensityExporter()
    csv_data = exporter.export_junctions_to_csv(tracker.junction_densities)
    
    filename = f"junction_density_export_{int(time.time())}.csv"
    
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


@router.get("/export/json")
async def export_density_json(tracker: DensityTracker = Depends(get_tracker)):
    """
    Export complete density data as JSON
    
    Includes both road and junction data with metadata.
    """
    exporter = DensityExporter()
    json_data = exporter.export_to_json(
        tracker.road_densities,
        tracker.junction_densities
    )
    
    return Response(
        content=json_data,
        media_type="application/json"
    )


@router.get("/ui-data")
async def get_density_ui_data(tracker: DensityTracker = Depends(get_tracker)):
    """
    Get density data formatted for UI visualization
    
    Returns color-coded density info suitable for Canvas overlays.
    """
    exporter = DensityExporter()
    
    return {
        'roads': exporter.format_for_ui(tracker.road_densities),
        'junctions': exporter.format_junctions_for_ui(tracker.junction_densities),
        'timestamp': time.time()
    }


@router.get("/stats")
async def get_density_stats(tracker: DensityTracker = Depends(get_tracker)):
    """
    Get density tracker statistics
    
    Returns operational statistics about the density tracking system.
    """
    tracker_stats = tracker.get_stats()
    history_stats = tracker.history.get_stats()
    
    return {
        'tracker': tracker_stats,
        'history': history_stats,
        'timestamp': time.time()
    }


@router.post("/mode")
async def set_traffic_data_mode(
    request: dict,
    tracker: DensityTracker = Depends(get_tracker)
):
    """
    Switch traffic data source mode
    
    Modes:
    - LIVE_API: Use TomTom API data only
    - SIMULATION: Use simulation data only
    - HYBRID: Combine API and simulation
    - MANUAL: Manual override mode
    """
    mode = request.get('mode')
    
    valid_modes = ['LIVE_API', 'SIMULATION', 'HYBRID', 'MANUAL']
    if mode not in valid_modes:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid mode. Must be one of: {valid_modes}"
        )
    
    tracker.set_data_source_mode(TrafficDataSource(mode))
    
    return {
        'mode': mode,
        'status': 'success',
        'timestamp': time.time()
    }


@router.get("/hotspots")
async def get_congestion_hotspots(
    threshold: float = Query(default=70.0, description="Density threshold"),
    tracker: DensityTracker = Depends(get_tracker)
):
    """
    Get roads above congestion threshold
    
    Returns list of congested roads sorted by density score.
    """
    from app.density.city_metrics import CityDensityCalculator
    
    calculator = CityDensityCalculator()
    hotspots = calculator.get_congestion_hotspots(
        tracker.road_densities,
        threshold
    )
    
    return {
        'threshold': threshold,
        'hotspots': [
            {'roadId': road_id, 'densityScore': round(score, 2)}
            for road_id, score in hotspots
        ],
        'count': len(hotspots),
        'timestamp': time.time()
    }


@router.get("/distribution")
async def get_density_distribution(tracker: DensityTracker = Depends(get_tracker)):
    """
    Get distribution of density scores
    
    Returns min, max, mean, median, and 90th percentile.
    """
    from app.density.city_metrics import CityDensityCalculator
    
    calculator = CityDensityCalculator()
    distribution = calculator.get_density_distribution(tracker.road_densities)
    
    return {
        'distribution': distribution,
        'totalRoads': len(tracker.road_densities),
        'timestamp': time.time()
    }

