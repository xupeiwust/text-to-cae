# CAE Agent Hub

**Language:** English | [中文](README.zh-CN.md)

![CAE Agent Hub preview](assets/text-to-cae-preview.png)

CAE Agent Hub is a workspace for MCP servers, agent skills, automation scripts, and browser viewers for mainstream engineering simulation software. It is designed for workflows where an AI coding client, such as Codex, Cursor, or Claude Desktop, connects to real CAE tools, writes or edits solver scripts, runs verified local simulations, exports results, and displays those results in an interactive web UI.

The project is expanding across solver ecosystems, including Abaqus and Ansys products such as Fluent, Workbench Mechanical, and AEDT/HFSS. The original Text to CAE viewer remains as the browser-based result viewer and demo workflow inside this broader hub.

The project connects four layers:

- **CAE applications** build models, mesh, solve, and produce native result databases.
- **MCP servers** let AI clients inspect and control live solver sessions.
- **Agent skills** package repeatable setup, modeling, solving, and postprocessing workflows.
- **Text to CAE Viewer** loads exported `result_mesh.json`, project metadata, parameters, time frames, contours, and model trees in the browser.

Repository:

```text
https://github.com/Cai-aa/text-to-cae
```

Related Abaqus MCP repository:

```text
https://github.com/Cai-aa/abaqus-mcp
```

## Recommended Workflow

```text
Codex or another MCP-capable AI client
  -> connects to a live CAE application through an MCP server
  -> creates or edits solver automation scripts
  -> asks the solver to build, mesh, solve, and read result data
  -> exports result_mesh.json
  -> opens the Text to CAE browser viewer
```

This keeps the responsibilities clear:

- The AI client handles natural-language changes, code editing, debugging, and automation.
- The CAE application handles the real solver work.
- The browser viewer handles fast interactive inspection of CAE results.

## Requirements

- Windows
- Node.js and npm
- A supported CAE application for solver-backed runs, such as Abaqus/CAE or Ansys tools
- Python available to the relevant solver scripts
- Optional: an MCP-capable AI client plus one of the included MCP servers or [Abaqus MCP](https://github.com/Cai-aa/abaqus-mcp)

The viewer can display any case that already has a `result_mesh.json`. A solver installation is only required when you want to regenerate solver output or run a case from the browser.

## Install and Run the Viewer

Clone the project:

```powershell
git clone https://github.com/Cai-aa/text-to-cae.git
Set-Location .\text-to-cae
```

Install viewer dependencies:

```powershell
Set-Location .\viewer
npm.cmd install
```

Start the local viewer:

```powershell
npm.cmd run dev
```

Open:

```text
http://127.0.0.1:4178/
```

If port `4178` is already in use, choose another port:

```powershell
$env:VIEWER_PORT = "4181"
npm.cmd run dev
```

Then open:

```text
http://127.0.0.1:4181/
```

## Open Example Cases

Use the `case` query parameter to open a specific simulation:

```text
http://127.0.0.1:4178/?case=cantilever
http://127.0.0.1:4178/?case=hole-plate
http://127.0.0.1:4178/?case=hole-plate-modal
http://127.0.0.1:4178/?case=sphere-impact
http://127.0.0.1:4178/?case=milling-3d
http://127.0.0.1:4178/?case=gear-mesh
http://127.0.0.1:4178/?case=bullet-plate
```

The viewer includes an Abaqus-style result viewport:

```text
http://127.0.0.1:4178/?case=sphere-impact&mode=cae
```

## Browser-to-Abaqus Runs

The Vite dev server includes local CAE API endpoints:

```text
/__cae/project
/__cae/result-mesh
/__cae/result-summary
/__cae/parameters
/__cae/run
```

For runnable examples, the browser can update parameters and trigger Abaqus noGUI execution:

```text
viewer
  -> /__cae/run
  -> Abaqus noGUI
  -> *_abaqus.py
  -> export_*.py
  -> result_mesh.json
  -> viewer refresh
```

By default the viewer looks for Abaqus at:

```text
G:\SIMULIA\Commands\abaqus.bat
```

If Abaqus is installed elsewhere, set `ABAQUS_COMMAND` before starting the viewer:

```powershell
$env:ABAQUS_COMMAND = "C:\SIMULIA\Commands\abaqus.bat"
npm.cmd run dev
```

## Case File Layout

Each example case normally contains:

```text
models/<case>/
  cae_parameters.json
  cae_project.json
  *_abaqus.py
  export_*.py
  result_mesh.json
```

File roles:

- `*_abaqus.py` builds the Abaqus model, assigns materials, meshes, defines steps, applies loads and boundary conditions, and submits the job.
- `export_*.py` reads ODB output and exports browser-readable mesh, contour, displacement, modal, or dynamic-frame data.
- `result_mesh.json` is the main result payload loaded by the viewer.
- `cae_project.json` stores project metadata, workflow state, model tree data, output paths, and result metrics.
- `cae_parameters.json` stores editable input parameters used by the browser run panel.

## Included Examples

| Case | Directory | Description |
| --- | --- | --- |
| Cantilever beam | `models/text-to-cae` | Static introductory case with displacement and stress contours. |
| Plate with hole | `models/text-to-cae-hole-plate` | Tensile plate with circular-hole stress concentration. |
| Plate with hole modal | `models/text-to-cae-hole-plate-modal` | Frequency extraction case with modal frames. |
| Sphere impact | `models/text-to-cae-sphere-impact` | Explicit dynamics example showing sphere-to-plate contact, impact, indentation, and rebound. |
| 3D milling | `models/text-to-cae-milling-3d` | End-milling dynamics visualization with editable machining parameters. |
| Gear mesh | `models/text-to-cae-gear-mesh` | Spur gear meshing dynamics with driver and driven gear parameters. |
| Bullet plate | `models/text-to-cae-bullet-plate` | High-speed projectile penetration example. |

Some large result files are intentionally not committed. Regenerate them locally with Abaqus or with the provided refresh scripts.

## Refresh Visual Result Data

Some examples include deterministic refresh scripts that can rebuild browser preview data without waiting for a full solver run:

```powershell
node models\text-to-cae-sphere-impact\refresh_contact_result.mjs
node models\text-to-cae-milling-3d\refresh_visual_result.mjs
node models\text-to-cae-gear-mesh\refresh_gear_result.mjs
```

## Run Abaqus Scripts Directly

You can also run cases from the command line without using the browser run button.

Sphere impact:

```powershell
& "G:\SIMULIA\Commands\abaqus.bat" cae noGUI=models\text-to-cae-sphere-impact\sphere_impact_abaqus.py
& "G:\SIMULIA\Commands\abaqus.bat" cae noGUI=models\text-to-cae-sphere-impact\export_dynamic_mesh.py
```

3D milling:

```powershell
& "G:\SIMULIA\Commands\abaqus.bat" cae noGUI=models\text-to-cae-milling-3d\milling_abaqus.py
& "G:\SIMULIA\Commands\abaqus.bat" cae noGUI=models\text-to-cae-milling-3d\export_milling_mesh.py
```

Gear mesh:

```powershell
& "G:\SIMULIA\Commands\abaqus.bat" cae noGUI=models\text-to-cae-gear-mesh\gear_mesh_abaqus.py
& "G:\SIMULIA\Commands\abaqus.bat" cae noGUI=models\text-to-cae-gear-mesh\export_gear_mesh.py
```

## Connect Codex to Abaqus with MCP

Install Abaqus MCP:

```powershell
git clone https://github.com/Cai-aa/abaqus-mcp.git $env:USERPROFILE\.abaqus-mcp
pip install mcp
```

Let Abaqus/CAE load the MCP startup environment:

```powershell
Copy-Item -Force "$env:USERPROFILE\.abaqus-mcp\abaqus_v6.env.example" "$env:USERPROFILE\abaqus_v6.env"
```

Optional GUI menu plugin:

```powershell
Copy-Item -Recurse -Force "$env:USERPROFILE\.abaqus-mcp\abaqus_plugins\mcp_control" "$env:USERPROFILE\abaqus_plugins\mcp_control"
```

After restarting Abaqus/CAE, start MCP from:

```text
Plug-ins -> MCP -> Start MCP
```

You can also start it from the Abaqus Python console:

```python
mcp_start()
```

If background threads are unstable in your Abaqus version, use the cooperative or blocking loop:

```python
mcp_coop_loop()
```

or:

```python
mcp_loop()
```

Configure your MCP-capable client with the Abaqus MCP server. A typical shape is:

```json
{
  "mcpServers": {
    "abaqus-mcp": {
      "command": "python",
      "args": ["C:/Users/<your-user>/.abaqus-mcp/mcp_server.py"]
    }
  }
}
```

Replace `<your-user>` with your Windows user name, or use an absolute Python interpreter path if `python` is not on `PATH`.

## Viewer Controls

The UI is organized around:

- A left model tree for project, parts, materials, assembly, steps, loads, boundary conditions, mesh, jobs, and results.
- A central 3D viewport for contours, mesh edges, dynamic frames, modal shapes, tools, spheres, gears, projectiles, and other case objects.
- A right panel for state, metrics, editable parameters, and run controls.

Common interactions:

- Left drag: rotate the model.
- Middle drag: pan the model.
- Mouse wheel: zoom.
- Play controls: animate dynamic or modal frames.
- Theme controls: switch between Abaqus, dark, and light viewport styles.

## Project Structure

```text
text-to-cae/
  README.md
  LICENSE
  models/
    text-to-cae/
    text-to-cae-hole-plate/
    text-to-cae-hole-plate-modal/
    text-to-cae-sphere-impact/
    text-to-cae-milling-3d/
    text-to-cae-gear-mesh/
    text-to-cae-bullet-plate/
  viewer/
    package.json
    vite.config.mjs
    main.jsx
    components/
      CaeResultViewer.js
      TextToCaeWorkspace.js
```

## Git and Large Files

The repository excludes generated or large local artifacts, including:

- `viewer/node_modules/`
- `viewer/dist/`
- `viewer/dist-verify/`
- Abaqus `.odb`
- Abaqus `.inp`
- Abaqus intermediate files such as `.sim`, `.dat`, `.msg`, `.sta`, `.prt`, and `.lck`
- Python `__pycache__`
- very large generated `result_mesh.json` files

These files can be recreated by installing dependencies, rebuilding the viewer, rerunning Abaqus scripts, or using the refresh scripts.

## Build

Build the frontend:

```powershell
Set-Location .\viewer
npm.cmd run build
```

The build output is written to `viewer/dist/`.

## Troubleshooting

### The page does not open

Make sure the dev server is running:

```powershell
Set-Location .\viewer
npm.cmd run dev
```

Open the URL printed by Vite, normally:

```text
http://127.0.0.1:4178/
```

### The viewer does not show updated results

Click the refresh control in the viewer or reload the browser page. `result_mesh.json` is loaded at runtime, so the page may still be showing the previous result payload.

### Abaqus does not start from the browser

Check `ABAQUS_COMMAND`:

```powershell
$env:ABAQUS_COMMAND
```

If it is empty or points to the wrong path, set it before starting the viewer:

```powershell
$env:ABAQUS_COMMAND = "G:\SIMULIA\Commands\abaqus.bat"
npm.cmd run dev
```

### Some result files are missing after clone

Large ODB, INP, and generated result files are not committed. Regenerate them with the corresponding Abaqus script or refresh script.
