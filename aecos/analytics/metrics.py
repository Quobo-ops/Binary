"""Metric definitions — pre-built event type constants."""

from __future__ import annotations

from pydantic import BaseModel


class MetricDefinition(BaseModel):
    """Definition of a trackable metric."""

    module: str
    event_type: str
    description: str = ""
    unit: str = ""


# Pre-built metric definitions for all modules
METRIC_DEFINITIONS: list[MetricDefinition] = [
    MetricDefinition(
        module="extraction",
        event_type="elements_extracted",
        description="Number of elements extracted from IFC",
        unit="count",
    ),
    MetricDefinition(
        module="parser",
        event_type="parse_completed",
        description="NL parse completed with confidence score",
        unit="confidence",
    ),
    MetricDefinition(
        module="compliance",
        event_type="check_completed",
        description="Compliance check completed",
        unit="pass_fail",
    ),
    MetricDefinition(
        module="generation",
        event_type="element_generated",
        description="Element generated",
        unit="duration_ms",
    ),
    MetricDefinition(
        module="validation",
        event_type="validation_completed",
        description="Validation completed",
        unit="status",
    ),
    MetricDefinition(
        module="cost",
        event_type="estimate_completed",
        description="Cost estimate produced",
        unit="total_usd",
    ),
    MetricDefinition(
        module="template",
        event_type="reuse_count",
        description="Template reused for generation",
        unit="count",
    ),
    MetricDefinition(
        module="collaboration",
        event_type="comment_added",
        description="Comment added to element",
        unit="count",
    ),
    MetricDefinition(
        module="collaboration",
        event_type="task_completed",
        description="Task marked as completed",
        unit="count",
    ),
    MetricDefinition(
        module="collaboration",
        event_type="review_approved",
        description="Review approved",
        unit="count",
    ),
    MetricDefinition(
        module="security",
        event_type="scan_completed",
        description="Security scan completed",
        unit="findings_count",
    ),
    MetricDefinition(
        module="finetune",
        event_type="evaluation_completed",
        description="Model evaluation completed",
        unit="accuracy_score",
    ),
]
