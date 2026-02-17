**Analytics Dashboard (Roadmap Item 19)**  
**Goal:** Deliver a centralized, interactive, and secure analytics dashboard that provides real-time and historical insights into the performance, usage, and value of the entire AEC OS. The dashboard aggregates key metrics across all prior roadmap components—including extraction volume (Item 1), template reuse rates (Item 2), parse accuracy and fine-tuning progress (Items 6 and 13), compliance pass rates (Item 7), generation throughput (Item 8), cost savings (Item 10), collaboration activity (Item 16), security events (Item 17), and deployment health (Item 18)—enabling data-driven decision-making, productivity tracking, and continuous system optimization for both individual users and enterprise teams.

**Core Architecture**  
- **Frontend:** Modern, responsive web interface built with Streamlit or FastAPI + React (for richer interactivity).  
- **Backend:** SQLite/PostgreSQL data warehouse fed by automated hooks from every module.  
- **Visualization:** Interactive charts (Plotly), tables, and KPI cards with drill-down capability.  
- **Access Control:** Role-based views (individual, team lead, admin) aligned with Security & Audit (Item 17).  
- **Export:** PDF/CSV reports and API endpoints for external BI tools (Power BI, Tableau).

**Key Metrics Tracked**  
- Time saved per element type and project  
- Template reuse percentage and cost avoidance  
- LLM parse accuracy and fine-tuning improvement trends  
- Compliance violation rates and regulatory update impact  
- Cost/schedule accuracy vs. actual project outcomes  
- Collaboration activity (comments, approvals, conflicts resolved)  
- System performance (generation latency, GPU utilization)  
- Security events and audit summary  

**Prerequisites (45 minutes)**  
- Completion of Roadmap Items 1–18.  
- `aecos` package installed in editable mode.  
- `pip install streamlit plotly pandas sqlalchemy psycopg2-binary` (or equivalent for PostgreSQL).  
- Existing audit and log databases (Items 13 and 17) available as data sources.

**Phase 1: Data Warehouse and Collection Hooks (Day 1)**  
Create `aecos/analytics/warehouse.py`:  
```python
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker
from datetime import datetime

engine = sa.create_engine("sqlite:///analytics.db")  # or PostgreSQL URL
Session = sessionmaker(bind=engine)

class AnalyticsEvent(Base):
    __tablename__ = "events"
    id = sa.Column(sa.Integer, primary_key=True)
    timestamp = sa.Column(sa.DateTime, default=datetime.utcnow)
    module = sa.Column(sa.String)
    event_type = sa.Column(sa.String)
    user = sa.Column(sa.String)
    element_guid = sa.Column(sa.String)
    metric_value = sa.Column(sa.Float)
    metadata = sa.Column(sa.JSON)

def record_event(module: str, event_type: str, value: float = None, **kwargs):
    with Session() as session:
        event = AnalyticsEvent(module=module, event_type=event_type, metric_value=value, metadata=kwargs)
        session.add(event)
        session.commit()
```
Add one-line hooks in every major function (e.g., `record_event("parser", "parse_success", confidence=0.97)`).

**Phase 2: Dashboard Backend API (Day 1–2)**  
Implement FastAPI endpoints in `aecos/analytics/api.py`:  
```python
@app.get("/metrics/reuse_rate")
def reuse_rate(period: str = "30d"):
    # SQL query aggregating template usage from library and generation logs
    return {"rate": 78.4, "trend": "+12%"}
```
Support filtering by project, discipline, user, and date range.

**Phase 3: Interactive Frontend (Day 2–3)**  
Build with Streamlit for rapid development (or React for production polish):  
```python
import streamlit as st
st.title("AEC OS Analytics Dashboard")
col1, col2, col3 = st.columns(3)
col1.metric("Time Saved This Month", "142 hours", "↑ 28%")
# Add Plotly charts for trends, heatmaps for discipline usage, etc.
```
Include tabs: Overview, Productivity, Compliance, Cost & Schedule, Collaboration, Security, System Health.

**Phase 4: Advanced Visualizations and Insights (Day 3)**  
- Line charts for accuracy trends over fine-tuning iterations  
- Sankey diagram for element generation → validation → collaboration flow  
- Heatmap of most-reused templates by region and code edition  
- Predictive insights: “At current rate, next regulatory update will affect 47 templates”

**Phase 5: Role-Based Access and Export (Day 4)**  
- Admin view shows all users; individual view limited to personal metrics.  
- One-click PDF/CSV export with cryptographic signature (Item 17) for audit-ready reports.

**Phase 6: CLI and Automated Refresh (Day 4)**  
```bash
aecos analytics launch          # starts local Streamlit server
aecos analytics export --report monthly --format pdf
```
Daily GitHub Action refreshes materialized views in the warehouse.

**Phase 7: Testing, Performance, and Maintenance (Day 5)**  
- Load testing with 10 000 simulated events.  
- Accuracy validation against manual project logs (target ±2 % variance).  
- Responsive design tested on desktop, tablet, and mobile.  
- Data retention policy (configurable: 90 days, 2 years, indefinite with archival).

**Total Time to Working Version 1:** 5–7 days  
**Milestone Verification:** Launching the dashboard displays a complete overview with live KPIs (e.g., “3 247 elements generated, $184 000 estimated cost avoidance, 96.8 % average compliance rate”), interactive drill-down into any module, and a downloadable signed monthly report—all sourced automatically from system logs and fully secured by the existing audit framework.

This analytics dashboard closes the feedback loop for the entire AEC OS, transforming raw activity into actionable intelligence that quantifies ROI, identifies optimization opportunities, and supports strategic scaling decisions.

Implement Phases 1–3 today by adding event-recording hooks to three core modules (parser, generator, and compliance engine) and launching a basic Streamlit prototype. Should any questions arise regarding metric definitions, database schema, or visualization choices, provide the relevant details for immediate refinement.
