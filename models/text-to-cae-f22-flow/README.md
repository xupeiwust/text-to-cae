# F-22 External Flow Browser Case

This case is an ANSYS Fluent-oriented external-flow setup for an F-22 inspired
fighter planform. The current browser result is a deterministic postprocessed
preview in `result_mesh.json`, so it can be inspected immediately in the
Text-to-CAE viewer.

Open it in the local viewer:

```powershell
Set-Location .\viewer
npm.cmd run dev
```

Then browse to:

```text
http://127.0.0.1:4178/?case=f22-flow&mode=cae
```

Regenerate the browser payload:

```powershell
node ..\models\text-to-cae-f22-flow\generate_f22_flow_result.mjs
```

The included `f22_external_flow_fluent.jou` records the intended Fluent run
shape. A full production run still needs a watertight CAD/mesh export and a
live Fluent solve before replacing `result_mesh.json` with solver-derived
fields.
