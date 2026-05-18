# Text-to-CAE Gear Mesh Dynamics

This case models two meshing spur gears with transient rotation, tooth contact
stress concentration, speed ratio, and torque transfer. It is designed for the
standalone Text-to-CAE viewer and includes a deterministic visual result so the
case is inspectable without waiting for a full Abaqus solve.

Files:

- `cae_parameters.json` stores editable gear and load parameters.
- `cae_project.json` stores the viewer-facing project manifest.
- `refresh_gear_result.mjs` regenerates `result_mesh.json` and result metrics.
- `gear_mesh_abaqus.py` is the Abaqus/CAE entrypoint for a solver-backed model.
- `export_gear_mesh.py` keeps the browser run pipeline compatible.

Run the visual refresh:

```powershell
node models\text-to-cae-gear-mesh\refresh_gear_result.mjs
```

Run the Abaqus model:

```powershell
& $env:ABAQUS_COMMAND cae noGUI=models\text-to-cae-gear-mesh\gear_mesh_abaqus.py
```
