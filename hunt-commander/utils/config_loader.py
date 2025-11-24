"""Configuration loader utility."""
import os
import yaml
from typing import Dict, Any
from dotenv import load_dotenv
from pathlib import Path

class ConfigLoader:
    """Loads and manages application configuration."""

    def __init__(self, config_path: str = "config.yaml"):
        """Initialize the config loader.

        Args:
            config_path: Path to the YAML configuration file
        """
        self.config_path = config_path
        self.config: Dict[str, Any] = {}
        load_dotenv()
        self._load_config()

    def _load_config(self):
        """Load configuration from YAML file."""
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Config file not found: {self.config_path}")

        with open(self.config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value by key.

        Args:
            key: Dot-notation key (e.g., 'user_preferences.job_titles')
            default: Default value if key not found

        Returns:
            Configuration value
        """
        keys = key.split('.')
        value = self.config

        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default

        return value

    def get_env(self, key: str, default: str = None) -> str:
        """Get an environment variable.

        Args:
            key: Environment variable name
            default: Default value if not found

        Returns:
            Environment variable value
        """
        return os.getenv(key, default)

    @property
    def user_preferences(self) -> Dict[str, Any]:
        """Get user preferences."""
        return self.config.get('user_preferences', {})

    @property
    def cv_config(self) -> Dict[str, Any]:
        """Get CV configuration."""
        return self.config.get('cv_config', {})

    @property
    def agent_config(self) -> Dict[str, Any]:
        """Get agent configuration."""
        return self.config.get('agent_config', {})

    def create_directories(self):
        """Create necessary directories if they don't exist."""
        directories = [
            'data/jobs',
            'data/cv/tailored',
            'data/logs'
        ]

        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
