**Parametric Generation (Roadmap Item 8)**  
**Goal:** Create a robust parametric generation module within the `aecos` package that accepts validated specifications from the natural language parser (Item 6) and compliance engine (Item 7), then programmatically constructs or modifies IFC elements and small assemblies using `ifcopenshell.api`. The module produces complete, standards-compliant IFC chunks that integrate seamlessly with the template library (Item 2), Markdown metadata layer (Item 3), and Python API wrapper (Item 5). This capability extends beyond static templates to generate bespoke elements (e.g., custom wall thicknesses, variable-height columns, or regionally adjusted MEP runs) while preserving traceability and version control.

**Core Capabilities**  
- Parameter-driven creation of individual IFC entities (IfcWall, IfcDoor, IfcBeam, etc.).  
- Assembly generation (e.g., wall + insulation + cladding).  
- Automatic application of compliance-derived constraints (e.g., minimum fire-rating thickness).  
- Output: self-contained IFC file or folder structure matching Items 1–3, ready for git commit.

**Integration Points**  
- Input: `ElementMetadata` object from Item 6 + compliance report from Item 7.  
- Output: new folder under `generated/` or direct insertion via Revit bridge (Item 5).

**Prerequisites (45 minutes)**  
- Completion of Roadmap Items 1–7.  
- `aecos` package installed in editable mode.  
- `ifcopenshell` version supporting IFC4.3 API calls (confirmed current as of February 2026).  
- Sample base templates available in the library for inheritance where applicable.

**Phase 1: Parameter Schema and Validation (Day 1)**  
Extend the Pydantic model in `aecos/models/element.py` with parametric fields:  
```python
class ParametricSpec(ElementMetadata):
    base_template_path: Optional[Path] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)  # e.g., {"thickness_mm": 180, "height_m": 3.2}
    assembly_components: List[str] = Field(default_factory=list)
```

**Phase 2: Base Creation Functions (Day 1)**  
Implement foundational creators in `aecos/core/generator.py` using `ifcopenshell.api`:  
```python
import ifcopenshell.api as api

def create_wall(model: ifcopenshell.file, spec: ParametricSpec) -> ifcopenshell.entity_instance:
    wall = api.root.create_entity(model, ifc_class="IfcWallStandardCase", name=spec.name)
    api.attribute.edit_attributes(wall, {"GlobalId": ifcopenshell.guid.new()})
    
    # Apply geometry
    placement = api.geometry.create_local_placement(model)
    representation = api.geometry.add_wall_representation(model, context=..., length=spec.parameters.get("length_m", 5.0))
    
    # Material and Psets from compliance
    material = api.material.add_material(model, name=spec.performance.get("material", "Concrete"))
    api.material.assign_material(wall, material)
    
    # Add Psets
    pset = api.pset.add_pset(model, product=wall, name="Pset_WallCommon")
    api.pset.edit_pset(model, pset, properties={"IsExternal": True, "FireRating": spec.performance.get("fire_rating")})
    
    return wall
```

**Phase 3: Template Inheritance and Modification (Day 2)**  
Support two modes:  
- Pure parametric (from scratch).  
- Template-based (load base IFC → edit parameters via API).  
```python
def generate_from_template(template_path: Path, spec: ParametricSpec) -> ifcopenshell.file:
    model = ifcopenshell.open(str(template_path / "template.ifc"))
    element = model.by_guid(spec.global_id)  # or first matching class
    # Modify geometry, properties, relationships per spec
    api.geometry.edit_object_placement(model, product=element, placement=updated_placement)
    return model
```

**Phase 4: Assembly Generator (Day 2–3)**  
Create layered assemblies:  
```python
def create_assembly(spec: ParametricSpec) -> ifcopenshell.file:
    model = api.root.create_ifc(model_schema="IFC4")
    main_element = create_wall(model, spec)
    for component in spec.assembly_components:
        sub_element = create_component(model, component, attached_to=main_element)
        api.relationship.create_rel_aggregates(model, relating_object=main_element, related_objects=[sub_element])
    return model
```

**Phase 5: Full Generation Pipeline and Metadata (Day 3)**  
```python
def generate_element(spec: ParametricSpec) -> Path:
    compliance_report = aecos.compliance.engine.check(spec)
    if compliance_report["status"] == "non_compliant":
        spec = apply_compliance_adjustments(spec, compliance_report)
    
    model = generate_from_template_or_scratch(spec)
    output_folder = create_element_folder(model, spec)  # reuses Item 3 Markdown generation
    aecos.core.markdown.generate_markdown(output_folder)
    return output_folder
```

**Phase 6: CLI, Error Handling, and Revit Export (Day 4)**  
CLI command:  
```bash
aecos generate "150 mm concrete wall, 2 hr fire rated, length 8 m, California" --output generated/
```
- Comprehensive error handling for invalid parameters.  
- Export options: `.ifc`, `.rvt` link (via pyRevit), or Speckle stream.

**Phase 7: Testing, Benchmarking, and Optimization (Day 4–5)**  
- Unit tests: 100 parametric cases covering walls, doors, beams, and assemblies.  
- Round-trip validation: generate → extract (Item 1) → compare properties (target 99 % match).  
- Performance: benchmark generation time < 2 seconds per element on standard hardware.  
- Edge-case handling: unit conversions, conflicting requirements, large assemblies.

**Total Time to Working Version 1:** 5–7 days  
**Milestone Verification:** Executing `aecos generate "Create a 180 mm thick exterior concrete wall with 2-hour fire rating, height 4.2 m, for California seismic zone D"` produces a complete folder containing a valid IFC file, updated Markdown metadata, and a compliance report confirming full adherence to referenced code sections. The generated element can be loaded directly into Revit or the template library.

This module transforms the system from a retrieval-based library into a true generative design engine, enabling rapid iteration on unique project requirements while maintaining full traceability.  

Initiate Phases 1–3 today using a single element type (e.g., IfcWall). Should any implementation questions arise regarding specific `ifcopenshell.api` calls or integration points, provide the relevant details for precise guidance.