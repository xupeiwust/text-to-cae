# Ansys AEDT MCP

Part of CAE Agent Hub. This module provides the Ansys Electronics Desktop / HFSS MCP bridge for the hub's Ansys tool family.

This folder contains a portable MCP server plus a raw TCP JSON bridge for Ansys Electronics Desktop 2026 R1. MCP-capable clients such as Codex can connect to a live AEDT session, inspect projects, create HFSS designs, save projects, and execute small AEDT Python snippets.

The bridge follows the same overall pattern as this repository's Abaqus MCP:

```text
MCP client
  <stdio MCP>
mcp_server.py
  <local raw TCP JSON, default 127.0.0.1:48252>
aedt_mcp_bridge.py running inside AEDT
  <oDesktop / oProject / oDesign scripting API>
Ansys Electronics Desktop / HFSS
```

It does not use HTTP or WebSocket. The socket protocol is newline-delimited JSON over localhost.

## Contents

- `mcp_server.py`: external stdio MCP server.
- `aedt_mcp_bridge.py`: script to run inside Ansys Electronics Desktop.
- `reload_bridge_in_aedt.py`: utility script for reloading the bridge in an already running AEDT session.
- `aedt_socket_protocol.py`: shared raw TCP JSON protocol helpers.
- `stop_mcp.py`: asks the running AEDT bridge to stop.
- `scripts/launch_aedt_with_mcp_bridge.ps1`: optional legacy launcher for starting or attaching to AEDT from outside the UI.
- `scripts/install_aedt_mcp_autostart.ps1`: optional legacy shortcut installer; not used by the current recommended setup.
- `scripts/install_aedt_toolkit_button.ps1`: installs the native AEDT Toolkit/Automation ribbon gallery dropdown for HFSS and Project contexts.
- `scripts/start_aedt_mcp_bridge_in_aedt.py`: menu-friendly AEDT script entry point for manual start/reload.
- `scripts/stop_aedt_mcp_bridge_in_aedt.py`: menu-friendly AEDT script entry point for manual stop.
- `.env.example`: bridge endpoint and timeout variables.
- `examples/mcp_config.example.json`: generic MCP client configuration.
- `tests/`: protocol unit tests that do not require AEDT.

## Install

From this folder:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -U pip
.\.venv\Scripts\python.exe -m pip install -e .
```

If `py` resolves to the wrong Python on this machine, use the Codex runtime Python or another known-good Python 3.10+ executable.

## Legacy Launcher

The external launcher shortcut is no longer the recommended default because AEDT now has a native `AEDT MCP` dropdown on the Automation ribbon.

The old shortcut installer is kept only as an optional helper:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\scripts\install_aedt_mcp_autostart.ps1"
```

To test the launcher against an already-open AEDT session without creating a shortcut:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\scripts\launch_aedt_with_mcp_bridge.ps1" -NoLaunch
```

## AEDT Automation Dropdown

Install the native AEDT Toolkit gallery dropdown:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\scripts\install_aedt_toolkit_button.ps1"
```

This updates the AEDT Toolkit `TabConfig.xml` files for `HFSS` and `Project`, after creating `.bak_aedt_mcp` backups. The ribbon entry is:

```text
AEDT MCP
  Start AEDT MCP Bridge
  Stop AEDT MCP Bridge
```

If AEDT is already open, run this from the live bridge or restart AEDT:

```python
oDesktop.RefreshToolkitUI()
```

After refresh, look on the `Automation` ribbon tab, in the `Codex MCP` panel. Open `AEDT MCP`, then use `Stop AEDT MCP Bridge` before closing AEDT if the bridge is running.

## Start The AEDT Bridge

Manual start is still available:

1. Open Ansys Electronics Desktop 2026 R1.
2. In AEDT, run `scripts\start_aedt_mcp_bridge_in_aedt.py` or `reload_bridge_in_aedt.py` from the script editor / script menu.
3. Confirm the AEDT message/log says:

```text
AEDT MCP bridge listening on 127.0.0.1:48252
```

Optional environment variables:

```text
AEDT_MCP_HOST=127.0.0.1
AEDT_MCP_PORT=48252
AEDT_MCP_TIMEOUT=60
AEDT_MCP_TOKEN=
AEDT_MCP_LOG=%TEMP%\aedt_mcp_socket_bridge.log
```

Keep the host as `127.0.0.1` unless you intentionally need remote access.

## MCP Client Setup

Replace `<repo>` with the absolute path to this folder.

```text
<your-checkout>\MCP\Ansys\AEDT MCP
```

```json
{
  "mcpServers": {
    "ansys-aedt": {
      "command": "<repo>\\.venv\\Scripts\\python.exe",
      "args": ["<repo>\\mcp_server.py"],
      "cwd": "<repo>",
      "env": {
        "AEDT_MCP_HOST": "127.0.0.1",
        "AEDT_MCP_PORT": "48252",
        "AEDT_MCP_TIMEOUT": "60"
      }
    }
  }
}
```

## Tools

- `ping`: verify the AEDT-side bridge and return live session telemetry.
- `check_aedt_connection`: concise human-readable connection status.
- `run_script`: execute AEDT Python code in the bridge namespace; assign `result` to return structured data.
- `get_project_info`: inspect active project/design state.
- `create_hfss_design`: create or activate an HFSS design.
- `save_project`: save the active AEDT project.

Resources:

- `aedt://status`
- `aedt://agent-instructions`

## Recommended Workflow

1. Start AEDT from the normal Ansys Electronics Desktop shortcut.
2. In AEDT, open the `Automation` ribbon, open `AEDT MCP`, and click `Start AEDT MCP Bridge`.
3. From Codex, call `ping`.
4. Call `get_project_info`.
5. Use small `run_script` chunks to inspect uncertain AEDT API behavior.
6. Use higher-level tools such as `create_hfss_design` once the current session state is clear.
7. Open `AEDT MCP` and click `Stop AEDT MCP Bridge` before closing AEDT to release the socket listener cleanly.

## Notes

This is the first raw TCP bridge implementation for AEDT in this repository. It intentionally keeps the bridge small and external-MCP-friendly. The current AEDT entry point is installed through the Toolkit `TabConfig.xml` files.

Later versions can add more HFSS-specific MCP tools for geometry, materials, boundaries, excitations, setups, solves, and reports.

The project does not include Ansys binaries, licenses, user projects, solver results, or private local configuration.
