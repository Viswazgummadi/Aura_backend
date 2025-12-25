
import yaml
import logging
from pathlib import Path
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)

CONFIG_FILE = Path("config.yaml")

class ModelConfig(BaseModel):
    id: str
    name: str
    provider: str = "google"
    model_id: str = "models/gemini-1.5-flash"
    context_window: int = 1000000
    description: str = ""

class ApiKeyConfig(BaseModel):
    id: str
    name: str
    key: str
    provider: str = "google"
    created_at: str

class AppConfig(BaseModel):
    active_model_id: str = "gemini-1.5-flash"
    active_api_key_id: Optional[str] = None
    system_instruction: str = "You are Aura."
    
    api_keys: List[ApiKeyConfig] = []
    models: List[ModelConfig] = []
    
    class Config:
        frozen = False

class SettingsManager:
    _instance = None
    _config: AppConfig = AppConfig()
    _raw_yaml: Dict[str, Any] = {} # Preservation storage

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SettingsManager, cls).__new__(cls)
            cls._instance.load()
        return cls._instance

    def load(self):
        """Load settings from config.yaml"""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r") as f:
                    data = yaml.safe_load(f) or {}
                    
                    if not data:
                        logger.info("config.yaml is empty. Populating defaults.")
                        self._config = AppConfig()
                        self._raw_yaml = {
                            "user_preferences": {
                                "name": "User",
                                "theme": "dark",
                                "gym_schedule": "Mon, Wed, Fri at 7:00 AM"
                            }
                        }
                        self.save()
                        return

                    self._raw_yaml = data # Store for preservation
                    
                    # Map YAML structure to AppConfig Flat Structure
                    active = data.get("active_settings", {})
                    
                    config_dict = {
                        "api_keys": data.get("api_keys", []),
                        "models": data.get("models", []),
                        "active_model_id": active.get("active_model_id", "gemini-1.5-flash"),
                        "active_api_key_id": active.get("active_api_key_id"),
                        "system_instruction": active.get("system_prompt", "")
                    }
                    self._config = AppConfig(**config_dict)
                logger.info("Settings loaded from config.yaml")
            except Exception as e:
                logger.error(f"Failed to load config.yaml: {e}")
                self._config = AppConfig()
        else:
            logger.info("config.yaml not found. Creating default configuration.")
            # Initialize with default structure including user_preferences
            self._config = AppConfig()
            self._raw_yaml = {
                "user_preferences": {
                    "name": "User",
                    "theme": "dark",
                    "gym_schedule": "Mon, Wed, Fri at 7:00 AM" # Default example
                }
            }
            self.save()

    def save(self):
        """Save current settings to config.yaml, preserving unknown fields"""
        try:
            # Get current app config
            current = self._config.dict()
            
            # Update specific sections in raw_yaml
            if "active_settings" not in self._raw_yaml:
                self._raw_yaml["active_settings"] = {}
                
            self._raw_yaml["api_keys"] = current["api_keys"]
            self._raw_yaml["models"] = current["models"]
            self._raw_yaml["active_settings"]["active_model_id"] = current["active_model_id"]
            self._raw_yaml["active_settings"]["active_api_key_id"] = current["active_api_key_id"]
            self._raw_yaml["active_settings"]["system_prompt"] = current["system_instruction"]
            
            # Note: user_preferences and other top-level keys in _raw_yaml remain untouched!
            
            with open(CONFIG_FILE, "w") as f:
                yaml.dump(self._raw_yaml, f, sort_keys=False, indent=2)
            logger.info("Settings saved to config.yaml")
        except Exception as e:
            logger.error(f"Failed to save config.yaml: {e}")

    def get_config(self) -> AppConfig:
        return self._config

    def get_active_key(self) -> Optional[str]:
        if self._config.active_api_key_id:
            for k in self._config.api_keys:
                if k.id == self._config.active_api_key_id:
                    return k.key
        if self._config.api_keys:
            return self._config.api_keys[0].key
        return None

    def get_active_model_resolved_id(self) -> str:
        """Resolve the active model ID to the actual provider model ID."""
        active = self._config.active_model_id
        for m in self._config.models:
            if m.id == active:
                return m.model_id
        return active # Fallback: Assume the active ID is the direct model ID if not found in list

    def update_config(self, updates: dict):
        current_data = self._config.dict()
        current_data.update(updates)
        self._config = AppConfig(**current_data)
        self.save()

def get_settings_manager() -> SettingsManager:
    return SettingsManager()
