"""TrainingManager — orchestrates LoRA fine-tuning."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class TrainingConfig:
    """Training configuration for LoRA fine-tuning."""

    base_model: str = "llama3.3:70b"
    dataset_path: str = ""
    output_name: str = "aecos-finetuned"
    lora_r: int = 64
    lora_alpha: int = 16
    lora_dropout: float = 0.05
    learning_rate: float = 2e-5
    num_epochs: int = 3
    batch_size: int = 2
    output_dir: str = "fine_tuning/models"

    def to_dict(self) -> dict[str, Any]:
        return {
            "base_model": self.base_model,
            "dataset_path": self.dataset_path,
            "output_name": self.output_name,
            "lora_r": self.lora_r,
            "lora_alpha": self.lora_alpha,
            "lora_dropout": self.lora_dropout,
            "learning_rate": self.learning_rate,
            "num_epochs": self.num_epochs,
            "batch_size": self.batch_size,
            "output_dir": self.output_dir,
        }


@dataclass
class TrainingResult:
    """Result of a training run."""

    success: bool
    model_path: Path | None = None
    message: str = ""
    config: dict[str, Any] = field(default_factory=dict)
    mock: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "model_path": str(self.model_path) if self.model_path else None,
            "message": self.message,
            "config": self.config,
            "mock": self.mock,
        }


class TrainingManager:
    """Manage LoRA fine-tuning of LLMs for AEC OS.

    When no GPU or training framework is available, operates in
    mock/dry-run mode: logs warnings and returns mock results.

    Parameters
    ----------
    models_dir:
        Directory for output models (default: fine_tuning/models/).
    """

    def __init__(self, models_dir: str | Path | None = None) -> None:
        if models_dir is None:
            models_dir = Path("fine_tuning") / "models"
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)

    def prepare_config(
        self,
        base_model: str = "llama3.3:70b",
        dataset_path: str | Path = "",
        output_name: str = "aecos-finetuned",
    ) -> TrainingConfig:
        """Create a training configuration.

        Parameters
        ----------
        base_model:
            Base model identifier.
        dataset_path:
            Path to the training dataset JSONL.
        output_name:
            Name for the output model.

        Returns
        -------
        TrainingConfig
        """
        return TrainingConfig(
            base_model=base_model,
            dataset_path=str(dataset_path),
            output_name=output_name,
            output_dir=str(self.models_dir),
        )

    def train(self, config: TrainingConfig) -> TrainingResult:
        """Launch training.

        When axolotl/unsloth is available and a GPU is present, runs
        actual fine-tuning. Otherwise, returns a mock result.

        Parameters
        ----------
        config:
            Training configuration.

        Returns
        -------
        TrainingResult
        """
        if not self._is_training_available():
            logger.warning(
                "No GPU or training framework (axolotl/unsloth) available. "
                "Running in mock/dry-run mode."
            )
            return self._mock_train(config)

        return self._real_train(config)

    def _is_training_available(self) -> bool:
        """Check if training frameworks and GPU are available."""
        try:
            import torch
            if not torch.cuda.is_available():
                return False
        except ImportError:
            return False

        # Check for training framework
        try:
            import axolotl  # noqa: F401
            return True
        except ImportError:
            pass

        try:
            import unsloth  # noqa: F401
            return True
        except ImportError:
            pass

        return False

    def _mock_train(self, config: TrainingConfig) -> TrainingResult:
        """Return a mock training result for testing."""
        output_path = self.models_dir / config.output_name
        output_path.mkdir(parents=True, exist_ok=True)

        # Write a marker file so we know a "training" happened
        marker = output_path / "training_config.json"
        import json
        marker.write_text(
            json.dumps(config.to_dict(), indent=2), encoding="utf-8",
        )

        return TrainingResult(
            success=True,
            model_path=output_path,
            message=(
                "Mock training completed (no GPU/framework available). "
                "Config saved for manual training."
            ),
            config=config.to_dict(),
            mock=True,
        )

    def _real_train(self, config: TrainingConfig) -> TrainingResult:
        """Run actual training via axolotl or unsloth."""
        import subprocess

        output_path = self.models_dir / config.output_name
        output_path.mkdir(parents=True, exist_ok=True)

        # Write axolotl config
        import json
        import yaml

        axolotl_config = {
            "base_model": config.base_model,
            "model_type": "llama",
            "adapter": "lora",
            "lora_r": config.lora_r,
            "lora_alpha": config.lora_alpha,
            "lora_dropout": config.lora_dropout,
            "learning_rate": config.learning_rate,
            "num_epochs": config.num_epochs,
            "micro_batch_size": config.batch_size,
            "datasets": [{"path": config.dataset_path, "type": "alpaca"}],
            "output_dir": str(output_path),
        }

        config_path = output_path / "config.yaml"
        config_path.write_text(
            yaml.dump(axolotl_config, default_flow_style=False),
            encoding="utf-8",
        )

        try:
            result = subprocess.run(
                ["accelerate", "launch", "-m", "axolotl.cli.train", str(config_path)],
                capture_output=True,
                text=True,
                timeout=3600 * 12,
            )
            if result.returncode == 0:
                return TrainingResult(
                    success=True,
                    model_path=output_path,
                    message="Training completed successfully.",
                    config=config.to_dict(),
                )
            else:
                return TrainingResult(
                    success=False,
                    message=f"Training failed: {result.stderr[:500]}",
                    config=config.to_dict(),
                )
        except Exception as exc:
            return TrainingResult(
                success=False,
                message=f"Training error: {exc}",
                config=config.to_dict(),
            )
