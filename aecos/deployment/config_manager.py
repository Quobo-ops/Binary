"""ConfigManager — environment profiles and secrets template."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# All known configuration keys with defaults
_CONFIG_KEYS: dict[str, dict[str, Any]] = {
    "AECOS_ENV": {"default": "development", "description": "Environment profile"},
    "AECOS_PROJECT_ROOT": {"default": ".", "description": "Project root directory"},
    "AECOS_AUTO_COMMIT": {"default": "true", "description": "Auto-commit on mutations"},
    "OLLAMA_HOST": {"default": "http://localhost:11434", "description": "Ollama LLM server"},
    "SPECKLE_TOKEN": {"default": "", "description": "Speckle API token (secret)"},
    "SPECKLE_SERVER": {"default": "https://speckle.xyz", "description": "Speckle server URL"},
    "SLACK_WEBHOOK": {"default": "", "description": "Slack webhook URL (secret)"},
    "TEAMS_WEBHOOK": {"default": "", "description": "MS Teams webhook URL (secret)"},
    "AECOS_ENCRYPTION_KEY": {"default": "", "description": "Default encryption key (secret)"},
    "AECOS_LOG_LEVEL": {"default": "INFO", "description": "Logging level"},
    "AECOS_AUDIT_DB": {"default": "audit.db", "description": "Audit database path"},
    "AECOS_ANALYTICS_DB": {"default": "analytics.db", "description": "Analytics database path"},
    "AECOS_COMPLIANCE_DB": {"default": ":memory:", "description": "Compliance database path"},
    "AECOS_DOCKER_IMAGE": {"default": "aecos:latest", "description": "Docker image tag"},
}

_PROFILES: dict[str, dict[str, str]] = {
    "development": {
        "AECOS_ENV": "development",
        "AECOS_LOG_LEVEL": "DEBUG",
        "AECOS_AUTO_COMMIT": "true",
    },
    "production": {
        "AECOS_ENV": "production",
        "AECOS_LOG_LEVEL": "WARNING",
        "AECOS_AUTO_COMMIT": "true",
    },
    "testing": {
        "AECOS_ENV": "testing",
        "AECOS_LOG_LEVEL": "DEBUG",
        "AECOS_AUTO_COMMIT": "false",
        "AECOS_COMPLIANCE_DB": ":memory:",
        "AECOS_AUDIT_DB": ":memory:",
        "AECOS_ANALYTICS_DB": ":memory:",
    },
}


class ConfigManager:
    """Manage AEC OS configuration across environments."""

    def generate_env_template(self, project_path: str | Path) -> Path:
        """Create .env.example with all config keys.

        Returns the path to the generated file.
        """
        root = Path(project_path)
        env_path = root / ".env.example"

        lines = ["# AEC OS Configuration Template", "# Copy to .env and fill in values", ""]
        for key, info in _CONFIG_KEYS.items():
            lines.append(f"# {info['description']}")
            lines.append(f"{key}={info['default']}")
            lines.append("")

        env_path.write_text("\n".join(lines), encoding="utf-8")
        return env_path

    def load_config(self, project_path: str | Path) -> dict[str, str]:
        """Load merged config: defaults -> profile -> config.json -> .env -> env vars.

        Returns a flat dict of configuration values.
        """
        root = Path(project_path)
        config: dict[str, str] = {}

        # 1. Defaults
        for key, info in _CONFIG_KEYS.items():
            config[key] = str(info["default"])

        # 2. Profile overrides
        env_name = os.environ.get("AECOS_ENV", config.get("AECOS_ENV", "development"))
        profile = _PROFILES.get(env_name, {})
        config.update(profile)

        # 3. .aecos/config.json
        config_json = root / ".aecos" / "config.json"
        if config_json.is_file():
            try:
                data = json.loads(config_json.read_text(encoding="utf-8"))
                for k, v in data.items():
                    config[k] = str(v)
            except (json.JSONDecodeError, OSError):
                logger.debug("Could not read config.json", exc_info=True)

        # 4. .env file
        env_file = root / ".env"
        if env_file.is_file():
            try:
                for line in env_file.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        k, v = line.split("=", 1)
                        config[k.strip()] = v.strip()
            except OSError:
                pass

        # 5. Environment variables override all
        for key in _CONFIG_KEYS:
            env_val = os.environ.get(key)
            if env_val is not None:
                config[key] = env_val

        return config
