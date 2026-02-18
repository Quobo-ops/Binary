"""DatasetBuilder — curates JSONL training datasets from interactions."""

from __future__ import annotations

import json
import logging
import random
import re
import time
from pathlib import Path
from typing import Any

from aecos.finetune.collector import InteractionCollector

logger = logging.getLogger(__name__)


class DatasetBuilder:
    """Build Alpaca-format JSONL training datasets from collected interactions.

    Parameters
    ----------
    collector:
        The InteractionCollector to source interactions from.
    output_dir:
        Directory for generated datasets (default: fine_tuning/datasets/).
    """

    def __init__(
        self,
        collector: InteractionCollector,
        output_dir: str | Path | None = None,
    ) -> None:
        self.collector = collector
        if output_dir is None:
            output_dir = Path("fine_tuning") / "datasets"
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def build_dataset(
        self,
        *,
        min_confidence: float = 0.85,
        include_corrections: bool = True,
        train_split: float = 0.9,
        seed: int = 42,
    ) -> Path:
        """Build a training dataset from approved and corrected interactions.

        Parameters
        ----------
        min_confidence:
            Minimum confidence for auto-approved interactions.
        include_corrections:
            Whether to include manually corrected interactions.
        train_split:
            Fraction for the training set (rest is validation).
        seed:
            Random seed for reproducible splits.

        Returns
        -------
        Path
            Path to the generated training JSONL file.
        """
        interactions = self.collector.list_interactions()
        examples = self._filter_and_convert(
            interactions, min_confidence, include_corrections,
        )
        examples = self._deduplicate(examples)

        # Split
        rng = random.Random(seed)
        rng.shuffle(examples)

        split_idx = max(1, int(len(examples) * train_split))
        train = examples[:split_idx]
        val = examples[split_idx:]

        # Write with timestamp version
        version = int(time.time())
        train_path = self.output_dir / f"v{version}_train.jsonl"
        val_path = self.output_dir / f"v{version}_val.jsonl"

        self._write_jsonl(train_path, train)
        self._write_jsonl(val_path, val)

        logger.info(
            "Built dataset v%d: %d train, %d val examples",
            version, len(train), len(val),
        )
        return train_path

    def _filter_and_convert(
        self,
        interactions: list[dict[str, Any]],
        min_confidence: float,
        include_corrections: bool,
    ) -> list[dict[str, str]]:
        """Filter interactions and convert to Alpaca format."""
        examples: list[dict[str, str]] = []

        for record in interactions:
            # Skip rejected
            if record.get("rejected", False):
                continue

            # Corrected interactions
            if record.get("corrected", False) and include_corrections:
                output = record.get("correction")
                if output:
                    examples.append({
                        "instruction": record.get("prompt", ""),
                        "input": json.dumps(record.get("context") or {}),
                        "output": json.dumps(output, default=str),
                    })
                continue

            # Accepted with sufficient confidence
            if record.get("accepted", False):
                confidence = record.get("confidence", 0)
                if confidence >= min_confidence:
                    output = record.get("parsed_spec")
                    if output:
                        examples.append({
                            "instruction": record.get("prompt", ""),
                            "input": json.dumps(record.get("context") or {}),
                            "output": json.dumps(output, default=str),
                        })

        return examples

    def _deduplicate(
        self, examples: list[dict[str, str]],
    ) -> list[dict[str, str]]:
        """Remove duplicate examples based on normalized prompt similarity."""
        seen: set[str] = set()
        unique: list[dict[str, str]] = []

        for ex in examples:
            key = _normalize_prompt(ex["instruction"])
            if key not in seen:
                seen.add(key)
                unique.append(ex)

        return unique

    @staticmethod
    def _write_jsonl(path: Path, examples: list[dict[str, str]]) -> None:
        """Write examples as JSONL."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            for ex in examples:
                f.write(json.dumps(ex) + "\n")


def _normalize_prompt(text: str) -> str:
    """Normalize a prompt for deduplication: lowercase, collapse whitespace."""
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    return text
