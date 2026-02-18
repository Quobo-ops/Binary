"""ReportExporter — PDF/CSV/JSON/Markdown export."""

from __future__ import annotations

import csv
import io
import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class ReportExporter:
    """Export analytics data in various formats."""

    def export_json(self, kpis: dict[str, Any]) -> str:
        """Export KPIs as structured JSON."""
        return json.dumps({"kpis": kpis}, indent=2)

    def export_csv(self, events: list[dict[str, Any]], path: str | Path) -> Path:
        """Export raw events to CSV.

        Parameters
        ----------
        events:
            List of event dicts from MetricsCollector.
        path:
            Output CSV file path.
        """
        p = Path(path)
        if not events:
            p.write_text("id,timestamp,module,event_type,value,metadata_json,user\n", encoding="utf-8")
            return p

        fieldnames = ["id", "timestamp", "module", "event_type", "value", "metadata_json", "user"]

        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for ev in events:
            writer.writerow(ev)

        p.write_text(buf.getvalue(), encoding="utf-8")
        return p

    def export_markdown(self, kpis: dict[str, Any]) -> str:
        """Export KPIs as a Markdown summary."""
        lines = [
            "# AEC OS Analytics Report",
            "",
            "| KPI | Value |",
            "|-----|-------|",
        ]
        display_names = {
            "parse_accuracy": "Parse Accuracy (%)",
            "template_reuse_rate": "Template Reuse Rate (%)",
            "avg_generation_time_ms": "Avg Generation Time (ms)",
            "compliance_pass_rate": "Compliance Pass Rate (%)",
            "cost_avoidance_usd": "Cost Avoidance ($)",
            "active_users_30d": "Active Users (30d)",
            "elements_generated": "Elements Generated",
            "collaboration_engagement": "Collaboration Engagement",
        }
        for key, value in kpis.items():
            name = display_names.get(key, key)
            lines.append(f"| {name} | {value} |")

        lines.append("")
        return "\n".join(lines)

    def export_html(self, kpis: dict[str, Any]) -> str:
        """Export KPIs as standalone HTML."""
        rows = ""
        for key, value in kpis.items():
            rows += f"<tr><td>{key}</td><td>{value}</td></tr>"

        return (
            "<!DOCTYPE html><html><head><meta charset='utf-8'>"
            "<title>AEC OS Analytics</title>"
            "<style>body{font-family:sans-serif;margin:20px;}table{border-collapse:collapse;}"
            "th,td{border:1px solid #ddd;padding:8px;}th{background:#f5f5f5;}</style>"
            "</head><body><h1>AEC OS Analytics Report</h1>"
            "<table><tr><th>KPI</th><th>Value</th></tr>"
            f"{rows}</table></body></html>"
        )
