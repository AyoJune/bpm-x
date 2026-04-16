"""
Config Loader - Reads configuration from YAML/JSON files
Manages user settings like naming templates, library paths, etc.
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

try:
    import json
    JSON_AVAILABLE = True
except ImportError:
    JSON_AVAILABLE = False

logger = logging.getLogger(__name__)


class ConfigLoader:
    """Manages application configuration."""
    
    DEFAULT_CONFIG = {
        'library_path': 'data/library',
        'workspace_path': 'data/workspace',
        'naming_template': '{BPM} - {CAMELOT} - {ORIGINAL}',
        'audio_sample_rate': 22050,
        'log_level': 'INFO',
        'auto_organize': False,
        'overwrite_tags': False,
    }
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize config loader.
        
        Args:
            config_file: Path to config file (YAML or JSON)
                        If None, looks for config.yaml in project root
        """
        self.config_file = config_file or Path('config.yaml')
        self.config_file = Path(self.config_file)
        self.config = self.DEFAULT_CONFIG.copy()
        
        if self.config_file.exists():
            self.load()
        else:
            logger.info(f"Config file not found: {self.config_file}")
            logger.info("Using default configuration")
    
    def load(self) -> Dict[str, Any]:
        """
        Load configuration from file.
        
        Supports YAML and JSON formats.
        
        Returns:
            Loaded configuration dictionary
        """
        try:
            if self.config_file.suffix.lower() in {'.yaml', '.yml'}:
                if not YAML_AVAILABLE:
                    raise ImportError("PyYAML required for YAML config files")
                
                with open(self.config_file, 'r') as f:
                    loaded = yaml.safe_load(f) or {}
            
            elif self.config_file.suffix.lower() == '.json':
                if not JSON_AVAILABLE:
                    raise ImportError("json module required for JSON config")
                
                with open(self.config_file, 'r') as f:
                    loaded = json.load(f)
            
            else:
                logger.warning(f"Unsupported config format: {self.config_file.suffix}")
                return self.config
            
            # Merge with defaults
            self.config.update(loaded)
            logger.info(f"Configuration loaded from: {self.config_file}")
            
            return self.config
        
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return self.config
    
    def save(self, config: Optional[Dict[str, Any]] = None) -> bool:
        """
        Save configuration to file.
        
        Args:
            config: Configuration dict (uses current if None)
            
        Returns:
            True if successful
        """
        config = config or self.config
        
        try:
            if self.config_file.suffix.lower() in {'.yaml', '.yml'}:
                if not YAML_AVAILABLE:
                    raise ImportError("PyYAML required for YAML config")
                
                with open(self.config_file, 'w') as f:
                    yaml.dump(config, f, default_flow_style=False)
            
            elif self.config_file.suffix.lower() == '.json':
                if not JSON_AVAILABLE:
                    raise ImportError("json module required")
                
                with open(self.config_file, 'w') as f:
                    json.dump(config, f, indent=2)
            
            else:
                logger.warning(f"Unsupported config format: {self.config_file.suffix}")
                return False
            
            logger.info(f"Configuration saved to: {self.config_file}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get config value."""
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set config value."""
        self.config[key] = value
        logger.debug(f"Config updated: {key} = {value}")
