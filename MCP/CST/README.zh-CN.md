# CST Studio Suite MCP

这个目录提供一个用于 CST Studio Suite 2026 的 MCP Server。它通过 CST 自带 Python API 控制可见的 CST Design Environment，让 Agent 执行 3D 全波建模、材料、端口、边界、网格、求解、后处理、结果读取，以及 CST Design Studio / Schematic 场路联合仿真相关操作。

## 当前能力

- 检测 CST Python、CST 主程序和正在运行的 Design Environment。
- 连接已有 CST GUI 或启动新实例。
- 打开、创建、保存 `.cst` 项目。
- 读取当前项目、打开项目列表和最近消息。
- 执行 CST VBA/history 命令。
- 运行 3D 项目求解器。
- 读取 result tree 和 1D 结果。
- 导出 3D Touchstone 数据。
- 通过 `cst_run_python_tool` 执行高级自定义控制代码。
- 通过 `cst_runtime_*` / `cst_toolbox_*` 调用 vendored `bbl21/cst-runtime-cli` 工具集。
- 预览和运行参数扫参，生成每个 case 的项目副本、CSV 汇总、可选求解、Touchstone 导出和 1D 结果导出。
- 根据 vendored toolbox schema 自动生成 Python typed wrapper。
- 新增 CST Design Studio / Schematic 控制能力：创建 schematic 项目、插入 Touchstone N-port、添加 R/L/C/diode/ground/external port、连线、配置 S 参数任务、运行 circuit/co-simulation、导出 schematic S 参数和 SE/IL CSV。

## Codex 配置示例

把下面配置加入 `C:\Users\Cai\.codex\config.toml`：

```toml
[mcp_servers.cst-studio-suite]
command = "E:\\Code\\CAE-Agent-Hub\\MCP\\CST\\.venv\\Scripts\\python.exe"
args = ["E:\\Code\\CAE-Agent-Hub\\MCP\\CST\\mcp_server.py"]
env = { CST_INSTALL_ROOT = "G:\\Program Files\\CST Studio Suite 2026", CST_DESIGN_ENVIRONMENT_EXE = "G:\\Program Files\\CST Studio Suite 2026\\AMD64\\CST DESIGN ENVIRONMENT_AMD64.exe" }
```

`command` 使用本目录独立 `.venv`。本项目会通过 `CST_INSTALL_ROOT` 自动注入 CST 的 `cst.interface` 和 `cst.results` 路径。

## 3D 全波常用工具顺序

1. `cst_detect_tool`
2. `cst_connect_tool`
3. `cst_project_info_tool`
4. `cst_new_project_tool` 或 `cst_open_project_tool`
5. `cst_add_to_history_tool`
6. `cst_save_project_tool`
7. `cst_run_solver_tool`
8. `cst_list_results_tool`
9. `cst_read_1d_result_tool`

## Design Studio / Schematic 新工具

- `cst_create_schematic_project_tool`
- `cst_open_schematic_project_tool`
- `cst_schematic_execute_vba_tool`
- `cst_schematic_add_to_history_tool`
- `cst_insert_em_3d_block_or_nport_tool`
- `cst_add_resistor_tool`
- `cst_add_inductor_tool`
- `cst_add_capacitor_tool`
- `cst_add_diode_spice_model_tool`
- `cst_add_ground_tool`
- `cst_add_external_port_tool`
- `cst_connect_schematic_nodes_tool`
- `cst_configure_frequency_sweep_tool`
- `cst_configure_power_sweep_tool`
- `cst_run_circuit_cosimulation_tool`
- `cst_export_schematic_sparameters_tool`
- `cst_export_se_il_vs_power_tool`

典型流程：

1. `cst_create_schematic_project_tool`
2. `cst_add_external_port_tool`
3. `cst_insert_em_3d_block_or_nport_tool`
4. `cst_add_resistor_tool`、`cst_add_inductor_tool`、`cst_add_capacitor_tool`、`cst_add_diode_spice_model_tool`、`cst_add_ground_tool`
5. `cst_connect_schematic_nodes_tool`
6. `cst_configure_frequency_sweep_tool`
7. `cst_run_circuit_cosimulation_tool`
8. `cst_list_results_tool(module="schematic")`
9. `cst_export_schematic_sparameters_tool` 或 `cst_export_se_il_vs_power_tool`

## 已验证的 Schematic 能力

本机 CST Studio Suite 2026.1 已实测通过：

- `DesignEnvironment.new_ds()` 创建 Design Studio 项目。
- `project.schematic.execute_vba_code(...)` 执行 Design Studio VBA。
- CST 暴露 `Block`、`ExternalPort`、`Net`、`SimulationTask`、`DSParameterSweep`、`TouchstoneExport`、`ResultTree`。
- `Block.SetDoubleProperty("Resistance"|"Capacitance"|"Inductance", ...)` 可设置 R/L/C 数值。
- `SimulationTask.Update()` 可运行 Schematic S 参数任务。
- `cst.results.ProjectFile(...).get_schematic()` 可读取 schematic 结果树和 1D 结果。
- Touchstone N-port block 可插入、连线、运行、再导出 `.s2p`。

## Demo

运行：

```powershell
cd E:\Code\CAE-Agent-Hub\MCP\CST
.\.venv\Scripts\python.exe .\examples\design_studio_cosim_demo.py
```

脚本会创建两阶段 demo：

- 第一阶段：Design Studio 电路，包含两个 external ports、`0.35 nH`、`0.07 pF`、`39 nH`、diode、`100 Ohm`、ground；运行 1-10 GHz、91 点 S 参数任务；导出 `.s2p` 和由 `S2,1` 计算的 SE/IL CSV。
- 第二阶段：把第一阶段导出的 `.s2p` 作为 Touchstone N-port block 插入新的 schematic，连接 external ports，运行 `SPara1`，再导出 `.s2p`。

当前本机已验证证据：

- `E:\Code\CAE-Agent-Hub\MCP\CST\examples\design_studio_cosim_demo_run\fss_rlc_diode_schematic_demo_1783569136.cst`
- `E:\Code\CAE-Agent-Hub\MCP\CST\examples\design_studio_cosim_demo_run\fss_rlc_diode_schematic_demo_1783569136_demo_log.json`
- `E:\Code\CAE-Agent-Hub\MCP\CST\examples\design_studio_cosim_demo_run\fss_rlc_diode_schematic_demo_1783569136_schematic_sparameters.s2p`
- `E:\Code\CAE-Agent-Hub\MCP\CST\examples\design_studio_cosim_demo_run\fss_rlc_diode_schematic_demo_1783569136_se_il.csv`
- `E:\Code\CAE-Agent-Hub\MCP\CST\examples\design_studio_cosim_demo_run\touchstone_nport_block_demo_1783569178.cst`
- `E:\Code\CAE-Agent-Hub\MCP\CST\examples\design_studio_cosim_demo_run\touchstone_nport_block_demo_1783569178_sparameters.s2p`

## 实验性能力

- `cst_insert_em_3d_block_or_nport_tool` 已验证 Touchstone `.sNp` N-port 路径；直接插入 CST Microwave Studio 3D project block 的接口已暴露，但仍需要结合具体 3D 项目和 CST 录制宏继续验证。
- `cst_configure_power_sweep_tool` 当前是通用 Design Studio 参数扫参 wrapper。只有当 schematic 中的 source、port、incident-field 或 nonlinear model 表达式实际引用该参数时，它才代表真实输入功率或场强 sweep。
- 完整的非线性 incident field / input power 场路联合仿真仍需要针对 FSS/超表面模型建立专用 3D 模板。

## 注意

- 当前版本是直接 API 版，不需要 CST 内部 socket bridge。
- 建模操作优先使用 CST Macro Recorder 录制的 VBA，再整理成 MCP 工具调用。
- 长时间求解前请先保存项目。
- 不要把求解器返回成功等同于结果成功；必须检查 result tree、导出文件或日志。
