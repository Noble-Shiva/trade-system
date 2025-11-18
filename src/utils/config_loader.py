"""
Configuration Loader
Loads configuration from YAML file and environment variables
"""

import os
import yaml
from pathlib import Path
from dotenv import load_dotenv


class ConfigLoader:
    """Load and manage application configuration"""

    def __init__(self, config_path=None):
        """
        Initialize configuration loader

        Args:
            config_path: Path to config.yaml file (optional)
        """
        # Load environment variables from .env file
        env_path = Path(__file__).parent.parent.parent / '.env'
        load_dotenv(env_path)

        # Default config path
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent / 'config' / 'config.yaml'

        self.config_path = Path(config_path)
        self.config = self._load_config()

    def _load_config(self):
        """Load configuration from YAML file"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")

        with open(self.config_path, 'r') as f:
            config = yaml.safe_load(f)

        # Replace environment variable placeholders
        config = self._replace_env_vars(config)

        return config

    def _replace_env_vars(self, config):
        """Recursively replace ${VAR_NAME} with environment variables"""
        if isinstance(config, dict):
            return {k: self._replace_env_vars(v) for k, v in config.items()}
        elif isinstance(config, list):
            return [self._replace_env_vars(item) for item in config]
        elif isinstance(config, str) and config.startswith('${') and config.endswith('}'):
            var_name = config[2:-1]
            return os.getenv(var_name, config)
        else:
            return config

    def get(self, *keys, default=None):
        """
        Get configuration value using dot notation

        Args:
            *keys: Keys to navigate the config dict
            default: Default value if key not found

        Returns:
            Configuration value

        Example:
            config.get('trading', 'initial_capital')
        """
        value = self.config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value

    def __getitem__(self, key):
        """Allow dict-like access"""
        return self.config[key]

    def __repr__(self):
        return f"ConfigLoader(config_path='{self.config_path}')"


# Create global config instance
config = ConfigLoader()


if __name__ == "__main__":
    # Test configuration loading
    print("Testing Configuration Loader...")
    print("-" * 60)

    cfg = ConfigLoader()

    print(f"Mode: {cfg.get('general', 'mode')}")
    print(f"Initial Capital: ₹{cfg.get('trading', 'initial_capital'):,}")
    print(f"Max Positions: {cfg.get('trading', 'max_open_positions')}")
    print(f"Daily Loss Limit: ₹{cfg.get('trading', 'max_daily_loss_amount')}")
    print(f"Broker: {cfg.get('broker', 'name')}")

    print("\n✅ Configuration loaded successfully!")
