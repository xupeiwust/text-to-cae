# CST Workflow

Use this file for task routing and execution order.

## Universal Preflight

1. Confirm the user wants one of: plan only, new project, existing project edit, sweep, or optimization.
2. Check the CST MCP with `cst_detect_tool`.
3. Connect with `cst_connect_tool`; set `launch_if_needed=true` only when the user wants execution or live inspection.
4. Choose a run directory under `cst_runs/<short_task>_<YYYYMMDD>` unless the user specified a path.
5. Record whether the task is destructive, expensive, or only a plan.

Do not run CST for plan-only tasks. Return the workflow, assumptions, expected outputs, and the MCP tools that would be used.

## New Project Flow

1. Select a template from `templates.md` or derive a case-specific setup.
2. Resolve required inputs with `parameter-policy.md`.
3. Show the defaults card if the solve may be expensive.
4. Create the project with `cst_new_project_tool`.
5. Add history blocks with `cst_add_to_history_tool` in small named chunks:
   - units and background
   - materials
   - geometry
   - ports/excitations
   - boundaries and symmetry
   - mesh/adaptation
   - solver
   - monitors
6. Save with `cst_save_project_tool`.
7. Run with `cst_run_solver_tool` only after save.
8. List results with `cst_list_results_tool`.
9. Read selected 1D results with `cst_read_1d_result_tool`, export Touchstone when S-parameters are requested.
10. Generate the report.

## Existing Project Flow

1. Locate the source `.cst` file or active project.
2. Inspect with `cst_project_info_tool` and, when needed, `cst_list_results_tool`.
3. Copy source `.cst` and companion result folder to a run directory before editing.
4. Open the working copy with `cst_open_project_tool`.
5. Read available parameters, entities, ports, monitors, solver settings, and result tree if the MCP/runtime tools expose them.
6. Change only requested parameters or settings.
7. Save, solve, export, validate, and report.

Never rebuild an existing project from scratch unless the user asks for a rebuild.

## Parameter Sweep Flow

1. Require a source `.cst` project or a generated baseline working project.
2. Parse parameter specs such as `w=1:3:0.5`, arrays, or CSV-like lists.
3. Preview cases with `cst_sweep_preview_tool`.
4. Show case count before running if count is large or solves are enabled.
5. Run with `cst_sweep_run_tool`.
6. Summarize CSV outputs, result exports, failed cases, and best case by the chosen objective.

Use `single` mode for quick one-factor sweeps, `zip` when values are paired, and `cartesian` only when the case count is acceptable.

## Optimization Flow

1. Confirm objective type, target, parameter bounds, maximum rounds, and stopping rule.
2. If using the vendored runtime, inspect available pipelines with `cst_runtime_list_pipelines_tool` or `cst_toolbox_list_pipelines_tool`.
3. Prefer runtime optimization helpers for multi-round loops. Do not hand-write a large independent optimizer unless the user explicitly asks for custom code.
4. Every round must include: prepare parameters, run/refresh simulation, export/read results, compute objective, decide stop/continue.
5. Stop early when the target is met or the configured no-improvement rule fires.

## Default Report Shape

Produce a Markdown report unless the user asked for HTML:

- task summary
- source project and working project paths
- assumptions/defaults
- tool sequence used
- parameter table
- solver and monitor setup
- result file paths
- validation status
- issues and next recommended changes
