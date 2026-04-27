# Text to CAE

Standalone local Text-to-CAE workspace for Abaqus examples and the browser result viewer.

## Run the Viewer

```powershell
Set-Location E:\Users\Cai\Downloads\text-to-cae\viewer
npm.cmd run dev
```

Open:

```text
http://127.0.0.1:4178/
```

Useful case URLs:

```text
http://127.0.0.1:4178/?case=cantilever
http://127.0.0.1:4178/?case=hole-plate
http://127.0.0.1:4178/?case=hole-plate-modal
http://127.0.0.1:4178/?case=sphere-impact
http://127.0.0.1:4178/?case=milling-3d
http://127.0.0.1:4178/?case=bullet-plate
```

## Abaqus

The viewer can run editable cases through Abaqus when `ABAQUS_COMMAND` points to the Abaqus command script. By default it uses:

```text
G:\SIMULIA\Commands\abaqus.bat
```

Override it before starting the viewer if your Abaqus install path is different:

```powershell
$env:ABAQUS_COMMAND = "C:\SIMULIA\Commands\abaqus.bat"
npm.cmd run dev
```

Each example under `models\text-to-cae*` contains its own `cae_project.json`, scripts, and exported viewer data.
