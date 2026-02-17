"""ClashDetector — pairwise element comparison using AABB overlap.

Uses pure Python bounding box math — no scipy, shapely, or trimesh.
Works entirely from JSON metadata / geometry data.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Default clash tolerance in metres
DEFAULT_TOLERANCE_M = 0.010  # 10mm


class ClashResult:
    """A single clash between two elements."""

    def __init__(
        self,
        element_a_id: str,
        element_b_id: str,
        overlap_volume: float,
        severity: str,
        message: str,
    ) -> None:
        self.element_a_id = element_a_id
        self.element_b_id = element_b_id
        self.overlap_volume = overlap_volume
        self.severity = severity  # "error", "warning"
        self.message = message

    def to_dict(self) -> dict[str, Any]:
        return {
            "element_a_id": self.element_a_id,
            "element_b_id": self.element_b_id,
            "overlap_volume": self.overlap_volume,
            "severity": self.severity,
            "message": self.message,
        }


class ClashDetector:
    """Detect geometric clashes between elements using AABB overlap.

    Parameters
    ----------
    tolerance_m:
        Clash tolerance in metres.  Two bounding boxes that overlap
        by less than this amount are not considered clashes.
    """

    def __init__(self, tolerance_m: float = DEFAULT_TOLERANCE_M) -> None:
        self.tolerance_m = tolerance_m

    def detect(self, element_data_list: list[dict[str, Any]]) -> list[ClashResult]:
        """Run pairwise clash detection on a list of element data dicts.

        Each dict must contain ``geometry.bounding_box`` and
        ``metadata.GlobalId``.

        Returns a list of ClashResult for overlapping pairs.
        """
        clashes: list[ClashResult] = []
        boxes = self._extract_boxes(element_data_list)

        # Pairwise comparison — O(n^2) but fine for element-level checks
        for i in range(len(boxes)):
            for j in range(i + 1, len(boxes)):
                overlap = self._compute_overlap(boxes[i][1], boxes[j][1])
                if overlap > 0:
                    id_a = boxes[i][0]
                    id_b = boxes[j][0]
                    severity = "error" if overlap > 0.001 else "warning"
                    clashes.append(ClashResult(
                        element_a_id=id_a,
                        element_b_id=id_b,
                        overlap_volume=round(overlap, 6),
                        severity=severity,
                        message=f"Bounding box overlap detected ({overlap:.4f} m^3) between {id_a} and {id_b}",
                    ))

        return clashes

    def _extract_boxes(
        self, element_data_list: list[dict[str, Any]]
    ) -> list[tuple[str, tuple[float, float, float, float, float, float]]]:
        """Extract (element_id, (min_x, min_y, min_z, max_x, max_y, max_z)) tuples."""
        boxes = []
        for data in element_data_list:
            geo = data.get("geometry", {})
            bb = geo.get("bounding_box", {})
            element_id = data.get("metadata", {}).get("GlobalId", "unknown")

            try:
                box = (
                    float(bb.get("min_x", 0.0)),
                    float(bb.get("min_y", 0.0)),
                    float(bb.get("min_z", 0.0)),
                    float(bb.get("max_x", 0.0)),
                    float(bb.get("max_y", 0.0)),
                    float(bb.get("max_z", 0.0)),
                )
                # Skip degenerate boxes
                if box[3] > box[0] or box[4] > box[1] or box[5] > box[2]:
                    boxes.append((element_id, box))
            except (TypeError, ValueError):
                logger.debug("Invalid bounding box for %s", element_id)

        return boxes

    def _compute_overlap(
        self,
        a: tuple[float, float, float, float, float, float],
        b: tuple[float, float, float, float, float, float],
    ) -> float:
        """Compute AABB overlap volume.

        Returns 0.0 if no overlap (accounting for tolerance).
        """
        # Expand boxes by tolerance for near-miss detection
        tol = self.tolerance_m

        overlap_x = max(0.0, min(a[3], b[3]) - max(a[0], b[0]) + tol)
        overlap_y = max(0.0, min(a[4], b[4]) - max(a[1], b[1]) + tol)
        overlap_z = max(0.0, min(a[5], b[5]) - max(a[2], b[2]) + tol)

        # All three axes must overlap
        if overlap_x <= tol and min(a[3], b[3]) - max(a[0], b[0]) < -tol:
            return 0.0
        if overlap_y <= tol and min(a[4], b[4]) - max(a[1], b[1]) < -tol:
            return 0.0
        if overlap_z <= tol and min(a[5], b[5]) - max(a[2], b[2]) < -tol:
            return 0.0

        # Actual overlap without tolerance
        real_x = max(0.0, min(a[3], b[3]) - max(a[0], b[0]))
        real_y = max(0.0, min(a[4], b[4]) - max(a[1], b[1]))
        real_z = max(0.0, min(a[5], b[5]) - max(a[2], b[2]))

        return real_x * real_y * real_z
