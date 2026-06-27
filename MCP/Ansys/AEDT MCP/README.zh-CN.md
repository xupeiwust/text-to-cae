# Ansys AEDT MCP

该模块通过 PyAEDT 让 Codex 等 MCP 客户端控制 Ansys Electronics Desktop 2026 R1。

## 架构

```text
Codex -> FastMCP stdio server -> 单次 PyAEDT Worker -> 明确的 AEDT PID 或 gRPC port
```

AEDT 内部不再运行 MCP 脚本、socket server、扩展或后台线程。每次操作启动一个外部 Worker，连接一个明确目标，执行一个命令，调用 `release_desktop(close_projects=False, close_on_exit=False)`，然后退出。MCP 进程不会长期持有 AEDT Automation 对象。

## 安装

使用 Python 3.10 或更高版本：

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -U pip
.\.venv\Scripts\python.exe -m pip install -e .
```

项目固定使用 PyAEDT 1.1.0，支持 AEDT 2026 R1。

根据 `.env.example` 配置 MCP 客户端。使用 `launch_aedt` 时，`AEDT_INSTALL_DIR` 必须指向包含 `ansysedt.exe` 的目录。

## MCP 配置

参考 `examples/mcp_config.example.json`，将 `<repo>` 替换成本目录的绝对路径。

## 会话选择

系统没有隐式默认 AEDT 会话。

1. 调用 `list_aedt_sessions`。
2. 明确选择一个进程 PID 或 gRPC port。
3. 每个操作工具必须且只能传入 `pid` 或 `port` 之一。

同时打开多个 AEDT 时，不会自动选择最近启动或前台窗口。通过 `launch_aedt` 启动的会话优先使用返回的 gRPC port。

## 使用方式

### 连接用户手动打开的 AEDT

1. 正常启动图形化 AEDT 2026 R1。
2. 调用 `list_aedt_sessions` 找到目标 PID。
3. 调用 `check_aedt_connection(pid=<PID>)`。
4. 后续工程和求解工具继续使用同一个 PID。

### 启动可见的 gRPC AEDT

1. 调用 `launch_aedt(port=0)`。
2. 保存返回的 PID 和 port。
3. 后续工具使用该 port。

启动命令为 `ansysedt.exe -grpcsrv <port>`，不会添加非图形模式参数。若启动超时，AEDT 会保留运行供检查，MCP 不会强制结束它。

## 工具

- `list_aedt_sessions`：只读发现 AEDT PID 和本地监听端口，不附加会话。
- `launch_aedt`：启动图形化 AEDT 2026 R1 gRPC 会话。
- `check_aedt_connection`：对明确目标执行真实 PyAEDT 探测。
- `release_connection`：执行连接和释放验证，不关闭 AEDT。
- `get_project_info`：读取活动工程和设计信息。
- `create_hfss_design`：创建或激活指定 HFSS design。
- `save_project`：保存当前工程或另存到指定路径。
- `start_analysis`：启动指定 HFSS setup，默认非阻塞。
- `get_analysis_status`：查询求解状态和 setup 列表。

资源：

- `aedt://status`：只做会话发现，不附加 AEDT。
- `aedt://agent-instructions`：目标选择和生命周期规则。

## 故障隔离

- 每个 Worker 都有超时。
- Worker 超时只结束 Worker，不结束 AEDT。
- 同一目标的操作串行执行。
- 不同明确目标可以独立执行。
- PyAEDT 日志写入 `AEDT_LOG_DIR`，不会污染 MCP stdio JSON。

## 清理旧工具栏

旧版曾在 AEDT 中安装 `Start AEDT MCP Bridge` 和 `Stop AEDT MCP Bridge`。新版不再使用这些按钮。可运行：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\scripts\remove_legacy_aedt_mcp_toolbar.ps1" -AedtRoot "G:\ANSYS206\ANSYS Inc\v261\AnsysEM"
```

脚本只移除已知旧按钮和脚本，保留 `TabConfig.xml.bak_aedt_mcp` 以及其他 Toolkit 配置。清理后重启 AEDT。

## 验证

离线测试：

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

实机验收必须同时覆盖 PID 附加和 gRPC 启动，并确认正常关闭 AEDT 时不再出现“being used by another application, script or extension wizard”弹窗。
