# Ansys AEDT MCP

This module lets MCP clients such as Codex control Ansys Electronics Desktop 2026 R1 through PyAEDT.

## Architecture

```text
Codex -> FastMCP stdio server -> external PyAEDT broker -> explicit AEDT PID or gRPC port
```

No MCP script, socket server, extension, or background thread runs inside AEDT. The MCP server creates one external broker for each selected target and reuses that PyAEDT connection across commands. The broker calls `release_desktop(close_projects=False, close_on_exit=False)` only when `release_connection` is called, the MCP process exits, or its stdin closes.

This lifecycle is required for AEDT 2026 R1 gRPC sessions: ending the PyAEDT client after every command also ends that session's gRPC listener. Keeping the connection in an external broker avoids rebuilding AEDT for each tool call without leaving Toolkit/Automation code running in AEDT.

On Windows, the broker watches only its target AEDT process. If the AEDT busy dialog appears, or the main window changes from visible to closed, the broker interprets that as an explicit user close request and calls AEDT `QuitApplication()` through the existing PyAEDT session. The broker then exits. This prevents a connected broker from leaving a hidden AEDT process behind.

## Install

Use Python 3.10 or newer:

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -U pip
.\.venv\Scripts\python.exe -m pip install -e .
```

The package pins PyAEDT 1.1.0 for AEDT 2026 R1. Set `AEDT_INSTALL_DIR` to the directory containing `ansysedt.exe` when using `launch_aedt`.

## MCP Configuration

Use `examples/mcp_config.example.json` and replace `<repo>` with this directory's absolute path.

## Explicit Targeting

There is no implicit AEDT session.

1. Call `list_aedt_sessions` or `launch_aedt`.
2. Choose one PID or one gRPC port.
3. Pass exactly one of `pid` or `port` to every targeted tool.

The server never chooses the newest or foreground AEDT window. A successful probe records the returned PID and port as aliases for the same broker, so either explicit identifier continues to address that same session.

## Lifecycle

- `check_aedt_connection` creates the broker on first use and performs a real PyAEDT probe.
- Project and analysis tools reuse that broker.
- `release_connection` disconnects the broker without requesting project or AEDT closure.
- MCP shutdown and broker stdin EOF also release all connections.
- Closing the AEDT window triggers `QuitApplication()` and terminates that target's broker.
- A timed-out broker is terminated; the AEDT process is never force-terminated.

For an MCP-launched session, prefer the port returned by `launch_aedt`. For a user-opened AEDT window, select its PID from `list_aedt_sessions`.

## Tools

- `list_aedt_sessions`: discover AEDT PIDs and local listener ports without attaching.
- `launch_aedt`: launch visible AEDT 2026 R1 with an explicit gRPC port.
- `check_aedt_connection`: probe one explicit target.
- `release_connection`: stop and release that target's broker.
- `get_project_info`: inspect project and active design metadata.
- `create_hfss_design`: create or activate a named HFSS design.
- `save_project`: save the active project, optionally to an explicit path.
- `start_analysis`: start a named HFSS setup; non-blocking by default.
- `get_analysis_status`: query running state and setups.

Resources `aedt://status` and `aedt://agent-instructions` never attach implicitly.

## Remove Legacy Toolbar

The old `Start AEDT MCP Bridge` and `Stop AEDT MCP Bridge` buttons are not used. Remove only those known entries with:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\scripts\remove_legacy_aedt_mcp_toolbar.ps1" -AedtRoot "G:\ANSYS206\ANSYS Inc\v261\AnsysEM"
```

## Verification

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\scripts\run_live_acceptance.ps1 -Mode both
```

Live acceptance covers explicit PID and port targeting, repeated commands on one broker, disposable HFSS project save, and normal AEDT close while the broker is still connected. It fails if the "being used by another application, script or extension wizard" dialog appears.
