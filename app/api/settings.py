
from fastapi import APIRouter, HTTPException, Body
from app.core.settings_manager import get_settings_manager, AppConfig, ModelConfig, ApiKeyConfig
from pydantic import BaseModel

router = APIRouter()
settings_manager = get_settings_manager()

class SettingsUpdate(BaseModel):
    google_api_key: str | None = None
    active_model_id: str | None = None
    system_instruction: str | None = None

@router.get("/", response_model=AppConfig)
async def get_settings():
    return settings_manager.get_config()

@router.post("/", response_model=AppConfig)
async def update_settings(update: SettingsUpdate):
    updates = update.model_dump(exclude_unset=True)
    if updates:
        settings_manager.update_config(updates)
    return settings_manager.get_config()

@router.post("/models", response_model=AppConfig)
async def add_model(model: ModelConfig):
    config = settings_manager.get_config()
    if any(m.id == model.id for m in config.models):
        raise HTTPException(status_code=400, detail="Model ID already exists")
    
    new_models = config.models + [model]
    settings_manager.update_config({"models": new_models})
    return settings_manager.get_config()

@router.put("/models/{model_id}", response_model=AppConfig)
async def update_model(model_id: str, model_update: ModelConfig):
    config = settings_manager.get_config()
    
    # Check if we are renaming the ID and if it conflicts
    if model_id != model_update.id and any(m.id == model_update.id for m in config.models):
         raise HTTPException(status_code=400, detail="New Model ID already exists")

    new_models = []
    found = False
    for m in config.models:
        if m.id == model_id:
            new_models.append(model_update)
            found = True
        else:
            new_models.append(m)
    
    if not found:
        raise HTTPException(status_code=404, detail="Model not found")
        
    settings_manager.update_config({"models": new_models})
    return settings_manager.get_config()

@router.delete("/models/{model_id}", response_model=AppConfig)
async def delete_model(model_id: str):
    config = settings_manager.get_config()
    
    # Prevent deleting active model
    if config.active_model_id == model_id:
        raise HTTPException(status_code=400, detail="Cannot delete the currently active model")

    new_models = [m for m in config.models if m.id != model_id]
    if len(new_models) == len(config.models):
         raise HTTPException(status_code=404, detail="Model not found")

    settings_manager.update_config({"models": new_models})
    return settings_manager.get_config()
@router.post("/keys", response_model=AppConfig)
async def add_api_key(key_config: ApiKeyConfig):
    config = settings_manager.get_config()
    # Check duplicate ID
    if any(k.id == key_config.id for k in config.api_keys):
         raise HTTPException(status_code=400, detail="Key ID already exists")

    new_keys = config.api_keys + [key_config]
    settings_manager.update_config({"api_keys": new_keys})
    return settings_manager.get_config()

@router.delete("/keys/{key_id}", response_model=AppConfig)
async def delete_api_key(key_id: str):
    config = settings_manager.get_config()
    new_keys = [k for k in config.api_keys if k.id != key_id]
    if len(new_keys) == len(config.api_keys):
         raise HTTPException(status_code=404, detail="Key not found")
    
    settings_manager.update_config({"api_keys": new_keys})
    return settings_manager.get_config()
