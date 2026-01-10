"""
Configuration Management System

This module provides centralized configuration management using YAML and JSON files.
Supports dot-notation access and hot reloading.
"""

import os
import yaml
import json
from pathlib import Path
from typing import Dict, Any, Optional


class ConfigManager:
    """
    Manage application configuration from YAML and JSON files
    
    Provides:
    - Load all config files on startup
    - Dot notation access: config.get('simulation.citySize.width')
    - Hot reload capability
    - Default values for missing keys
    """
    
    def __init__(self, config_dir: str = None):
        """
        Initialize configuration manager
        
        Args:
            config_dir: Path to config directory (default: project_root/config)
        """
        if config_dir:
            self.config_dir = Path(config_dir)
        else:
            # Find config dir relative to this file
            self.config_dir = Path(__file__).parent.parent / "config"
        
        self.configs: Dict[str, Any] = {}
        self._load_all_configs()
    
    def _load_all_configs(self):
        """Load all configuration files from config directory"""
        # Ensure config directory exists
        if not self.config_dir.exists():
            self.config_dir.mkdir(parents=True, exist_ok=True)
            self._create_default_configs()
        
        # Load YAML configs
        for yaml_file in self.config_dir.glob("*.yaml"):
            try:
                with open(yaml_file, 'r') as f:
                    config_name = yaml_file.stem
                    self.configs[config_name] = yaml.safe_load(f) or {}
                    print(f"   [CONFIG] Loaded: {yaml_file.name}")
            except Exception as e:
                print(f"   [WARN] Failed to load {yaml_file.name}: {e}")
        
        # Load JSON configs
        for json_file in self.config_dir.glob("*.json"):
            try:
                with open(json_file, 'r') as f:
                    config_name = json_file.stem
                    self.configs[config_name] = json.load(f)
                    print(f"   [CONFIG] Loaded: {json_file.name}")
            except Exception as e:
                print(f"   [WARN] Failed to load {json_file.name}: {e}")
    
    def _create_default_configs(self):
        """Create default configuration files if they don't exist"""
        # This will be called if config directory is empty
        print("   Creating default configuration files...")
        # The actual config files will be created separately
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by dot notation key
        
        Examples:
            config.get('simulation.citySize.width')
            config.get('traffic.density.updateInterval')
        
        Args:
            key: Dot-separated key path
            default: Default value if key not found
        
        Returns:
            Configuration value or default
        """
        keys = key.split('.')
        value = self.configs
        
        try:
            for k in keys:
                if isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    return default
            return value
        except (KeyError, TypeError):
            return default
    
    def get_system_config(self) -> Dict[str, Any]:
        """Get system configuration section"""
        return self.configs.get('system', {})
    
    def get_traffic_config(self) -> Dict[str, Any]:
        """Get traffic configuration section"""
        return self.configs.get('traffic', {})
    
    def get_simulation_config(self) -> Dict[str, Any]:
        """Get simulation configuration section"""
        return self.configs.get('simulation', {})
    
    def get_prediction_config(self) -> Dict[str, Any]:
        """Get prediction configuration section"""
        return self.configs.get('prediction', {})
    
    def get_emergency_config(self) -> Dict[str, Any]:
        """Get emergency configuration section"""
        return self.configs.get('emergency', {})
    
    def reload(self):
        """Reload all configuration files"""
        print("[CONFIG] Reloading configuration...")
        self.configs.clear()
        self._load_all_configs()
        print("[OK] Configuration reloaded")
    
    def set(self, key: str, value: Any):
        """
        Set a configuration value (runtime only, not persisted)
        
        Args:
            key: Dot-separated key path
            value: Value to set
        """
        keys = key.split('.')
        config = self.configs
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value


# Global configuration instance
# This will be initialized when the module is imported
try:
    config = ConfigManager()
except Exception as e:
    print(f"[WARN] Config initialization deferred: {e}")
    config = None


def get_config() -> ConfigManager:
    """Get the global configuration instance"""
    global config
    if config is None:
        config = ConfigManager()
    return config

