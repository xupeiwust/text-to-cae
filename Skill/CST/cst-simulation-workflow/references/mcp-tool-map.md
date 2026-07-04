# CST MCP Tool Map

Use this file to map workflow steps to this repository's CST MCP tools.

## Native CST MCP Tools

Prefer native tools for live CST Design Environment control.

| Workflow need | Preferred tool |
| --- | --- |
| detect CST install, Python paths, running DEs | `cst_detect_tool` |
| connect or launch CST | `cst_connect_tool` |
| inspect current project/session | `cst_project_info_tool` |
| create project | `cst_new_project_tool` |
| open project | `cst_open_project_tool` |
| save project | `cst_save_project_tool` |
| add VBA/history commands | `cst_add_to_history_tool` |
| run configured 3D solver | `cst_run_solver_tool` |
| list result tree | `cst_list_results_tool` |
| read 1D result item | `cst_read_1d_result_tool` |
| export Touchstone | use the MCP export tool if available, otherwise runtime export helpers |
| advanced custom control | `cst_run_python_tool` only when simpler tools cannot express the operation |

Use small named `cst_add_to_history_tool` calls. Suggested titles:

- `set units and background`
- `define materials`
- `create substrate`
- `create patch`
- `create feed`
- `define ports`
- `set boundaries`
- `set mesh`
- `set solver`
- `set monitors`

## Runtime / Toolbox Wrapper Tools

Use runtime wrappers for broader command catalogs, workflows, result exports, and optimization helpers:

| Workflow need | Tool |
| --- | --- |
| detect runtime availability | `cst_runtime_detect_tool` or `cst_toolbox_detect_tool` |
| list runtime commands | `cst_runtime_list_tools_tool` or `cst_toolbox_list_tools_tool` |
| inspect command schema | `cst_runtime_describe_tool` or `cst_toolbox_describe_tool` |
| create args JSON template | `cst_runtime_args_template_tool` or `cst_toolbox_args_template_tool` |
| invoke runtime command | `cst_runtime_invoke_tool` or `cst_toolbox_invoke_tool` |
| list pipelines | `cst_runtime_list_pipelines_tool` or `cst_toolbox_list_pipelines_tool` |
| usage guide | `cst_runtime_usage_guide_tool` or `cst_toolbox_usage_guide_tool` |

When using `cst_runtime_invoke_tool`, pass the runtime command name and JSON args. Example:

```json
{
  "tool_name": "list-result-items",
  "args": {
    "project_path": "E:\\Code\\CAE-Agent-Hub\\cst_runs\\case.cst"
  }
}
```

## Parameter Sweep Tools

Use native sweep tools before hand-rolling loops:

| Workflow need | Tool |
| --- | --- |
| preview generated parameter cases | `cst_sweep_preview_tool` |
| run copied per-case projects | `cst_sweep_run_tool` |

Always preview when case count is unknown. Report generated case count, mode, output directory, and whether solves are enabled.

## Typed Wrapper Tools

Use only when developing or refreshing helper code around the vendored toolbox:

| Workflow need | Tool |
| --- | --- |
| inspect schema catalog | `cst_toolbox_schema_catalog_tool` |
| generate typed wrappers | `cst_toolbox_generate_typed_wrappers_tool` |

Do not use typed wrapper generation as part of a normal simulation workflow.

## Fallback Rules

- If a native MCP tool exists for a live action, use it before `cst_run_python_tool`.
- If no native tool exists, prefer CST Macro Recorder-style VBA through `cst_add_to_history_tool`.
- Use `cst_run_python_tool` for inspection or control that cannot be expressed by history commands or existing tools.
- Use runtime wrappers when the task needs repeatable workspace pipelines, result export helpers, optimization, or a large predefined modeling command.
- Do not invent unverified tool names. Inspect available tools when uncertain.
