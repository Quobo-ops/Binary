**Visualization Bridge (Roadmap Item 11)**  
**Goal:** Develop a bidirectional visualization bridge within the `aecos` package that converts any generated, extracted, or parametric element (or full assembly) into real-time, interactive 3D representations. The bridge supports immediate previews in professional AEC viewers, web-based interfaces, and immersive environments, enabling rapid design iteration, stakeholder feedback, clash visualization, and AR/VR walkthroughs without manual file conversion or external tools. All exports remain fully traceable to the source folder structure, Markdown metadata, and version-control history.

**Core Capabilities**  
- One-click export to Speckle streams (primary AEC collaboration platform).  
- glTF 2.0 export for web viewers and game engines.  
- Live synchronization for real-time updates.  
- Optional AR/VR export for Unity/Unreal Engine.  
- Embedded viewer links automatically added to README.md.

**Integration Points**  
- Automatic invocation after `aecos.core.generator.generate_element()` or `aecos.validation.run_full_validation()`.  
- Input: element folder or generated IFC model.  
- Output: public/private Speckle stream URL, glTF file, and updated Markdown links.  
- Hooks into natural language parser (Item 6) for “show me the wall in 3D” commands.

**Prerequisites (45 minutes)**  
- Completion of Roadmap Items 1–10.  
- `aecos` package installed in editable mode.  
- `pip install specklepy ifcopenshell trimesh pygltflib`  
- Free Speckle account and server token stored in `.env` (or self-hosted Speckle server).  
- Optional: Unity 2026 LTS or WebGL-compatible browser for advanced viewers.

**Phase 1: Speckle Connector Setup (Day 1)**  
Create `aecos/visualization/speckle_bridge.py`:  
```python
import os
from specklepy.api.client import SpeckleClient
from specklepy.api.credentials import get_default_account
from specklepy.objects import Base
from dotenv import load_dotenv

load_dotenv()
client = SpeckleClient(host="speckle.xyz")  # or self-hosted URL
client.authenticate_with_token(os.getenv("SPECKLE_TOKEN"))

def send_to_speckle(element_folder: Path, stream_id: str = None) -> str:
    if stream_id is None:
        stream = client.stream.create(name=f"AECOS_{element_folder.name}")
        stream_id = stream.id
    
    # Convert IFC to Speckle objects
    model = ifcopenshell.open(str(element_folder / "template.ifc" if "template.ifc" in element_folder.iterdir() else "generated.ifc"))
    speckle_obj = convert_ifc_to_speckle(model)  # custom converter using ifcopenshell + specklepy
    
    commit_id = client.commit.create(
        stream_id=stream_id,
        object=speckle_obj,
        message=f"Generated from {element_folder.name}",
        branch_name="main"
    )
    return f"https://speckle.xyz/streams/{stream_id}/commits/{commit_id}"
```

**Phase 2: glTF Export and Web Viewer (Day 1–2)**  
Implement geometry tessellation and glTF serialization:  
```python
import trimesh
from pygltflib import GLTF2

def export_to_gltf(element_model: ifcopenshell.file, output_path: Path):
    settings = ifcopenshell.geom.settings()
    settings.set(settings.USE_PYTHON_OPENCASCADE, True)
    shape = ifcopenshell.geom.create_shape(settings, element_model)
    mesh = trimesh.Trimesh(vertices=shape.geometry.verts, faces=shape.geometry.faces)
    mesh.export(output_path.with_suffix(".glb"))
    return output_path.with_suffix(".glb")
```

Embed a simple Three.js viewer link in README.md via Markdown generator (Item 3).

**Phase 3: Live Synchronization Layer (Day 2)**  
Add webhook support: on file change in git (Item 4), trigger Speckle commit update.  
```python
def watch_and_update(folder: Path):
    # Use watchdog library to monitor folder
    # On change → re-export to same Speckle stream
```

**Phase 4: AR/VR and Immersive Export (Day 3)**  
Generate Unity-compatible packages or direct glTF import scripts for Unity/Unreal.  
Provide prefab generation script for quick AR placement on mobile devices.

**Phase 5: Markdown and Reporting Integration (Day 3)**  
Automatically append to README.md and create `VISUALIZATION.md`:  
```markdown
## Live Preview
- Speckle: [View in Browser](https://speckle.xyz/...)
- glTF Download: [Download .glb](...)
- AR Experience: Scan QR code (generated via qrcode library)
```

**Phase 6: CLI and Automated Hooks (Day 4)**  
```bash
aecos visualize generated/wall_123 --platform speckle --stream myproject
aecos visualize --all --web
```
Automatic hook in generation/validation pipeline.

**Phase 7: Testing, Performance, and Scaling (Day 4–5)**  
- Test suite: 100 elements validated in Speckle viewer (geometry fidelity ≥ 99.5 %).  
- Performance target: export < 3 seconds per element; full model < 30 seconds.  
- Browser compatibility tested on Chrome/Edge.  
- Security: private streams by default, optional public sharing.

**Total Time to Working Version 1:** 5–7 days  
**Milestone Verification:** Executing `aecos generate "150 mm concrete wall..."` followed by `aecos visualize` produces a live Speckle link and glTF file. Opening the link displays the exact element with metadata overlays, ready for real-time markup or AR viewing on a mobile device.

This bridge transforms the system from file-centric to visually interactive, allowing instant design validation and stakeholder engagement at every stage.  

Begin implementation with Phases 1–3 today using one existing generated wall element. Should any questions arise regarding Speckle object conversion or glTF material mapping, provide the relevant details for immediate refinement.
