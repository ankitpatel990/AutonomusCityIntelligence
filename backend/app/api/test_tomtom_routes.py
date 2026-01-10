"""
Test TomTom API Routes

Quick test endpoints to verify TomTom API integration is working.
"""

from fastapi import APIRouter, HTTPException
import os
import aiohttp
import asyncio
from typing import Optional

from app.services.live_traffic_service import get_live_traffic_service, init_live_traffic_service

router = APIRouter(prefix="/api/test-tomtom", tags=["test-tomtom"])


@router.get("/status")
async def get_tomtom_status():
    """Check TomTom API configuration status"""
    api_key = os.getenv("TOMTOM_API_KEY", "")
    
    return {
        "configured": bool(api_key),
        "key_prefix": api_key[:8] + "..." if len(api_key) > 8 else "not set",
        "key_length": len(api_key)
    }


@router.get("/live-traffic")
async def test_live_traffic():
    """
    Test live traffic API call for Gandhinagar area
    
    Fetches real traffic data from TomTom for a point in Gandhinagar
    """
    api_key = os.getenv("TOMTOM_API_KEY", "")
    
    if not api_key:
        raise HTTPException(status_code=400, detail="TOMTOM_API_KEY not configured")
    
    # Test location: GIFT City, Gandhinagar
    # Coordinates: 23.1550, 72.6850
    test_lat = 23.1550
    test_lon = 72.6850
    
    # TomTom Flow Segment Data API
    url = f"https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json"
    params = {
        'key': api_key,
        'point': f"{test_lat},{test_lon}",
        'unit': 'KMPH',
        'openLr': 'false'
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    flow_data = data.get('flowSegmentData', {})
                    
                    # Calculate congestion level
                    current_speed = flow_data.get('currentSpeed', 0)
                    free_flow_speed = flow_data.get('freeFlowSpeed', 50)
                    
                    if free_flow_speed > 0:
                        ratio = current_speed / free_flow_speed
                        if ratio >= 0.8:
                            congestion = "LOW"
                        elif ratio >= 0.5:
                            congestion = "MEDIUM"
                        elif ratio >= 0.2:
                            congestion = "HIGH"
                        else:
                            congestion = "JAM"
                    else:
                        congestion = "UNKNOWN"
                    
                    return {
                        "status": "success",
                        "location": {
                            "lat": test_lat,
                            "lon": test_lon,
                            "name": "GIFT City, Gandhinagar"
                        },
                        "traffic": {
                            "currentSpeed": current_speed,
                            "freeFlowSpeed": free_flow_speed,
                            "congestionLevel": congestion,
                            "confidence": flow_data.get('confidence', 0),
                            "roadClosure": flow_data.get('roadClosure', False)
                        },
                        "raw": flow_data
                    }
                elif response.status == 401:
                    raise HTTPException(status_code=401, detail="Invalid TomTom API key")
                elif response.status == 429:
                    raise HTTPException(status_code=429, detail="TomTom API rate limit exceeded")
                else:
                    error_text = await response.text()
                    raise HTTPException(status_code=response.status, detail=f"TomTom API error: {error_text}")
                    
    except aiohttp.ClientError as e:
        raise HTTPException(status_code=500, detail=f"Network error: {str(e)}")
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="TomTom API request timed out")


@router.get("/multi-point")
async def test_multi_point_traffic():
    """
    Test traffic data for multiple points in Gandhinagar
    
    Tests the live traffic service for several locations
    """
    service = get_live_traffic_service()
    await service.initialize()
    
    # Test roads in Gandhinagar area
    test_roads = [
        {"id": "R-1", "start_lat": 23.2200, "start_lon": 72.6400, "end_lat": 23.2300, "end_lon": 72.6400},
        {"id": "R-2", "start_lat": 23.2200, "start_lon": 72.6500, "end_lat": 23.2200, "end_lon": 72.6600},
        {"id": "R-3", "start_lat": 23.1600, "start_lon": 72.6800, "end_lat": 23.1550, "end_lon": 72.6850},  # GIFT City
    ]
    
    results = await service.get_traffic_for_roads(test_roads)
    
    # Convert to JSON-serializable format
    formatted_results = {}
    for road_id, data in results.items():
        formatted_results[road_id] = {
            "currentSpeed": data.current_speed,
            "freeFlowSpeed": data.free_flow_speed,
            "congestionLevel": data.congestion_level,
            "confidence": data.confidence,
            "source": data.source,
            "provider": data.provider,
            "timestamp": data.timestamp
        }
    
    return {
        "status": "success",
        "roads": formatted_results,
        "count": len(results),
        "apiStatus": service.status.model_dump()
    }


@router.get("/density-with-traffic")
async def get_density_with_live_traffic():
    """
    Get density data enhanced with live TomTom traffic
    
    Combines our density tracking with real-time API data
    """
    from app.density import get_density_tracker, TrafficToVehicleConverter
    
    tracker = get_density_tracker()
    service = get_live_traffic_service()
    converter = TrafficToVehicleConverter()
    
    await service.initialize()
    
    # Test roads
    test_roads = [
        {"id": "R-1", "start_lat": 23.2200, "start_lon": 72.6400, "end_lat": 23.2300, "end_lon": 72.6400, "length": 500},
        {"id": "R-2", "start_lat": 23.2200, "start_lon": 72.6500, "end_lat": 23.2200, "end_lon": 72.6600, "length": 400},
        {"id": "R-3", "start_lat": 23.1600, "start_lon": 72.6800, "end_lat": 23.1550, "end_lon": 72.6850, "length": 600},
    ]
    
    # Get live traffic
    traffic_data = await service.get_traffic_for_roads(test_roads)
    
    # Calculate vehicle counts based on live data
    results = []
    for road in test_roads:
        road_id = road["id"]
        live_traffic = traffic_data.get(road_id)
        
        if live_traffic:
            vehicle_count = converter.calculate_vehicle_count(
                live_traffic.congestion_level,
                road["length"]
            )
            
            results.append({
                "roadId": road_id,
                "liveData": {
                    "congestionLevel": live_traffic.congestion_level,
                    "currentSpeed": live_traffic.current_speed,
                    "source": live_traffic.source
                },
                "simulation": {
                    "vehicleCount": vehicle_count,
                    "densityScore": min(100, vehicle_count * 5),
                }
            })
    
    return {
        "status": "success",
        "roads": results,
        "summary": converter.get_congestion_summary(traffic_data)
    }


