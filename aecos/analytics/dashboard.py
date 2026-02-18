"""DashboardGenerator — self-contained HTML report with SVG charts."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from aecos.analytics.kpi import KPICalculator
from aecos.analytics.warehouse import DataWarehouse

logger = logging.getLogger(__name__)


def _svg_bar_chart(data: list[tuple[str, float]], width: int = 600, height: int = 300, title: str = "") -> str:
    """Generate an SVG bar chart."""
    if not data:
        return f'<svg width="{width}" height="{height}"><text x="10" y="30">No data</text></svg>'

    max_val = max(v for _, v in data) or 1
    bar_w = max(10, (width - 80) // len(data))
    gap = 4

    bars = []
    for i, (label, value) in enumerate(data):
        bar_h = int((value / max_val) * (height - 80))
        x = 60 + i * (bar_w + gap)
        y = height - 40 - bar_h

        bars.append(
            f'<rect x="{x}" y="{y}" width="{bar_w}" height="{bar_h}" '
            f'fill="#4A90D9" rx="2"/>'
        )
        # Label
        bars.append(
            f'<text x="{x + bar_w // 2}" y="{height - 20}" '
            f'text-anchor="middle" font-size="10" fill="#666">'
            f'{label[:8]}</text>'
        )
        # Value
        bars.append(
            f'<text x="{x + bar_w // 2}" y="{y - 4}" '
            f'text-anchor="middle" font-size="10" fill="#333">'
            f'{value:.0f}</text>'
        )

    title_el = f'<text x="{width // 2}" y="18" text-anchor="middle" font-size="14" font-weight="bold">{title}</text>' if title else ""

    return (
        f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">'
        f'{title_el}'
        f'<line x1="58" y1="20" x2="58" y2="{height - 38}" stroke="#ccc"/>'
        f'<line x1="58" y1="{height - 38}" x2="{width}" y2="{height - 38}" stroke="#ccc"/>'
        + "".join(bars)
        + "</svg>"
    )


def _svg_line_chart(data: list[tuple[str, float]], width: int = 600, height: int = 300, title: str = "") -> str:
    """Generate an SVG line chart."""
    if not data:
        return f'<svg width="{width}" height="{height}"><text x="10" y="30">No data</text></svg>'

    max_val = max(v for _, v in data) or 1
    n = len(data)
    margin_x, margin_y = 60, 40

    points = []
    for i, (label, value) in enumerate(data):
        x = margin_x + (i * (width - margin_x - 20)) // max(n - 1, 1)
        y = height - margin_y - int((value / max_val) * (height - margin_y - 30))
        points.append((x, y, label, value))

    polyline = " ".join(f"{x},{y}" for x, y, _, _ in points)

    elements = [
        f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">',
    ]
    if title:
        elements.append(
            f'<text x="{width // 2}" y="18" text-anchor="middle" '
            f'font-size="14" font-weight="bold">{title}</text>'
        )

    elements.append(f'<polyline points="{polyline}" fill="none" stroke="#4A90D9" stroke-width="2"/>')

    for x, y, label, value in points:
        elements.append(f'<circle cx="{x}" cy="{y}" r="3" fill="#4A90D9"/>')

    elements.append("</svg>")
    return "".join(elements)


def _kpi_card(label: str, value: Any, unit: str = "") -> str:
    """Generate an HTML KPI card."""
    return (
        '<div style="display:inline-block;margin:10px;padding:20px;'
        'border:1px solid #ddd;border-radius:8px;min-width:180px;text-align:center;">'
        f'<div style="font-size:28px;font-weight:bold;color:#333;">{value}{unit}</div>'
        f'<div style="font-size:13px;color:#888;margin-top:4px;">{label}</div>'
        '</div>'
    )


class DashboardGenerator:
    """Generate a self-contained HTML dashboard.

    Parameters
    ----------
    kpi_calculator:
        KPICalculator instance for metrics.
    warehouse:
        DataWarehouse for chart data.
    """

    def __init__(
        self,
        kpi_calculator: KPICalculator,
        warehouse: DataWarehouse,
    ) -> None:
        self.kpi = kpi_calculator
        self.wh = warehouse

    def generate_html(self, project_path: str | Path) -> Path:
        """Generate and write an HTML dashboard file.

        Returns the path to the generated file.
        """
        root = Path(project_path)
        kpis = self.kpi.all_kpis()

        sections = [
            self._section_overview(kpis),
            self._section_productivity(kpis),
            self._section_compliance(kpis),
            self._section_cost(kpis),
            self._section_collaboration(kpis),
            self._section_security(),
            self._section_health(),
        ]

        html = (
            "<!DOCTYPE html><html><head>"
            "<meta charset='utf-8'>"
            "<title>AEC OS Dashboard</title>"
            "<style>"
            "body{font-family:system-ui,-apple-system,sans-serif;margin:20px;background:#fafafa;color:#333;}"
            "h1{color:#2c3e50;border-bottom:2px solid #4A90D9;padding-bottom:8px;}"
            "h2{color:#34495e;margin-top:30px;}"
            ".section{background:#fff;padding:20px;margin:15px 0;border-radius:8px;box-shadow:0 1px 3px rgba(0,0,0,0.1);}"
            "table{border-collapse:collapse;width:100%;margin:10px 0;}"
            "th,td{border:1px solid #ddd;padding:8px;text-align:left;}"
            "th{background:#f5f5f5;}"
            "</style></head><body>"
            "<h1>AEC OS Analytics Dashboard</h1>"
            + "".join(sections)
            + "</body></html>"
        )

        out_path = root / "DASHBOARD.html"
        out_path.write_text(html, encoding="utf-8")
        return out_path

    def _section_overview(self, kpis: dict[str, Any]) -> str:
        cards = "".join([
            _kpi_card("Parse Accuracy", f"{kpis['parse_accuracy']}", "%"),
            _kpi_card("Template Reuse", f"{kpis['template_reuse_rate']}", "%"),
            _kpi_card("Compliance Pass", f"{kpis['compliance_pass_rate']}", "%"),
            _kpi_card("Elements Generated", kpis["elements_generated"]),
            _kpi_card("Active Users (30d)", kpis["active_users_30d"]),
            _kpi_card("Cost Avoidance", f"${kpis['cost_avoidance_usd']:,.0f}"),
        ])
        return f'<div class="section"><h2>Overview KPIs</h2>{cards}</div>'

    def _section_productivity(self, kpis: dict[str, Any]) -> str:
        trend = self.wh.aggregate("generation", "element_generated", period="month")
        chart = _svg_bar_chart(trend, title="Elements Generated (Monthly)")
        gen_time = kpis["avg_generation_time_ms"]
        card = _kpi_card("Avg Generation Time", f"{gen_time:.0f}", " ms")
        return f'<div class="section"><h2>Productivity</h2>{card}{chart}</div>'

    def _section_compliance(self, kpis: dict[str, Any]) -> str:
        trend = self.wh.aggregate("compliance", "check_completed", period="month")
        chart = _svg_bar_chart(trend, title="Compliance Checks (Monthly)")
        pass_rate = kpis["compliance_pass_rate"]
        card = _kpi_card("Pass Rate", f"{pass_rate}", "%")
        return f'<div class="section"><h2>Compliance</h2>{card}{chart}</div>'

    def _section_cost(self, kpis: dict[str, Any]) -> str:
        cost = kpis["cost_avoidance_usd"]
        card = _kpi_card("Cost Avoidance Estimate", f"${cost:,.0f}")
        return f'<div class="section"><h2>Cost</h2>{card}</div>'

    def _section_collaboration(self, kpis: dict[str, Any]) -> str:
        engagement = kpis["collaboration_engagement"]
        card = _kpi_card("Engagement Score", f"{engagement:.1f}", " / user")
        return f'<div class="section"><h2>Collaboration</h2>{card}</div>'

    def _section_security(self) -> str:
        return '<div class="section"><h2>Security</h2><p>Run <code>scan_security()</code> for latest report.</p></div>'

    def _section_health(self) -> str:
        return '<div class="section"><h2>System Health</h2><p>Run <code>check_health()</code> for status.</p></div>'
