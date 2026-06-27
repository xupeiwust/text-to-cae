# Ansys AEDT MCP

This CAE Agent Hub module lets MCP clients such as Codex control Ansys Electronics Desktop 2026 R1 through PyAEDT.

## Architecture

```text
Codex -> FastMCP stdio server -> one short-lived PyAEDT worker -> explicit AEDT PID or gRPC port
```

No MCP script, socket server, extension, or background thread runs inside AEDT. Each operation starts one external worker, connects to exactly one target, performs one command, calls `release_desktop(close_projects=False, close_on_exit=False)`, and exits. The MCP process never retains an AEDT Automation object.

## Install

Use Python 3.10 or newer:

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -U pip
.\.venv\Scripts\python.exe -m pip install -e .
```

The package pins PyAEDT 1.1.0, which supports AEDT 2026 R1.

Copy the relevant values from `.env.example` into the MCP client environment. `AEDT_INSTALL_DIR` must contain `ansysedt.exe` when `launch_aedt` is used.

## MCP configuration

Use `examples/mcp_config.example.json` and replace `<repo>` with the absolute path to this directory.

## Session selection

There is no implicit AEDT session.

1. Call `list_aedt_sessions`.
2. Choose one process PID or one gRPC port.
3. Pass exactly one of `pid` or `port` to every targeted tool.

When multiple AEDT sessions are open, the server never chooses the newest or foreground window. Port targeting is preferred for sessions created by `launch_aedt`.

## Workflows

### Attach to an AEDT window opened by the user

1. Start graphical AEDT 2026 R1 normally.
2. Call `list_aedt_sessions` and identify its PID.
3. Call `check_aedt_connection(pid=<PID>)`.
4. Use the same PID for project and analysis tools.

### Launch a visible gRPC AEDT session

1. Call `launch_aedt(port=0)`.
2. Keep the returned PID and port.
3. Target subsequent tools with the returned port.

The launcher uses `ansysedt.exe -grpcsrv <port>` without non-graphical flags. If readiness times out, AEDT is left running for inspection; the MCP never force-closes it.

## Tools

- `list_aedt_sessions`: discover AEDT PIDs and local listener ports without attaching.
- `launch_aedt`: launch visible AEDT 2026 R1 in gRPC mode.
- `check_aedt_connection`: run a real PyAEDT probe for one explicit target.
- `release_connection`: perform an attach/release smoke test without closing AEDT.
- `get_project_info`: inspect active project and design metadata.
- `create_hfss_design`: create or activate a named HFSS design.
- `save_project`: save the active project or save it to an explicit path.
- `start_analysis`: start a named HFSS setup; non-blocking by default.
- `get_analysis_status`: query running state and available setups.

Resources:

- `aedt://status`: discovery-only status; it does not attach to AEDT.
- `aedt://agent-instructions`: targeting and lifecycle rules.

## Failure isolation

- Every Worker has a timeout.
- A timed-out Worker is terminated; AEDT is not terminated.
- Calls to the same target are serialized.
- Calls to different explicit targets can run independently.
- PyAEDT diagnostics are written under `AEDT_LOG_DIR` and never mixed with MCP stdio JSON.

## Remove the legacy toolbar

Older versions installed `Start AEDT MCP Bridge` and `Stop AEDT MCP Bridge` in AEDT. They are not used by this implementation. To remove only those known entries:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\scripts\remove_legacy_aedt_mcp_toolbar.ps1" -AedtRoot "G:\ANSYS206\ANSYS Inc\v261\AnsysEM"
```

The script preserves `TabConfig.xml.bak_aedt_mcp` and unrelated Toolkit entries. Restart AEDT after cleanup.

## Verification

Offline tests:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Live acceptance testing must verify both PID attachment and gRPC launch mode, including normal AEDT window close without the "being used by another application, script or extension wizard" dialog.
