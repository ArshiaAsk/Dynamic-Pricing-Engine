"""Environment configuration management with validation."""
import os
from typing import Any, Dict, Optional
from pathlib import Path
import yaml
from dotenv import load_dotenv


class ConfigurationError(Exception):
    """Raised when configuration is invalid or missing."""
    pass


class EnvConfig:
    """Manages environment configuration with validation."""
    
    def __init__(self, env: Optional[str] = None):
        """Initialize configuration.
        
        Args:
            env: Environment name (development, production). 
                 If None, reads from APP_ENV or defaults to development.
        """
        # Load .env file if exists
        load_dotenv()
        
        self.env = env or os.getenv("APP_ENV", "development")
        self.config: Dict[str, Any] = {}
        self._load_config()
        self._validate_config()
    
    def _load_config(self):
        """Load configuration from YAML file."""
        config_map = {
            "production": "configs/config.prod.yaml",
            "development": "configs/config.dev.yaml",
            "dev": "configs/config.dev.yaml",
            "prod": "configs/config.prod.yaml"
        }
        
        config_file = config_map.get(self.env, "configs/config.yaml")
        
        if not Path(config_file).exists():
            # Fallback to default config
            config_file = "configs/config.yaml"
        
        try:
            with open(config_file, 'r') as f:
                self.config = yaml.safe_load(f)
        except Exception as e:
            raise ConfigurationError(f"Failed to load config from {config_file}: {e}")
    
    def _validate_config(self):
        """Validate required configuration keys."""
        required_sections = ['model', 'pricing', 'features']
        
        for section in required_sections:
            if section not in self.config:
                raise ConfigurationError(f"Missing required config section: {section}")
        
        # Validate model path exists
        model_path = self.get('pricing.model_path', 'models/demand_model.pkl')
        if not Path(model_path).exists():
            raise ConfigurationError(f"Model file not found: {model_path}")
        
        # Validate features path exists
        features_path = self.get('pricing.feature_columns_path', 'models/features.json')
        if not Path(features_path).exists():
            raise ConfigurationError(f"Features file not found: {features_path}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value using dot notation.
        
        Args:
            key: Configuration key in dot notation (e.g., 'model.max_depth')
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def get_env(self, key: str, default: Any = None) -> Any:
        """Get environment variable with fallback to default.
        
        Args:
            key: Environment variable name
            default: Default value if not found
            
        Returns:
            Environment variable value or default
        """
        return os.getenv(key, default)
    
    def get_bool(self, key: str, default: bool = False) -> bool:
        """Get boolean environment variable.
        
        Args:
            key: Environment variable name
            default: Default value if not found
            
        Returns:
            Boolean value
        """
        value = os.getenv(key, str(default)).lower()
        return value in ('true', '1', 'yes', 'on')
    
    def get_int(self, key: str, default: int = 0) -> int:
        """Get integer environment variable.
        
        Args:
            key: Environment variable name
            default: Default value if not found
            
        Returns:
            Integer value
        """
        try:
            return int(os.getenv(key, default))
        except (ValueError, TypeError):
            return default
    
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.env in ('production', 'prod')
    
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.env in ('development', 'dev')


# Global config instance
_config: Optional[EnvConfig] = None


def get_config() -> EnvConfig:
    """Get global configuration instance."""
    global _config
    if _config is None:
        _config = EnvConfig()
    return _config


def reload_config(env: Optional[str] = None):
    """Reload configuration with optional environment override."""
    global _config
    _config = EnvConfig(env)
    return _config