
import json
import logging
from pathlib import Path
from pydantic import BaseModel
from typing import List, Optional

logger = logging.getLogger(__name__)

SETTINGS_FILE = Path("settings.json")

class ModelConfig(BaseModel):
    id: str
    name: str
    provider: str = "google" # For now, mainly google

class ApiKeyConfig(BaseModel):
    id: str
    name: str # e.g. "Personal Key", "Work Key"
    key: str
    provider: str = "google"
    created_at: str # ISO timestamp

class AppConfig(BaseModel):
    google_api_key: Optional[str] = None # Deprecated, use api_keys[0] or active one
    active_model_id: str = "gemini-2.5-flash"
    active_api_key_id: Optional[str] = "test-key-1"
    system_instruction: str = ""
    api_keys: List[ApiKeyConfig] = [
        ApiKeyConfig(id="test-key-1", name="Test Key 1", key="AIzaSyCVek5_adXj2pMlGBaV9O25PjPSFyNrrOA", created_at="2025-12-25"),
        ApiKeyConfig(id="test-key-2", name="Test Key 2", key="AIzaSyD6qWUb7_kWo9A_6lOfA7qydjy-RYijkAk", created_at="2025-12-25"),
        ApiKeyConfig(id="test-key-3", name="Test Key 3", key="AIzaSyARV4nqta20-P0oRGuQqmNVVxJNRQY2xS0", created_at="2025-12-25"),
        ApiKeyConfig(id="test-key-4", name="Test Key 4", key="AIzaSyC5gRvOVsC8hwCQm9p77Hfyx2MAbwK3I0s", created_at="2025-12-25"),
    ]
    models: List[ModelConfig] = [
        ModelConfig(id="gemini-2.5-flash", name="Gemini 2.5 Flash"),
        ModelConfig(id="gemini-2.5-flash-lite-preview-09-2025", name="Gemini 2.5 Flash Lite Preview (09-2025)"),
        ModelConfig(id="gemini-2.5-flash-lite", name="Gemini 2.5 Flash Lite"),
        ModelConfig(id="gemini-2.5-flash-preview-09-2025", name="Gemini 2.5 Flash Preview (09-2025)"),
    ]

    class Config:
        frozen = False

class SettingsManager:
    _instance = None
    _config: AppConfig = AppConfig()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SettingsManager, cls).__new__(cls)
            cls._instance.load()
        return cls._instance

    def load(self):
        """Load settings from JSON file"""
        if SETTINGS_FILE.exists():
            try:
                with open(SETTINGS_FILE, "r") as f:
                    data = json.load(f)
                    self._config = AppConfig(**data)
                logger.info("Settings loaded from settings.json")
            except Exception as e:
                logger.error(f"Failed to load settings.json: {e}")
                self._config = AppConfig()
        else:
            import os
            logger.info(f"No settings.json found at {SETTINGS_FILE.absolute()} (CWD: {os.getcwd()}), using defaults.")
            self.save() # Initialize file

    def save(self):
        """Save current settings to JSON file"""
        try:
            with open(SETTINGS_FILE, "w") as f:
                json.dump(self._config.model_dump(), f, indent=4)
            logger.info("Settings saved to settings.json")
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")

    def get_config(self) -> AppConfig:
        return self._config

    def get_active_key(self) -> Optional[str]:
        """Get the actual key string of the active API key"""
        if self._config.active_api_key_id:
            for k in self._config.api_keys:
                if k.id == self._config.active_api_key_id:
                    return k.key
        
        # Fallback to first key if exists
        if self._config.api_keys:
            return self._config.api_keys[0].key
            
        return self._config.google_api_key

    def update_config(self, updates: dict):
        """Update config with a dictionary of values"""
        current_data = self._config.model_dump()
        current_data.update(updates)
        self._config = AppConfig(**current_data)
        self.save()

def get_settings_manager() -> SettingsManager:
    return SettingsManager()
