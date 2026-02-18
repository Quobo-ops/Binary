"""ModelDeployer — registers and rolls back Ollama models."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class ModelDeployer:
    """Manage model registration and deployment with Ollama.

    When Ollama is unavailable, stores metadata only and logs
    instructions for manual deployment.

    Parameters
    ----------
    registry_path:
        Path to the model registry JSON file
        (default: fine_tuning/registry.json).
    """

    def __init__(self, registry_path: str | Path | None = None) -> None:
        if registry_path is None:
            registry_path = Path("fine_tuning") / "registry.json"
        self._registry_path = Path(registry_path)
        self._registry: dict[str, list[dict[str, Any]]] = {}
        self._load_registry()

    def _load_registry(self) -> None:
        """Load registry from disk."""
        if self._registry_path.is_file():
            try:
                self._registry = json.loads(
                    self._registry_path.read_text(encoding="utf-8")
                )
            except (json.JSONDecodeError, OSError):
                self._registry = {}

    def _save_registry(self) -> None:
        """Persist registry to disk."""
        self._registry_path.parent.mkdir(parents=True, exist_ok=True)
        self._registry_path.write_text(
            json.dumps(self._registry, indent=2, default=str),
            encoding="utf-8",
        )

    def register_model(
        self,
        adapter_path: str | Path,
        model_name: str,
        version: str,
    ) -> dict[str, Any]:
        """Register a fine-tuned model adapter.

        If Ollama is available, registers the model. Otherwise, stores
        metadata for manual deployment.

        Parameters
        ----------
        adapter_path:
            Path to the LoRA adapter weights directory.
        model_name:
            Name for the model in the registry.
        version:
            Version string for the model.

        Returns
        -------
        dict
            Registration metadata.
        """
        entry = {
            "version": version,
            "adapter_path": str(adapter_path),
            "registered_at": time.time(),
            "deployed": False,
        }

        if self._is_ollama_available():
            try:
                self._deploy_to_ollama(adapter_path, model_name, version)
                entry["deployed"] = True
                logger.info("Deployed model %s v%s to Ollama", model_name, version)
            except Exception as exc:
                logger.warning("Ollama deployment failed: %s", exc)
                entry["deploy_error"] = str(exc)
        else:
            logger.warning(
                "Ollama not available. Model registered locally only. "
                "To deploy manually: ollama create %s -f Modelfile",
                model_name,
            )

        # Store in registry
        if model_name not in self._registry:
            self._registry[model_name] = []
        self._registry[model_name].append(entry)
        self._save_registry()

        return entry

    def rollback(self, model_name: str, to_version: str) -> dict[str, Any] | None:
        """Roll back to a previous model version.

        Parameters
        ----------
        model_name:
            The model name in the registry.
        to_version:
            The target version to roll back to.

        Returns
        -------
        dict or None
            The restored version entry, or None if not found.
        """
        versions = self._registry.get(model_name, [])

        for entry in versions:
            if entry.get("version") == to_version:
                if self._is_ollama_available():
                    try:
                        self._deploy_to_ollama(
                            entry["adapter_path"], model_name, to_version,
                        )
                        entry["deployed"] = True
                    except Exception as exc:
                        logger.warning("Rollback deployment failed: %s", exc)

                self._save_registry()
                return entry

        return None

    def list_models(self) -> dict[str, list[dict[str, Any]]]:
        """Return all registered models and their versions."""
        return dict(self._registry)

    def _is_ollama_available(self) -> bool:
        """Check if Ollama is available."""
        import subprocess

        try:
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True, text=True, timeout=5,
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            return False

    def _deploy_to_ollama(
        self,
        adapter_path: str | Path,
        model_name: str,
        version: str,
    ) -> None:
        """Deploy a model to Ollama."""
        import subprocess

        model_tag = f"{model_name}:{version}"
        modelfile_content = f"FROM {adapter_path}\n"

        # Write temporary Modelfile
        adapter_dir = Path(adapter_path)
        modelfile = adapter_dir / "Modelfile"
        modelfile.write_text(modelfile_content, encoding="utf-8")

        result = subprocess.run(
            ["ollama", "create", model_tag, "-f", str(modelfile)],
            capture_output=True, text=True, timeout=300,
        )

        if result.returncode != 0:
            raise RuntimeError(f"Ollama create failed: {result.stderr}")
