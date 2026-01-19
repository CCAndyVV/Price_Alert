"""Configuration management for Polymarket Price Monitor."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml
from dotenv import load_dotenv


@dataclass
class Config:
    """Application configuration."""

    # Monitoring settings
    poll_interval_seconds: int = 300  # 5 minutes
    price_change_threshold_percent: float = 3.0
    min_volume_usd: float = 0

    # API settings
    gamma_api_url: str = "https://gamma-api.polymarket.com"
    clob_api_url: str = "https://clob.polymarket.com"
    api_page_size: int = 100
    api_request_delay: float = 0.1

    # Telegram settings
    telegram_enabled: bool = True
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    @classmethod
    def load(cls, config_path: Optional[str] = None, env_path: Optional[str] = None) -> "Config":
        """
        Load configuration from YAML file and environment variables.

        Args:
            config_path: Path to settings.yaml file
            env_path: Path to .env file

        Returns:
            Loaded Config object
        """
        # Load environment variables
        if env_path:
            load_dotenv(env_path)
        else:
            load_dotenv()

        config = cls()

        # Load YAML config if provided
        if config_path and Path(config_path).exists():
            with open(config_path, "r") as f:
                yaml_config = yaml.safe_load(f) or {}

            # Monitoring settings
            monitoring = yaml_config.get("monitoring", {})
            if "poll_interval_seconds" in monitoring:
                config.poll_interval_seconds = monitoring["poll_interval_seconds"]
            if "price_change_threshold_percent" in monitoring:
                config.price_change_threshold_percent = monitoring["price_change_threshold_percent"]
            if "min_volume_usd" in monitoring:
                config.min_volume_usd = monitoring["min_volume_usd"]

            # API settings
            api = yaml_config.get("api", {})
            if "gamma_url" in api:
                config.gamma_api_url = api["gamma_url"]
            if "clob_url" in api:
                config.clob_api_url = api["clob_url"]
            if "page_size" in api:
                config.api_page_size = api["page_size"]

            # Telegram settings
            telegram = yaml_config.get("telegram", {})
            if "enabled" in telegram:
                config.telegram_enabled = telegram["enabled"]

        # Load sensitive values from environment
        config.telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        config.telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID", "")

        return config

    def validate(self) -> list[str]:
        """
        Validate the configuration.

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        if self.poll_interval_seconds < 10:
            errors.append("poll_interval_seconds must be at least 10")

        if self.price_change_threshold_percent <= 0:
            errors.append("price_change_threshold_percent must be positive")

        if self.min_volume_usd < 0:
            errors.append("min_volume_usd cannot be negative")

        if self.telegram_enabled:
            if not self.telegram_bot_token:
                errors.append("TELEGRAM_BOT_TOKEN environment variable not set")
            if not self.telegram_chat_id:
                errors.append("TELEGRAM_CHAT_ID environment variable not set")

        return errors

    def to_dict(self) -> dict:
        """Convert config to dictionary (excluding sensitive values)."""
        return {
            "poll_interval_seconds": self.poll_interval_seconds,
            "price_change_threshold_percent": self.price_change_threshold_percent,
            "min_volume_usd": self.min_volume_usd,
            "telegram_enabled": self.telegram_enabled,
            "api_page_size": self.api_page_size,
        }


def get_default_config_path() -> str:
    """Get the default path to settings.yaml."""
    # Try to find settings.yaml relative to the project
    possible_paths = [
        Path(__file__).parent.parent / "resources" / "config" / "settings.yaml",
        Path("src/main/resources/config/settings.yaml"),
        Path("settings.yaml"),
    ]

    for path in possible_paths:
        if path.exists():
            return str(path)

    return str(possible_paths[0])  # Return first option even if it doesn't exist
