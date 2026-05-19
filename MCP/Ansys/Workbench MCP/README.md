# ANSYS Workbench MCP

This folder contains a portable MCP server plus an ANSYS Mechanical ACT bridge for controlling Workbench and Mechanical from an MCP client.

It is intentionally limited to reusable source files. Local virtual environments, job outputs, queue responses, solver result databases, and user-specific paths are not included.

## Contents

- `server.py` exposes Workbench, Mechanical, file queue, and socket timer MCP tools.
- `tools/` contains Python-side helpers for launching Workbench jobs and communicating with Mechanical.
- `workbench_plugin/` contains the ACT extension loaded by ANSYS Mechanical.
- `.env.example` documents the environment variables needed on each machine.
- `examples/codex_config.example.toml` shows a Codex MCP registration shape.

## Install

From this folder:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -U pip
.\.venv\Scripts\python.exe -m pip install -e .[mechanical]
```

Copy `.env.example` to `.env` and set your local ANSYS paths.

## Configure Mechanical ACT

Install the plugin files into the ANSYS ACT extensions directory for your version, for example:

```text
%APPDATA%\Ansys\v261\ACT\extensions\WorkbenchMCP.xml
%APPDATA%\Ansys\v261\ACT\extensions\WorkbenchMCP\main.py
%APPDATA%\Ansys\v261\ACT\extensions\WorkbenchMCP\mechanical_queue_processor.py
%APPDATA%\Ansys\v261\ACT\extensions\WorkbenchMCP\mechanical_socket_timer_v7.py
```

When the ACT plugin is installed outside this folder, set these environment variables before launching Mechanical:

```text
WORKBENCH_MCP_ROOT=<path to this folder>
WORKBENCH_MCP_QUEUE_ROOT=<path to this folder>\workbench_queue
WORKBENCH_MCP_PORT=9885
```

Open Mechanical and use the `Workbench MCP` toolbar:

- `Process MCP Queue` processes pending file queue requests once.
- `Socket Timer Start` starts the localhost socket bridge.
- `Socket Timer Stop` stops the socket bridge.

The plugin also auto-starts the queue timer and socket timer by default. Set `WORKBENCH_MCP_AUTO_START_SOCKET=0` or `WORKBENCH_MCP_AUTO_START_QUEUE=0` to disable those behaviors.

## MCP Tools

The server exposes tools for:

- detecting Workbench and PyMechanical
- launching Workbench journals
- launching Mechanical Python scripts
- reading job logs and status
- submitting queue requests to Mechanical
- executing Python in the currently open Mechanical session through the queue or socket timer bridge

## Notes

This project still requires a licensed ANSYS installation on the user's machine. It does not include ANSYS binaries, solver result files, or private local configuration.
