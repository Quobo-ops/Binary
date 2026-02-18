"""FeedbackManager — corrections, approvals, and rejections."""

from __future__ import annotations

import logging
from typing import Any

from aecos.finetune.collector import InteractionCollector

logger = logging.getLogger(__name__)

# Confidence threshold below which interactions are flagged for review
REVIEW_THRESHOLD = 0.75


class FeedbackManager:
    """Manage human feedback on parser interactions.

    Parameters
    ----------
    collector:
        The InteractionCollector instance to read/write interactions.
    """

    def __init__(self, collector: InteractionCollector) -> None:
        self.collector = collector

    def record_correction(
        self,
        interaction_id: str,
        corrected_spec: dict[str, Any],
    ) -> bool:
        """Mark an interaction as corrected with the right output.

        Parameters
        ----------
        interaction_id:
            The interaction to correct.
        corrected_spec:
            The corrected specification dict.

        Returns True if successful.
        """
        return self.collector.update_interaction(interaction_id, {
            "corrected": True,
            "correction": corrected_spec,
            "accepted": False,
        })

    def record_approval(self, interaction_id: str) -> bool:
        """Confirm that the interaction output was correct."""
        return self.collector.update_interaction(interaction_id, {
            "accepted": True,
            "corrected": False,
        })

    def record_rejection(self, interaction_id: str, reason: str) -> bool:
        """Mark an interaction output as wrong.

        Parameters
        ----------
        interaction_id:
            The interaction to reject.
        reason:
            Why the output was incorrect.
        """
        return self.collector.update_interaction(interaction_id, {
            "rejected": True,
            "accepted": False,
            "rejection_reason": reason,
        })

    def get_pending_reviews(self) -> list[dict[str, Any]]:
        """Get interactions needing human review.

        Returns interactions with confidence below REVIEW_THRESHOLD
        that haven't been reviewed yet.
        """
        interactions = self.collector.list_interactions()
        pending: list[dict[str, Any]] = []

        for record in interactions:
            confidence = record.get("confidence", 0)
            corrected = record.get("corrected", False)
            rejected = record.get("rejected", False)

            # Already reviewed
            if corrected or rejected:
                continue

            # Below threshold — needs review
            if confidence < REVIEW_THRESHOLD:
                pending.append(record)

        return pending
