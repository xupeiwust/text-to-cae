# CST Studio Suite MCP

This directory contains an MCP server for CST Studio Suite 2026. It uses CST's bundled Python automation APIs to control a visible CST Design Environment from an Agent.

## Capabilities

- Detect CST Python, the CST executable, and running Design Environments
- Connect to an existing CST GUI or launch a new instance
- Open, create, and save `.cst` projects
- Inspect the active project, open projects, and recent messages
- Execute CST VBA/history commands
- Run the configured 3D solver
- List result tree items and read 1D results
- Export Touchstone data
- Run advanced custom Python through `cst_run_python_tool`
- Call the vendored `bbl21/cst-runtime-cli` toolset through `cst_runtime_*` MCP wrappers
- Preview and run parameter sweeps with per-case projects, CSV summaries, optional solves, Touchstone export, and 1D result export
- Generate schema-driven Python typed wrappers for the vendored toolbox commands

## Codex Configuration

Add this to `C:\Users\Cai\.codex\config.toml`:

```toml
[mcp_servers.cst-studio-suite]
command = "E:\\Code\\CAE-Agent-Hub\\MCP\\CST\\.venv\\Scripts\\python.exe"
args = ["E:\\Code\\CAE-Agent-Hub\\MCP\\CST\\mcp_server.py"]
env = { CST_INSTALL_ROOT = "G:\\Program Files\\CST Studio Suite 2026", CST_DESIGN_ENVIRONMENT_EXE = "G:\\Program Files\\CST Studio Suite 2026\\AMD64\\CST DESIGN ENVIRONMENT_AMD64.exe" }
```

`command` uses this directory's dedicated `.venv`. This project injects CST's `cst.interface` and `cst.results` paths through `CST_INSTALL_ROOT`.

If you use CST's bundled Python directly, install the complete MCP dependency set there first. On this machine, CST Python can import `cst`, but its MCP dependencies are incomplete because `anyio` is missing.

## Typical Tool Flow

1. `cst_detect_tool`
2. `cst_connect_tool` with `launch_if_needed=true` if CST is not already running
3. `cst_project_info_tool`
4. `cst_new_project_tool` or `cst_open_project_tool`
5. `cst_add_to_history_tool` for materials, geometry, boundaries, mesh, and solver setup
6. `cst_save_project_tool`
7. `cst_run_solver_tool`
8. `cst_list_results_tool`
9. `cst_read_1d_result_tool`

## Vendored cst-runtime-cli Tools

This MCP also vendors `bbl21/cst-runtime-cli` under `vendor/cst-runtime-cli` and exposes it through wrapper tools:

- `cst_runtime_detect_tool`
- `cst_runtime_list_tools_tool`
- `cst_runtime_describe_tool`
- `cst_runtime_args_template_tool`
- `cst_runtime_invoke_tool`
- `cst_runtime_list_pipelines_tool`
- `cst_runtime_usage_guide_tool`

Use `cst_runtime_list_tools_tool` to inspect the full runtime command catalog. Use `cst_runtime_invoke_tool` to call any runtime command by name:

```json
{
  "tool_name": "list-result-items",
  "args": {
    "project_path": "E:\\Code\\CAE-Agent-Hub\\cst_runs\\case.cst"
  }
}
```

The native MCP tools remain the preferred path for live session control. The runtime wrappers are useful for the larger command catalog, workspace workflows, result exports, optimization helpers, and predefined modeling operations.

The same tools are also available through shorter aliases without the `runtime` word:

- `cst_toolbox_detect_tool`
- `cst_toolbox_list_tools_tool`
- `cst_toolbox_describe_tool`
- `cst_toolbox_args_template_tool`
- `cst_toolbox_invoke_tool`
- `cst_toolbox_list_pipelines_tool`
- `cst_toolbox_usage_guide_tool`

## Parameter Sweep Tools

The sweep tools are modeled after public CST parameter-sweep workflows, but implemented as native MCP tools:

- `cst_sweep_preview_tool` parses parameter specs and previews generated cases without opening CST.
- `cst_sweep_run_tool` copies the source `.cst` project and its companion folder for each case, writes parameters through CST history commands, saves each case, and can optionally run the solver, export Touchstone, and export selected 1D result tree items.

Accepted sweep specs include:

```json
{
  "w": "1:3:0.5",
  "h": [10, 20],
  "eps": "2.2,2.8,3.4"
}
```

Modes:

- `cartesian`: all combinations
- `single`: sweep the first parameter only, keep others fixed at their first value
- `zip`: pair values by index

## Typed Wrapper Generation

The vendored toolbox schemas can be converted into Python typed helper functions:

- `cst_toolbox_schema_catalog_tool`
- `cst_toolbox_generate_typed_wrappers_tool`

The default generated module is `generated/cst_toolbox_wrappers.py`. It currently contains wrappers for the 113 vendored toolbox commands.

## Notes

- This first version is a direct API server, not an in-CST socket bridge.
- A persistent CST-side bridge can be added later if lower-latency live injection is needed.
- Prefer commands recorded by CST Macro Recorder, then parameterize them through MCP calls.
- Result reading generally requires a saved `.cst` project.
