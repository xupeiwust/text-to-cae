#!/usr/bin/env python3
from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from cst_automation import CSTSessionManager, dumps
from cst_parameter_sweep import CSTParameterSweepRunner, preview_sweep
from cst_runtime_cli_bridge import (
    describe_runtime_tool,
    detect_runtime,
    invoke_runtime_tool,
    list_runtime_pipelines,
    list_runtime_tools,
    runtime_args_template,
    runtime_usage_guide,
)
from cst_typed_wrapper_generator import generate_typed_wrappers, load_runtime_schema_catalog


INSTRUCTIONS = """You are controlling CST Studio Suite through MCP.

Prefer CST's native Python API and recorded VBA/history commands over GUI
click automation. Inspect the active project before changing it. Use small,
named history commands for geometry, materials, boundary conditions, mesh, and
solver setup so the CST history tree remains understandable. Save projects
before long solves, and read the message log and result tree after every solve.
"""

mcp = FastMCP("cst-studio-suite-mcp", instructions=INSTRUCTIONS)
session = CSTSessionManager()
sweep_runner = CSTParameterSweepRunner(session)


@mcp.tool()
def cst_detect_tool() -> dict[str, Any]:
    """Detect CST Python modules, CST executable path, and running Design Environments."""
    return session.detect_environment()


@mcp.tool()
def cst_list_design_environments_tool() -> dict[str, Any]:
    """List running CST Design Environment process IDs."""
    return session.list_running()


@mcp.tool()
def cst_connect_tool(pid_or_address: int | str | None = None, launch_if_needed: bool = False) -> dict[str, Any]:
    """Connect to a running CST Design Environment, optionally launching one if none exists."""
    return session.connect(pid_or_address=pid_or_address, launch_if_needed=launch_if_needed)


@mcp.tool()
def cst_launch_tool(options: list[str] | None = None) -> dict[str, Any]:
    """Launch a new CST Design Environment instance."""
    return session.launch_new(options=options)


@mcp.tool()
def cst_project_info_tool() -> str:
    """Return active CST project metadata, open projects, and recent messages."""
    return dumps(session.get_project_info())


@mcp.tool()
def cst_active_project_tool() -> dict[str, Any]:
    """Attach this MCP session to the active project in the connected CST instance."""
    return session.active_project()


@mcp.tool()
def cst_open_project_tool(path: str) -> dict[str, Any]:
    """Open a .cst project in the connected CST Design Environment."""
    return session.open_project(path)


@mcp.tool()
def cst_new_project_tool(project_type: str = "mws") -> dict[str, Any]:
    """Create a new CST project. project_type: mws, ems, ps, mps, cs, pcbs, or ds."""
    return session.new_project(project_type=project_type)


@mcp.tool()
def cst_save_project_tool(path: str | None = None) -> dict[str, Any]:
    """Save the active CST project, optionally to a target .cst path."""
    return session.save_project(path=path)


@mcp.tool()
def cst_add_to_history_tool(title: str, vba_code: str) -> dict[str, Any]:
    """Add CST VBA/history commands to the active 3D project history tree."""
    return session.add_to_history(title=title, vba_code=vba_code)


@mcp.tool()
def cst_execute_vba_tool(vba_code: str) -> dict[str, Any]:
    """Execute VBA code directly in the active 3D project. A Sub Main wrapper is added if absent."""
    return session.execute_vba(vba_code=vba_code)


@mcp.tool()
def cst_run_solver_tool() -> dict[str, Any]:
    """Run the configured solver for the active 3D project."""
    return session.run_solver()


@mcp.tool()
def cst_run_python_tool(code: str) -> dict[str, Any]:
    """Execute Python inside this MCP process with manager, de, prj/project, and model3d variables.

    Assign a variable named result to return structured data.
    """
    return session.run_python(code=code)


@mcp.tool()
def cst_list_results_tool(cst_file: str | None = None, module: str = "3d") -> dict[str, Any]:
    """List CST result tree items from a saved project file or the active project."""
    return session.list_results(cst_file=cst_file, module=module)


@mcp.tool()
def cst_read_1d_result_tool(
    tree_path: str,
    cst_file: str | None = None,
    module: str = "3d",
    max_points: int = 2000,
) -> dict[str, Any]:
    """Read a 1D result tree item such as '1D Results\\S-Parameters\\S1,1'."""
    return session.read_1d_result(
        tree_path=tree_path,
        cst_file=cst_file,
        module=module,
        max_points=max_points,
    )


@mcp.tool()
def cst_export_touchstone_tool(
    filename: str,
    impedance: float = 50.0,
    export_type: str = "S",
    data_format: str = "RI",
    frequency_range: str = "Full",
) -> dict[str, Any]:
    """Export S/Y/Z parameters through CST's TOUCHSTONE VBA command."""
    return session.export_touchstone(
        filename=filename,
        impedance=impedance,
        export_type=export_type,
        data_format=data_format,
        frequency_range=frequency_range,
    )


@mcp.tool()
def cst_sweep_preview_tool(
    parameters: dict[str, Any],
    mode: str = "cartesian",
    max_cases: int = 200,
) -> dict[str, Any]:
    """Preview a CST parameter sweep without opening CST or modifying files."""
    return preview_sweep(parameters=parameters, mode=mode, max_cases=max_cases)


@mcp.tool()
def cst_sweep_run_tool(
    project_path: str,
    parameters: dict[str, Any],
    output_dir: str | None = None,
    mode: str = "cartesian",
    run_solver: bool = False,
    export_touchstone: bool = False,
    result_tree_paths: list[str] | None = None,
    max_cases: int = 200,
    overwrite: bool = False,
    continue_on_error: bool = True,
    close_after_case: bool = True,
    result_max_points: int = 2000,
) -> dict[str, Any]:
    """Run a CST parameter sweep and write per-case projects plus sweep_summary.csv."""
    return sweep_runner.run_sweep(
        project_path=project_path,
        parameters=parameters,
        output_dir=output_dir,
        mode=mode,
        run_solver=run_solver,
        export_touchstone=export_touchstone,
        result_tree_paths=result_tree_paths,
        max_cases=max_cases,
        overwrite=overwrite,
        continue_on_error=continue_on_error,
        close_after_case=close_after_case,
        result_max_points=result_max_points,
    )


@mcp.tool()
def cst_runtime_detect_tool() -> dict[str, Any]:
    """Detect the vendored cst-runtime-cli bridge used by the extended CST tools."""
    return detect_runtime()


@mcp.tool()
def cst_runtime_list_tools_tool(timeout_seconds: float | None = None) -> dict[str, Any]:
    """List all vendored cst-runtime-cli tools available through this MCP server."""
    return list_runtime_tools(timeout_seconds=timeout_seconds)


@mcp.tool()
def cst_runtime_describe_tool(tool_name: str, timeout_seconds: float | None = None) -> dict[str, Any]:
    """Return schema, template, runbook, and direct flags for one cst-runtime-cli tool."""
    return describe_runtime_tool(tool_name=tool_name, timeout_seconds=timeout_seconds)


@mcp.tool()
def cst_runtime_args_template_tool(tool_name: str, timeout_seconds: float | None = None) -> dict[str, Any]:
    """Generate an argument template for one cst-runtime-cli tool."""
    return runtime_args_template(tool_name=tool_name, timeout_seconds=timeout_seconds)


@mcp.tool()
def cst_runtime_invoke_tool(
    tool_name: str,
    args: dict[str, Any] | None = None,
    workspace: str | None = None,
    timeout_seconds: float | None = None,
) -> dict[str, Any]:
    """Invoke any vendored cst-runtime-cli tool by name with JSON arguments."""
    return invoke_runtime_tool(
        tool_name=tool_name,
        args=args,
        workspace=workspace,
        timeout_seconds=timeout_seconds,
    )


@mcp.tool()
def cst_runtime_list_pipelines_tool(timeout_seconds: float | None = None) -> dict[str, Any]:
    """List cst-runtime-cli pipeline recipes available through this MCP server."""
    return list_runtime_pipelines(timeout_seconds=timeout_seconds)


@mcp.tool()
def cst_runtime_usage_guide_tool(timeout_seconds: float | None = None) -> dict[str, Any]:
    """Return the cst-runtime-cli machine-readable usage guide for agents."""
    return runtime_usage_guide(timeout_seconds=timeout_seconds)


@mcp.tool()
def cst_toolbox_detect_tool() -> dict[str, Any]:
    """Alias for cst_runtime_detect_tool without the runtime naming."""
    return cst_runtime_detect_tool()


@mcp.tool()
def cst_toolbox_list_tools_tool(timeout_seconds: float | None = None) -> dict[str, Any]:
    """Alias for cst_runtime_list_tools_tool without the runtime naming."""
    return cst_runtime_list_tools_tool(timeout_seconds=timeout_seconds)


@mcp.tool()
def cst_toolbox_describe_tool(tool_name: str, timeout_seconds: float | None = None) -> dict[str, Any]:
    """Alias for cst_runtime_describe_tool without the runtime naming."""
    return cst_runtime_describe_tool(tool_name=tool_name, timeout_seconds=timeout_seconds)


@mcp.tool()
def cst_toolbox_args_template_tool(tool_name: str, timeout_seconds: float | None = None) -> dict[str, Any]:
    """Alias for cst_runtime_args_template_tool without the runtime naming."""
    return cst_runtime_args_template_tool(tool_name=tool_name, timeout_seconds=timeout_seconds)


@mcp.tool()
def cst_toolbox_invoke_tool(
    tool_name: str,
    args: dict[str, Any] | None = None,
    workspace: str | None = None,
    timeout_seconds: float | None = None,
) -> dict[str, Any]:
    """Alias for cst_runtime_invoke_tool without the runtime naming."""
    return cst_runtime_invoke_tool(
        tool_name=tool_name,
        args=args,
        workspace=workspace,
        timeout_seconds=timeout_seconds,
    )


@mcp.tool()
def cst_toolbox_list_pipelines_tool(timeout_seconds: float | None = None) -> dict[str, Any]:
    """Alias for cst_runtime_list_pipelines_tool without the runtime naming."""
    return cst_runtime_list_pipelines_tool(timeout_seconds=timeout_seconds)


@mcp.tool()
def cst_toolbox_usage_guide_tool(timeout_seconds: float | None = None) -> dict[str, Any]:
    """Alias for cst_runtime_usage_guide_tool without the runtime naming."""
    return cst_runtime_usage_guide_tool(timeout_seconds=timeout_seconds)


@mcp.tool()
def cst_toolbox_schema_catalog_tool(category: str | None = None) -> dict[str, Any]:
    """Return the vendored CST toolbox command schema catalog, optionally filtered by category."""
    return load_runtime_schema_catalog(category=category)


@mcp.tool()
def cst_toolbox_generate_typed_wrappers_tool(
    output_path: str | None = None,
    selected_tools: list[str] | None = None,
    category: str | None = None,
    overwrite: bool = True,
) -> dict[str, Any]:
    """Generate Python typed wrapper functions from the vendored runtime command schemas."""
    return generate_typed_wrappers(
        output_path=output_path,
        selected_tools=selected_tools,
        category=category,
        overwrite=overwrite,
    )


@mcp.resource("cst://agent-instructions")
def agent_instructions() -> str:
    """CST automation guidance for MCP clients."""
    return INSTRUCTIONS


@mcp.resource("cst://environment")
def cst_environment() -> dict[str, Any]:
    """Current CST automation environment detection."""
    return session.detect_environment()


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
