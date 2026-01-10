"""
RL Model Management API Routes

API endpoints for managing RL models - uploading, downloading,
switching between models, and viewing model metadata.
Implements FRD-04 FR-04.6: Model management.

Endpoints:
- GET    /api/rl/models              - List all models
- POST   /api/rl/models/upload       - Upload new model
- GET    /api/rl/models/{name}/download - Download model
- POST   /api/rl/models/{name}/activate - Activate model
- DELETE /api/rl/models/{name}       - Delete model
- GET    /api/rl/status              - Get RL service status
- POST   /api/rl/reload              - Reload current model
- POST   /api/rl/predict             - Run inference
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from typing import List, Optional
import os
import shutil
import time

from app.rl.inference import get_inference_service

router = APIRouter(prefix="/api/rl", tags=["rl"])

# Models directory
MODELS_DIR = "./models"
os.makedirs(MODELS_DIR, exist_ok=True)


# ============================================
# Request/Response Models
# ============================================

class ModelInfo(BaseModel):
    """Model information"""
    name: str
    size_bytes: int
    modified_time: float
    is_active: bool


class PredictionRequest(BaseModel):
    """Request for RL prediction"""
    observation: List[float] = Field(..., min_length=63, max_length=63)
    deterministic: bool = True


class PredictionResponse(BaseModel):
    """Response from RL prediction"""
    actions: List[int]
    inference_time_ms: float


class RLStatusResponse(BaseModel):
    """RL service status"""
    model_loaded: bool
    model_path: Optional[str]
    inference_count: int
    avg_inference_time: float
    max_inference_time: float
    slow_inference_count: int
    device: Optional[str]
    ready: bool


class TrainingStatusResponse(BaseModel):
    """Training status (for async training)"""
    is_training: bool
    current_step: int
    total_steps: int
    progress_percent: float
    elapsed_time: float
    estimated_remaining: float


# ============================================
# Model Management Endpoints
# ============================================

@router.get("/models", response_model=List[ModelInfo])
async def list_models():
    """
    List all available RL models
    
    Returns list of model files in the models directory.
    """
    models = []
    
    inference_service = get_inference_service()
    active_model = inference_service.model_path
    
    if not os.path.exists(MODELS_DIR):
        return models
    
    for filename in os.listdir(MODELS_DIR):
        if filename.endswith('.zip'):
            filepath = os.path.join(MODELS_DIR, filename)
            stat = os.stat(filepath)
            
            # Normalize paths for comparison
            active_normalized = os.path.normpath(active_model) if active_model else None
            filepath_normalized = os.path.normpath(filepath)
            
            models.append(ModelInfo(
                name=filename,
                size_bytes=stat.st_size,
                modified_time=stat.st_mtime,
                is_active=(filepath_normalized == active_normalized)
            ))
    
    # Sort by modification time (newest first)
    models.sort(key=lambda m: m.modified_time, reverse=True)
    
    return models


@router.post("/models/upload")
async def upload_model(file: UploadFile = File(...)):
    """
    Upload a new RL model
    
    Model file should be .zip format (Stable-Baselines3 saved model).
    """
    if not file.filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="Model must be .zip file")
    
    # Save uploaded file
    filepath = os.path.join(MODELS_DIR, file.filename)
    
    try:
        with open(filepath, 'wb') as f:
            shutil.copyfileobj(file.file, f)
        
        return {
            'status': 'uploaded',
            'filename': file.filename,
            'path': filepath,
            'size_bytes': os.path.getsize(filepath)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.get("/models/{model_name}/download")
async def download_model(model_name: str):
    """
    Download a model file
    
    Returns the model file as a downloadable attachment.
    """
    filepath = os.path.join(MODELS_DIR, model_name)
    
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Model not found")
    
    return FileResponse(
        path=filepath,
        filename=model_name,
        media_type='application/zip'
    )


@router.post("/models/{model_name}/activate")
async def activate_model(model_name: str):
    """
    Switch to a different model
    
    Loads the specified model into the inference service.
    """
    filepath = os.path.join(MODELS_DIR, model_name)
    
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Model not found")
    
    inference_service = get_inference_service()
    
    try:
        success = inference_service.load_model(filepath)
        
        if success:
            return {
                'status': 'activated',
                'model': model_name,
                'path': filepath,
                'timestamp': time.time()
            }
        else:
            raise HTTPException(status_code=500, detail="Model activation failed")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Model load failed: {str(e)}")


@router.delete("/models/{model_name}")
async def delete_model(model_name: str):
    """
    Delete a model file
    
    Cannot delete the currently active model.
    """
    filepath = os.path.join(MODELS_DIR, model_name)
    
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Model not found")
    
    # Check if active
    inference_service = get_inference_service()
    if inference_service.model_path:
        active_normalized = os.path.normpath(inference_service.model_path)
        filepath_normalized = os.path.normpath(filepath)
        
        if filepath_normalized == active_normalized:
            raise HTTPException(status_code=400, detail="Cannot delete active model")
    
    try:
        os.remove(filepath)
        
        return {
            'status': 'deleted',
            'model': model_name
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Delete failed: {str(e)}")


# ============================================
# Inference Service Endpoints
# ============================================

@router.get("/status", response_model=RLStatusResponse)
async def get_rl_status():
    """
    Get RL inference service status
    
    Returns current model status, statistics, and readiness.
    """
    inference_service = get_inference_service()
    stats = inference_service.get_statistics()
    
    return RLStatusResponse(
        model_loaded=stats.get('modelLoaded', False),
        model_path=stats.get('modelPath'),
        inference_count=stats.get('inferenceCount', 0),
        avg_inference_time=stats.get('avgInferenceTime', 0.0),
        max_inference_time=stats.get('maxInferenceTime', 0.0),
        slow_inference_count=stats.get('slowInferenceCount', 0),
        device=stats.get('device'),
        ready=inference_service.is_ready()
    )


@router.post("/reload")
async def reload_model():
    """
    Reload current model (e.g., after retraining)
    
    Reloads the model from disk without changing the active model path.
    """
    inference_service = get_inference_service()
    
    if not inference_service.model_path:
        raise HTTPException(status_code=400, detail="No model loaded")
    
    try:
        inference_service.reload_model()
        
        return {
            'status': 'reloaded',
            'model': inference_service.model_path,
            'timestamp': time.time()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/predict", response_model=PredictionResponse)
async def predict(request: PredictionRequest):
    """
    Run RL inference
    
    Takes a 63-dimensional observation and returns 9 actions (one per junction).
    Each action is 0-3 representing N/E/S/W direction.
    """
    import numpy as np
    
    inference_service = get_inference_service()
    
    if not inference_service.is_ready():
        raise HTTPException(status_code=503, detail="RL model not loaded")
    
    try:
        observation = np.array(request.observation, dtype=np.float32)
        
        start_time = time.time()
        actions, _ = inference_service.predict(
            observation, 
            deterministic=request.deterministic
        )
        inference_time = (time.time() - start_time) * 1000
        
        return PredictionResponse(
            actions=actions.tolist() if hasattr(actions, 'tolist') else list(actions),
            inference_time_ms=round(inference_time, 2)
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")


@router.get("/model-info")
async def get_model_info():
    """
    Get detailed information about loaded model
    """
    inference_service = get_inference_service()
    
    if not inference_service.is_ready():
        return {
            'loaded': False,
            'message': 'No model loaded'
        }
    
    return inference_service.get_model_info()


# ============================================
# Training Control Endpoints (Future)
# ============================================

@router.post("/train/start")
async def start_training(timesteps: int = 100000, quick: bool = False):
    """
    Start RL training (async, background task)
    
    Note: For hackathon, training is done via CLI.
    This endpoint is a placeholder for future async training.
    """
    return {
        'status': 'not_implemented',
        'message': 'Use CLI for training: python train_rl.py train --timesteps 100000',
        'hint': 'For quick test: python train_rl.py train --quick'
    }


@router.get("/train/status")
async def get_training_status():
    """
    Get current training status
    
    Returns training progress if training is in progress.
    """
    return {
        'is_training': False,
        'message': 'No training in progress. Use CLI to train.'
    }


@router.post("/train/stop")
async def stop_training():
    """
    Stop ongoing training
    """
    return {
        'status': 'not_implemented',
        'message': 'Training control via API not yet implemented'
    }

