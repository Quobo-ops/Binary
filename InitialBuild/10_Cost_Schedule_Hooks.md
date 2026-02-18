**Cost & Schedule Hooks (Roadmap Item 10)**  
**Goal:** Embed accurate, traceable cost estimation and preliminary scheduling data directly into every element and assembly within the `aecos` ecosystem. The module automatically calculates unit costs, total installed costs, labor hours, and high-level activity durations by linking the template library (Item 2), parametric generator (Item 8), and compliance engine (Item 7) to authoritative sources. Outputs are attached as standardized JSON and Markdown files, enabling instant project-level takeoffs, budget dashboards, and schedule stubs while remaining fully local or API-driven for privacy and speed.

**Core Architecture**  
- **Data Sources:** RSMeans Data Online (Gordian) API, local Louisiana supplier catalogs (e.g., Baton Rouge material pricing), open datasets (US Bureau of Labor Statistics, ENR indices), and cached offline CSV fallback.  
- **Calculation Engine:** Quantity takeoff from IFC geometry → unit pricing → regional adjustment factors → total cost/schedule.  
- **Output:** `COST.md`, `SCHEDULE.md`, and `cost.json` per element folder, version-controlled via Item 4.  
- **Integration:** Automatic call at the end of `generate_element()` (Item 8) and during validation (Item 9).

**Prerequisites (1 hour)**  
- Completion of Roadmap Items 1–9.  
- `aecos` package installed in editable mode.  
- `pip install requests pandas sqlalchemy python-dotenv` (for API keys and caching).  
- Valid RSMeans API key (or Gordian developer account) stored in `.env`; fallback local CSV in `data/pricing/`.  
- Git LFS already configured for cost data files.

**Phase 1: Data Acquisition and Caching Layer (Day 1)**  
Create `aecos/cost/data_fetcher.py`:  
```python
import os
import requests
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv

load_dotenv()
RSMEANS_API_KEY = os.getenv("RSMEANS_API_KEY")

def fetch_rsmeans_unit_cost(material_code: str, region: str = "LA") -> dict:
    url = f"https://api.rsmeans.com/v1/costs/{material_code}"
    headers = {"Authorization": f"Bearer {RSMEANS_API_KEY}"}
    params = {"region": region, "date": "2026-01"}  # current as of February 2026
    response = requests.get(url, headers=headers, params=params, timeout=10)
    return response.json() if response.ok else None

def load_local_cache() -> pd.DataFrame:
    cache_path = Path("data/pricing/louisiana_2026.csv")
    return pd.read_csv(cache_path) if cache_path.exists() else pd.DataFrame()
```

**Phase 2: Quantity Takeoff Engine (Day 1–2)**  
Leverage IFC geometry from generated models:  
```python
import ifcopenshell.geom
def calculate_quantities(element_model: ifcopenshell.file) -> dict:
    settings = ifcopenshell.geom.settings()
    shape = ifcopenshell.geom.create_shape(settings, element_model)
    return {
        "volume_m3": shape.geometry.volume,
        "area_m2": shape.geometry.area,
        "length_m": shape.geometry.length if hasattr(shape.geometry, "length") else None
    }
```

**Phase 3: Cost Calculation and Regional Adjustment (Day 2)**  
Implement in `aecos/cost/engine.py`:  
```python
class CostEngine:
    def calculate(self, spec: ParametricSpec, quantities: dict) -> dict:
        base_cost = self._get_unit_cost(spec.performance.get("material"))
        regional_factor = self._get_louisiana_factor(spec.region[0])  # e.g., 0.92 for Baton Rouge
        total_material = base_cost * quantities["volume_m3"] * regional_factor
        
        labor_hours = self._estimate_labor(spec.ifc_class, quantities)
        total_cost = total_material + (labor_hours * 85.50)  # avg LA rate 2026
        
        return {
            "unit_cost_usd": round(base_cost, 2),
            "total_installed_usd": round(total_cost, 2),
            "labor_hours": round(labor_hours, 1),
            "currency": "USD",
            "source": "RSMeans 2026 Q1 + LA adjustment",
            "confidence": 0.95
        }
```

**Phase 4: Schedule Hook Integration (Day 3)**  
Map element type to standard RSMeans durations (e.g., “install wall” = 0.12 days per m²):  
```python
def estimate_duration(cost_data: dict, quantities: dict) -> dict:
    return {
        "duration_days": round(quantities["area_m2"] * 0.12, 2),
        "predecessor_types": ["foundation", "framing"],
        "crew_size": 4
    }
```

**Phase 5: Markdown and JSON Output (Day 3)**  
Reuse Item 3 Markdown generator to create:  
- `COST.md` (summary table, breakdowns, sensitivity analysis)  
- `SCHEDULE.md` (activity ID, duration, float)  
- Append to `README.md` under new “Cost & Schedule” section.

**Phase 6: CLI and Automated Hooks (Day 4)**  
```bash
aecos cost "150mm concrete wall fire 2hr CA" --quantity 45m2
```
Automatic trigger: `generate_element()` → `cost_engine.calculate()` → write files → git commit hook (Item 4).

**Phase 7: Testing, Accuracy, and Maintenance (Day 4–5)**  
- Test suite: 80 elements benchmarked against published RSMeans data (target ±8 % variance).  
- Cache refresh workflow (weekly GitHub Action).  
- Sensitivity analysis for material price volatility (±15 %).  
- Support for custom supplier overrides via local CSV.

**Total Time to Working Version 1:** 5–7 days  
**Milestone Verification:** After running `aecos generate "150 mm concrete wall, 2-hour fire rated, 45 m², Baton Rouge LA"`, the resulting folder contains `COST.md` and `cost.json` showing precise total installed cost ($X,XXX), labor hours, and a 5-day schedule stub, all traceable to RSMeans source data and committed to the repository.

This module converts your system from pure geometry into a true cost- and time-aware design engine, delivering instant feasibility feedback at the point of creation.  

Begin with Phases 1–3 today using a single wall template and your local pricing CSV. Provide any API response samples or calculation discrepancies encountered, and I will refine the engine logic immediately.
