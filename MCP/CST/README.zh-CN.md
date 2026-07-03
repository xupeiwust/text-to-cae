# CST Studio Suite MCP

这个目录提供一个用于 CST Studio Suite 2026 的 MCP Server。它通过 CST 自带 Python API 控制可见的 CST Design Environment，让 Agent 执行建模、材料、边界条件、网格、求解器、后处理和结果读取等操作。

## 能力

- 检测 CST Python、CST 主程序和正在运行的 Design Environment
- 连接已有 CST GUI 或启动新实例
- 打开、创建、保存 `.cst` 项目
- 读取当前项目、打开项目列表和最近消息
- 执行 CST VBA/history 命令
- 运行 3D 项目求解器
- 读取 result tree 和 1D 结果
- 导出 Touchstone
- 通过 `cst_run_python_tool` 执行高级自定义控制代码
- 通过 `cst_runtime_*` wrapper 调用 vendored `bbl21/cst-runtime-cli` 工具集
- 预览和运行参数扫参，自动生成每个 case 的项目副本、CSV 汇总、可选求解、Touchstone 导出和 1D 结果导出
- 根据 vendored toolbox 的 schema 自动生成 Python typed wrapper

## Codex 配置示例

把下面配置加入 `C:\Users\Cai\.codex\config.toml`：

```toml
[mcp_servers.cst-studio-suite]
command = "E:\\Code\\CAE-Agent-Hub\\MCP\\CST\\.venv\\Scripts\\python.exe"
args = ["E:\\Code\\CAE-Agent-Hub\\MCP\\CST\\mcp_server.py"]
env = { CST_INSTALL_ROOT = "G:\\Program Files\\CST Studio Suite 2026", CST_DESIGN_ENVIRONMENT_EXE = "G:\\Program Files\\CST Studio Suite 2026\\AMD64\\CST DESIGN ENVIRONMENT_AMD64.exe" }
```

`command` 使用本目录独立的 `.venv`。本项目会自动通过 `CST_INSTALL_ROOT` 注入 CST 的 `cst.interface` 和 `cst.results` 路径。

如果改用 CST 自带 Python，需要先确保里面安装了完整 MCP 依赖。当前这台机器上的 CST Python 能导入 `cst`，但缺少 MCP 依赖 `anyio`，所以示例没有直接使用它。

## 常用原生工具顺序

1. `cst_detect_tool`
2. `cst_connect_tool`，如果没有运行中的 CST，可设置 `launch_if_needed=true`
3. `cst_project_info_tool`
4. `cst_new_project_tool` 或 `cst_open_project_tool`
5. `cst_add_to_history_tool` 添加材料、几何、边界、网格和求解器设置
6. `cst_save_project_tool`
7. `cst_run_solver_tool`
8. `cst_list_results_tool`
9. `cst_read_1d_result_tool`

## vendored cst-runtime-cli 工具

本 MCP 还把 `bbl21/cst-runtime-cli` 放在 `vendor/cst-runtime-cli` 下，并通过这些 wrapper 暴露：

- `cst_runtime_detect_tool`
- `cst_runtime_list_tools_tool`
- `cst_runtime_describe_tool`
- `cst_runtime_args_template_tool`
- `cst_runtime_invoke_tool`
- `cst_runtime_list_pipelines_tool`
- `cst_runtime_usage_guide_tool`

先用 `cst_runtime_list_tools_tool` 查看完整 runtime 工具目录，再用 `cst_runtime_invoke_tool` 按名称调用任意 runtime 命令：

```json
{
  "tool_name": "list-result-items",
  "args": {
    "project_path": "E:\\Code\\CAE-Agent-Hub\\cst_runs\\case.cst"
  }
}
```

原生 MCP 工具仍然更适合直接控制当前 CST GUI 会话。`cst_runtime_*` wrapper 更适合调用更大的命令目录、workspace workflow、结果导出、优化辅助和预定义建模操作。

同一组能力也提供了不含 `runtime` 的短别名：

- `cst_toolbox_detect_tool`
- `cst_toolbox_list_tools_tool`
- `cst_toolbox_describe_tool`
- `cst_toolbox_args_template_tool`
- `cst_toolbox_invoke_tool`
- `cst_toolbox_list_pipelines_tool`
- `cst_toolbox_usage_guide_tool`

## 参数扫参工具

参数扫参工具参考公开 CST 参数化扫参项目的工作流，但实现为原生 MCP 工具：

- `cst_sweep_preview_tool`：解析参数范围并预览将生成的 case，不打开 CST、不修改文件。
- `cst_sweep_run_tool`：为每个 case 复制源 `.cst` 项目和 companion 文件夹，通过 CST history 命令写入参数，保存 case，并可选运行求解器、导出 Touchstone、导出指定 1D result tree 项。

支持的扫参规格示例：

```json
{
  "w": "1:3:0.5",
  "h": [10, 20],
  "eps": "2.2,2.8,3.4"
}
```

扫参模式：

- `cartesian`：所有参数做笛卡尔积组合
- `single`：只扫第一个参数，其他参数固定为第一个值
- `zip`：按索引配对各参数值

## Typed Wrapper 生成

vendored toolbox 的 schema 可以自动转换成 Python typed helper functions：

- `cst_toolbox_schema_catalog_tool`
- `cst_toolbox_generate_typed_wrappers_tool`

默认生成文件是 `generated/cst_toolbox_wrappers.py`。当前已生成 113 个 vendored toolbox 命令的 wrapper。

## 建模示例

```python
cst_add_to_history_tool(
    title="create copper brick",
    vba_code="""
With Brick
    .Reset
    .Name "patch"
    .Component "component1"
    .Material "Copper (annealed)"
    .Xrange "-10", "10"
    .Yrange "-8", "8"
    .Zrange "0", "0.035"
    .Create
End With
"""
)
```

## 求解器示例

```python
cst_add_to_history_tool(
    title="frequency-domain setup",
    vba_code="""
ChangeSolverType "HF Frequency Domain"
Solver.FrequencyRange "1", "10"
FDSolver.OrderTet "First"
FDSolver.MeshAdaptionTet "True"
"""
)
```

## 注意

- 当前版本是直接 API 版，不需要 CST 内部 socket bridge。
- 如果后续需要更强的实时会话注入能力，可以在这个项目里增加 CST 内部常驻 bridge。
- 建议优先使用 CST Macro Recorder 录制手工流程，再把生成的 VBA 整理成 MCP 工具调用。
- 结果读取依赖保存后的 `.cst` 项目；长求解前请先保存项目。
