"""HTML viewer generator — self-contained Three.js page."""

from __future__ import annotations

from pathlib import Path

from aecos.visualization.scene import Scene


def generate_viewer(scene: Scene, output_path: str | Path) -> Path:
    """Generate a self-contained HTML file that renders the scene.

    Embeds Three.js via CDN and renders the JSON3D scene with orbit controls.
    The resulting HTML can be opened directly in any modern browser.

    Parameters
    ----------
    scene:
        The 3D scene to render.
    output_path:
        Path for the output HTML file.

    Returns
    -------
    Path
        Path to the generated HTML file.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    scene_json = scene.to_json(indent=None)
    camera = scene.camera

    html = _VIEWER_TEMPLATE.format(
        title=f"AEC OS Viewer — {scene.element_id or 'Scene'}",
        scene_json=scene_json,
        cam_x=camera.position[0],
        cam_y=camera.position[1],
        cam_z=camera.position[2],
        target_x=camera.target[0],
        target_y=camera.target[1],
        target_z=camera.target[2],
    )

    output_path.write_text(html, encoding="utf-8")
    return output_path


_VIEWER_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
  body {{ margin: 0; overflow: hidden; background: #1a1a2e; }}
  canvas {{ display: block; }}
  #info {{ position: absolute; top: 10px; left: 10px; color: #eee;
           font-family: monospace; font-size: 14px; }}
</style>
</head>
<body>
<div id="info">{title}<br>Orbit: drag | Zoom: scroll | Pan: right-drag</div>
<script src="https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/three@0.160.0/examples/js/controls/OrbitControls.js"></script>
<script>
(function() {{
  const sceneData = {scene_json};

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x1a1a2e);

  const camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 0.1, 1000);
  camera.position.set({cam_x}, {cam_y}, {cam_z});

  const renderer = new THREE.WebGLRenderer({{ antialias: true }});
  renderer.setSize(window.innerWidth, window.innerHeight);
  renderer.setPixelRatio(window.devicePixelRatio);
  document.body.appendChild(renderer.domElement);

  const controls = new THREE.OrbitControls(camera, renderer.domElement);
  controls.target.set({target_x}, {target_y}, {target_z});
  controls.update();

  // Lighting
  scene.add(new THREE.AmbientLight(0x404040, 2));
  const dirLight = new THREE.DirectionalLight(0xffffff, 1.5);
  dirLight.position.set(10, 10, 10);
  scene.add(dirLight);

  // Grid helper
  const gridSize = 20;
  scene.add(new THREE.GridHelper(gridSize, gridSize, 0x444444, 0x222222));

  // Axes
  scene.add(new THREE.AxesHelper(5));

  // Build meshes from scene data
  if (sceneData.meshes) {{
    sceneData.meshes.forEach(function(m) {{
      const geometry = new THREE.BufferGeometry();
      const verts = new Float32Array(m.vertices.flat());
      geometry.setAttribute('position', new THREE.BufferAttribute(verts, 3));
      const indices = m.faces.flat();
      geometry.setIndex(indices);
      geometry.computeVertexNormals();

      const material = new THREE.MeshPhongMaterial({{
        color: m.color,
        flatShading: true,
        transparent: true,
        opacity: 0.9,
        side: THREE.DoubleSide,
      }});

      const mesh = new THREE.Mesh(geometry, material);
      scene.add(mesh);

      // Wireframe overlay
      const wireframe = new THREE.LineSegments(
        new THREE.WireframeGeometry(geometry),
        new THREE.LineBasicMaterial({{ color: 0x000000, linewidth: 1, opacity: 0.2, transparent: true }})
      );
      scene.add(wireframe);
    }});
  }}

  function animate() {{
    requestAnimationFrame(animate);
    controls.update();
    renderer.render(scene, camera);
  }}
  animate();

  window.addEventListener('resize', function() {{
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
  }});
}})();
</script>
</body>
</html>
"""
