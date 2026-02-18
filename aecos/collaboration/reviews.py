"""ReviewManager — approval/rejection workflows for element reviews."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aecos.collaboration.models import Review

logger = logging.getLogger(__name__)


class ReviewManager:
    """Manage element review workflows stored in .aecos/reviews.json."""

    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root
        self._reviews_path = project_root / ".aecos" / "reviews.json"
        self._reviews_path.parent.mkdir(parents=True, exist_ok=True)

    def _load_reviews(self) -> list[Review]:
        """Load reviews from disk."""
        if not self._reviews_path.is_file():
            return []
        try:
            data = json.loads(self._reviews_path.read_text(encoding="utf-8"))
            return [Review.model_validate(r) for r in data]
        except (json.JSONDecodeError, OSError):
            return []

    def _save_reviews(self, reviews: list[Review]) -> None:
        """Persist reviews to disk."""
        data = [r.model_dump(mode="json") for r in reviews]
        self._reviews_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def request_review(
        self,
        element_id: str,
        reviewer: str,
        notes: str | None = None,
        requested_by: str = "",
    ) -> Review:
        """Request a review for an element.

        Parameters
        ----------
        element_id:
            The element to review.
        reviewer:
            User assigned to review.
        notes:
            Optional notes for the reviewer.
        requested_by:
            User requesting the review.
        """
        review = Review(
            element_id=element_id,
            reviewer=reviewer,
            comments=notes or "",
            requested_by=requested_by,
        )

        reviews = self._load_reviews()
        reviews.append(review)
        self._save_reviews(reviews)

        logger.info("Review %s requested for element %s (reviewer: %s)", review.id, element_id, reviewer)
        return review

    def approve(
        self,
        review_id: str,
        reviewer: str,
        comments: str | None = None,
    ) -> Review | None:
        """Approve a review.

        Parameters
        ----------
        review_id:
            Review identifier.
        reviewer:
            User approving (must match the assigned reviewer).
        comments:
            Optional approval comments.
        """
        reviews = self._load_reviews()
        for review in reviews:
            if review.id == review_id:
                review.status = "approved"
                review.resolved_at = datetime.now(timezone.utc)
                if comments:
                    review.comments = comments
                self._save_reviews(reviews)

                # Update element metadata with reviewed_by
                self._update_element_metadata(review.element_id, reviewer)

                logger.info("Review %s approved by %s", review_id, reviewer)
                return review
        return None

    def reject(
        self,
        review_id: str,
        reviewer: str,
        reason: str,
    ) -> Review | None:
        """Reject a review.

        Parameters
        ----------
        review_id:
            Review identifier.
        reviewer:
            User rejecting.
        reason:
            Reason for rejection (required).
        """
        reviews = self._load_reviews()
        for review in reviews:
            if review.id == review_id:
                review.status = "rejected"
                review.resolved_at = datetime.now(timezone.utc)
                review.comments = reason
                self._save_reviews(reviews)
                logger.info("Review %s rejected by %s: %s", review_id, reviewer, reason)
                return review
        return None

    def get_pending_reviews(self, reviewer: str | None = None) -> list[Review]:
        """Get pending reviews, optionally filtered by reviewer."""
        reviews = self._load_reviews()
        result: list[Review] = []
        for review in reviews:
            if review.status != "pending":
                continue
            if reviewer and review.reviewer != reviewer:
                continue
            result.append(review)
        return result

    def get_review(self, review_id: str) -> Review | None:
        """Get a single review by ID."""
        reviews = self._load_reviews()
        for review in reviews:
            if review.id == review_id:
                return review
        return None

    def _update_element_metadata(self, element_id: str, reviewer: str) -> None:
        """Update element metadata with reviewed_by field on approval."""
        for prefix in ("element_", "template_"):
            for parent in ("elements", "templates"):
                meta_path = (
                    self.project_root / parent / f"{prefix}{element_id}" / "metadata.json"
                )
                if meta_path.is_file():
                    try:
                        meta = json.loads(meta_path.read_text(encoding="utf-8"))
                        meta["reviewed_by"] = reviewer
                        meta["reviewed_at"] = datetime.now(timezone.utc).isoformat()
                        meta_path.write_text(
                            json.dumps(meta, indent=2, default=str),
                            encoding="utf-8",
                        )
                        logger.info("Updated metadata for %s with reviewed_by=%s", element_id, reviewer)
                        return
                    except (json.JSONDecodeError, OSError):
                        logger.debug("Failed to update metadata for %s", element_id, exc_info=True)
