# Ansys AEDT MCP

该模块通过 PyAEDT 让 Codex 等 MCP 客户端控制 Ansys Electronics Desktop 2026 R1。

## 架构

```text
Codex -> FastMCP stdio server -> 外部 PyAEDT broker -> 明确的 AEDT PID 或 gRPC port
```

AEDT 内部不运行 MCP 脚本、socket server、扩展或后台线程。MCP 会为每个明确目标建立一个外部 broker，并在多次命令之间复用同一条 PyAEDT 连接。只有调用 `release_connection`、MCP 退出或 broker 的 stdin 关闭时，broker 才执行 `release_desktop(close_projects=False, close_on_exit=False)`。

AEDT 2026 R1 的 gRPC 会话要求客户端持续存在；如果每条命令后都结束 PyAEDT 客户端，对应 gRPC 监听也会消失。外部 broker 既避免每次工具调用重建 AEDT，也不会在 AEDT 内留下 Toolkit/Automation 脚本状态。

在 Windows 上，broker 只监视它所连接的目标 AEDT 进程。如果出现 busy 弹窗，或主窗口从可见变为关闭，broker 会把它视为用户明确发出的关闭请求，通过现有 PyAEDT 会话调用 AEDT `QuitApplication()`，随后退出 broker，避免留下无窗口的 AEDT 进程。

## 安装

使用 Python 3.10 或更高版本：

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -U pip
.\.venv\Scripts\python.exe -m pip install -e .
```

项目固定使用面向 AEDT 2026 R1 的 PyAEDT 1.1.0。使用 `launch_aedt` 时，`AEDT_INSTALL_DIR` 必须指向包含 `ansysedt.exe` 的目录。

## MCP 配置

参考 `examples/mcp_config.example.json`，把 `<repo>` 替换为本目录的绝对路径。

## 明确指定目标

系统没有隐式默认 AEDT 会话。

1. 调用 `list_aedt_sessions` 或 `launch_aedt`。
2. 明确选择一个 PID 或一个 gRPC port。
3. 每个目标工具必须且只能传入 `pid` 或 `port` 之一。

服务器不会自动选择最近启动或前台窗口。探测成功后，返回的 PID 和 port 会登记为同一个 broker 的别名，因此后续可以继续使用任一明确标识访问同一会话。

## 生命周期

- `check_aedt_connection` 在首次使用时创建 broker，并执行真实 PyAEDT 探测。
- 工程和仿真工具复用该 broker。
- `release_connection` 断开 broker，但不请求关闭工程或 AEDT。
- MCP 正常退出或 broker stdin 关闭时也会释放全部连接。
- 直接关闭 AEDT 窗口会触发 `QuitApplication()`，并结束该目标的 broker。
- broker 超时只会结束 broker，不会强制结束 AEDT。

通过 MCP 启动的会话优先使用 `launch_aedt` 返回的 port。用户手动打开的 AEDT 应从 `list_aedt_sessions` 中选择 PID。

## 工具

- `list_aedt_sessions`：只读发现 AEDT PID 和本地监听端口。
- `launch_aedt`：使用明确 gRPC port 启动可见 AEDT 2026 R1。
- `check_aedt_connection`：探测一个明确目标。
- `release_connection`：停止并释放该目标的 broker。
- `get_project_info`：读取工程和活动设计信息。
- `create_hfss_design`：创建或激活指定 HFSS design。
- `save_project`：保存当前工程，可指定另存路径。
- `start_analysis`：启动指定 HFSS setup，默认非阻塞。
- `get_analysis_status`：查询求解状态和 setup。

资源 `aedt://status` 与 `aedt://agent-instructions` 不会隐式连接 AEDT。

## 清理旧工具栏

旧版的 `Start AEDT MCP Bridge` 和 `Stop AEDT MCP Bridge` 按钮不再使用。只清理这些已知条目：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\scripts\remove_legacy_aedt_mcp_toolbar.ps1" -AedtRoot "G:\ANSYS206\ANSYS Inc\v261\AnsysEM"
```

## 验证

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\scripts\run_live_acceptance.ps1 -Mode both
```

实机验收覆盖明确 PID/port、同一 broker 连续命令、一次性 HFSS 工程保存，以及 broker 仍连接时正常关闭 AEDT。若出现“being used by another application, script or extension wizard”弹窗，测试会失败。
