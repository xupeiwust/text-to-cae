# Ansys AEDT MCP

这是 CAE Agent Hub 的一部分。本模块提供 Hub 中 Ansys 工具族的 Ansys Electronics Desktop / HFSS MCP bridge。

这个目录包含一个可移植的 MCP server，以及一个用于 Ansys Electronics Desktop 2026 R1 的 raw TCP JSON bridge。Codex 等支持 MCP 的客户端可以通过它连接正在运行的 AEDT 会话，查看工程、创建 HFSS design、保存工程，并执行小段 AEDT Python 脚本。

整体结构参考本仓库的 Abaqus MCP：

```text
MCP client
  <stdio MCP>
mcp_server.py
  <local raw TCP JSON, default 127.0.0.1:48252>
在 AEDT 内运行的 aedt_mcp_bridge.py
  <oDesktop / oProject / oDesign scripting API>
Ansys Electronics Desktop / HFSS
```

它不使用 HTTP，也不使用 WebSocket。桥接层是 localhost 上的换行分隔 JSON TCP 协议。

## 内容

- `mcp_server.py`：外部 stdio MCP server。
- `aedt_mcp_bridge.py`：在 AEDT 内运行的 bridge 脚本。
- `reload_bridge_in_aedt.py`：在已运行 AEDT 会话中重载 bridge 的辅助脚本。
- `aedt_socket_protocol.py`：raw TCP JSON 协议辅助函数。
- `stop_mcp.py`：请求正在运行的 AEDT bridge 停止。
- `scripts/launch_aedt_with_mcp_bridge.ps1`：可选的旧版外部 launcher，用于从 AEDT 外部启动或连接 AEDT。
- `scripts/install_aedt_mcp_autostart.ps1`：可选的旧版快捷方式安装脚本；当前推荐流程不再使用它。
- `scripts/install_aedt_toolkit_button.ps1`：给 HFSS 和 Project 上下文安装 AEDT 原生 Toolkit / Automation ribbon gallery 下拉按钮。
- `scripts/start_aedt_mcp_bridge_in_aedt.py`：适合放到 AEDT 脚本菜单里手动启动/重载 bridge 的入口。
- `.env.example`：bridge 端口、超时和 token 配置。
- `examples/mcp_config.example.json`：通用 MCP 客户端配置示例。
- `tests/`：不依赖 AEDT 的协议单元测试。

## 安装

在本目录下执行：

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -U pip
.\.venv\Scripts\python.exe -m pip install -e .
```

如果这台机器上的 `py` 或 `python` 解析不稳定，可以改用 Codex runtime Python 或其他确定可用的 Python 3.10+。

## 旧版 Launcher

外部 launcher 快捷方式已经不是当前推荐默认入口，因为 AEDT 里已经有原生的 `AEDT MCP` 下拉按钮。

旧版快捷方式安装脚本保留为可选辅助工具：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\scripts\install_aedt_mcp_autostart.ps1"
```

如果 AEDT 已经打开，可以这样只做连接和重载验证，不创建快捷方式：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\scripts\launch_aedt_with_mcp_bridge.ps1" -NoLaunch
```

## AEDT Automation 下拉按钮

安装 AEDT 原生 Toolkit gallery 下拉按钮：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\scripts\install_aedt_toolkit_button.ps1"
```

这个脚本会修改 `HFSS` 和 `Project` 两个 Toolkit 的 `TabConfig.xml`，并先创建 `.bak_aedt_mcp` 备份。ribbon 入口是：

```text
AEDT MCP
  Start AEDT MCP Bridge
  Stop AEDT MCP Bridge
```

如果 AEDT 已经打开，可以通过 live bridge 执行下面这句刷新，或者直接重启 AEDT：

```python
oDesktop.RefreshToolkitUI()
```

刷新后在 `Automation` ribbon tab 的 `Codex MCP` panel 下查看。打开 `AEDT MCP`，即可点击 `Start AEDT MCP Bridge` 或 `Stop AEDT MCP Bridge`。

## 在 AEDT 内手动启动 Bridge

Automation 按钮之外，也可以手动启动：

1. 打开 Ansys Electronics Desktop 2026 R1。
2. 在 AEDT 的 Script Editor 或脚本菜单中运行 `scripts\start_aedt_mcp_bridge_in_aedt.py`，也可以直接运行 `reload_bridge_in_aedt.py`。
3. 确认 AEDT 消息或日志里出现：

```text
AEDT MCP bridge listening on 127.0.0.1:48252
```

可选环境变量：

```text
AEDT_MCP_HOST=127.0.0.1
AEDT_MCP_PORT=48252
AEDT_MCP_TIMEOUT=60
AEDT_MCP_TOKEN=
AEDT_MCP_LOG=%TEMP%\aedt_mcp_socket_bridge.log
```

除非明确需要远程访问，否则 `AEDT_MCP_HOST` 保持 `127.0.0.1`。

## MCP 客户端配置

把 `<repo>` 替换成本目录的绝对路径。

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

## 工具

- `ping`：验证 AEDT 侧 bridge，并返回 live session telemetry。
- `check_aedt_connection`：返回简洁的人类可读连接状态。
- `run_script`：在 bridge 命名空间中执行 AEDT Python；设置 `result` 变量来返回结构化数据。
- `get_project_info`：查看当前工程和 design 状态。
- `create_hfss_design`：创建或激活 HFSS design。
- `save_project`：保存当前 AEDT 工程。

资源：

- `aedt://status`
- `aedt://agent-instructions`

## 推荐工作流

1. 从普通 Ansys Electronics Desktop 快捷方式启动 AEDT。
2. 在 AEDT 的 `Automation` ribbon 中打开 `AEDT MCP`，点击 `Start AEDT MCP Bridge`。
3. 从 Codex 调用 `ping`。
4. 调用 `get_project_info`。
5. 对不确定的 AEDT API 行为，先用小段 `run_script` 探测。
6. 当前会话状态明确后，再使用 `create_hfss_design` 等高层工具。

## 说明

这是本仓库里 AEDT raw TCP bridge 的第一版实现。当前重点是让外部 MCP 和已打开的 AEDT 稳定通讯。当前 AEDT 内部入口通过 Toolkit `TabConfig.xml` 安装到 Automation ribbon。

后续可以继续增加 HFSS 专用 MCP 工具，例如几何、材料、边界、激励、setup、求解和报告导出。

本项目不包含 Ansys 二进制文件、许可证、用户工程、求解结果或本机私有配置。
