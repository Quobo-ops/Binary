"""InteractionCollector — logs every parse request and result."""

from __future__ import annotations

import json
import logging
import time
import uuid
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class InteractionCollector:
    """Collect and store NLP interaction data for fine-tuning.

    Writes each interaction to a JSONL file in the interactions directory.

    Parameters
    ----------
    output_dir:
        Directory for interaction logs (default: fine_tuning/interactions/).
    """

    def __init__(self, output_dir: str | Path | None = None) -> None:
        if output_dir is None:
            output_dir = Path("fine_tuning") / "interactions"
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def log_interaction(
        self,
        prompt: str,
        context: dict[str, Any] | None,
        raw_output: str | None,
        parsed_spec: dict[str, Any] | None,
        confidence: float,
        *,
        accepted: bool = True,
    ) -> str:
        """Log a single interaction.

        Parameters
        ----------
        prompt:
            The user's natural language input.
        context:
            Optional parsing context.
        raw_output:
            Raw output from the LLM/parser.
        parsed_spec:
            The final parsed specification as a dict.
        confidence:
            Confidence score (0.0-1.0).
        accepted:
            Whether the output was accepted (default True).

        Returns
        -------
        str
            The interaction ID.
        """
        interaction_id = str(uuid.uuid4())[:12]
        timestamp = time.time()

        record = {
            "interaction_id": interaction_id,
            "timestamp": timestamp,
            "prompt": prompt,
            "context": context,
            "raw_output": raw_output,
            "parsed_spec": parsed_spec,
            "confidence": confidence,
            "accepted": accepted,
            "corrected": False,
            "correction": None,
            "rejected": False,
            "rejection_reason": None,
        }

        # Write as individual JSONL file
        filename = f"{interaction_id}.jsonl"
        filepath = self.output_dir / filename
        filepath.write_text(
            json.dumps(record, default=str) + "\n", encoding="utf-8",
        )

        logger.debug("Logged interaction %s", interaction_id)
        return interaction_id

    def get_interaction(self, interaction_id: str) -> dict[str, Any] | None:
        """Load a single interaction by ID."""
        filepath = self.output_dir / f"{interaction_id}.jsonl"
        if not filepath.is_file():
            return None
        try:
            line = filepath.read_text(encoding="utf-8").strip()
            return json.loads(line)
        except (json.JSONDecodeError, OSError):
            return None

    def update_interaction(
        self, interaction_id: str, updates: dict[str, Any],
    ) -> bool:
        """Update fields of an existing interaction.

        Returns True if successful.
        """
        record = self.get_interaction(interaction_id)
        if record is None:
            return False

        record.update(updates)
        filepath = self.output_dir / f"{interaction_id}.jsonl"
        filepath.write_text(
            json.dumps(record, default=str) + "\n", encoding="utf-8",
        )
        return True

    def list_interactions(self) -> list[dict[str, Any]]:
        """Load all interactions from the output directory."""
        interactions: list[dict[str, Any]] = []
        for filepath in sorted(self.output_dir.glob("*.jsonl")):
            try:
                line = filepath.read_text(encoding="utf-8").strip()
                if line:
                    interactions.append(json.loads(line))
            except (json.JSONDecodeError, OSError):
                continue
        return interactions
