#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import json
from typing import Any

from mcp.server.fastmcp import FastMCP

from aedt_launcher import AedtLauncher
from aedt_target import AedtTarget
from session_discovery import SessionDiscovery
from worker_client import WorkerClient


INSTRUCTIONS = """Control Ansys Electronics Desktop 2026 R1 through external PyAEDT workers.

Call list_aedt_sessions first. Every operation that touches AEDT requires exactly
one explicit PID or gRPC port; there is no implicit or automatic session target.
Prefer the gRPC port returned by launch_aedt for MCP-launched sessions. Each tool
uses a short-lived worker that releases PyAEDT without closing projects or AEDT.
"""

mcp = FastMCP("ansys-aedt-mcp-server", instructions=INSTRUCTIONS)
worker_client = WorkerClient()
session_discovery = SessionDiscovery(worker_client=worker_client)
aedt_launcher = AedtLauncher(worker_client=worker_client)


def _target(pid: int | None, port: int | None) -> AedtTarget:
    return AedtTarget.from_values(pid=pid, port=port)


async def _worker_call(
    command: str,
    *,
    pid: int | None,
    port: int | None,
    arguments: dict[str, Any] | None = None,
    timeout: float | None = None,
) -> dict[str, Any]:
    target = _target(pid, port)
    result = await worker_client.execute_async(
        target,
        command,
        arguments or {},
        timeout=timeout,
    )
    if not isinstance(result, dict):
        raise RuntimeError(f"AEDT worker command {command} returned a non-object result")
    return result


@mcp.tool()
async def list_aedt_sessions() -> dict[str, Any]:
    """List all detected AEDT processes and listener ports without attaching."""
    sessions = await asyncio.to_thread(session_discovery.list_sessions)
    return {"sessions": sessions, "selection_required": True}


@mcp.tool()
async def launch_aedt(
    version: str = "2026.1",
    port: int = 0,
    install_dir: str = "",
    timeout: float | None = None,
) -> dict[str, Any]:
    """Launch a visible AEDT gRPC session and return its explicit PID and port."""
    return await asyncio.to_thread(
        aedt_launcher.launch,
        version=version,
        port=port,
        install_dir=install_dir or None,
        timeout=timeout,
    )


@mcp.tool()
async def check_aedt_connection(
    pid: int | None = None,
    port: int | None = None,
    timeout: float | None = None,
) -> dict[str, Any]:
    """Run a real PyAEDT health probe against one explicit PID or gRPC port."""
    return await _worker_call("ping", pid=pid, port=port, timeout=timeout)


@mcp.tool()
async def release_connection(
    pid: int | None = None,
    port: int | None = None,
    timeout: float | None = None,
) -> dict[str, Any]:
    """Attach and release one explicit AEDT target without closing it."""
    result = await _worker_call("ping", pid=pid, port=port, timeout=timeout)
    return {**result, "released": True}


@mcp.tool()
async def get_project_info(
    pid: int | None = None,
    port: int | None = None,
    timeout: float | None = None,
) -> dict[str, Any]:
    """Return project and active design metadata for one explicit AEDT target."""
    return await _worker_call("project_info", pid=pid, port=port, timeout=timeout)


@mcp.tool()
async def create_hfss_design(
    project_name: str,
    design_name: str,
    solution_type: str = "DrivenModal",
    pid: int | None = None,
    port: int | None = None,
    timeout: float | None = None,
) -> dict[str, Any]:
    """Create or activate a named HFSS design in one explicit AEDT target."""
    return await _worker_call(
        "create_hfss_design",
        pid=pid,
        port=port,
        arguments={
            "project_name": project_name,
            "design_name": design_name,
            "solution_type": solution_type,
        },
        timeout=timeout,
    )


@mcp.tool()
async def save_project(
    path: str = "",
    pid: int | None = None,
    port: int | None = None,
    timeout: float | None = None,
) -> dict[str, Any]:
    """Save the active project in one explicit AEDT target."""
    return await _worker_call(
        "save_project",
        pid=pid,
        port=port,
        arguments={"path": path},
        timeout=timeout,
    )


@mcp.tool()
async def start_analysis(
    project_name: str,
    design_name: str,
    setup_name: str,
    pid: int | None = None,
    port: int | None = None,
    blocking: bool = False,
    timeout: float | None = None,
) -> dict[str, Any]:
    """Start a named HFSS analysis; non-blocking is the default."""
    return await _worker_call(
        "start_analysis",
        pid=pid,
        port=port,
        arguments={
            "project_name": project_name,
            "design_name": design_name,
            "setup_name": setup_name,
            "blocking": blocking,
        },
        timeout=timeout,
    )


@mcp.tool()
async def get_analysis_status(
    project_name: str,
    design_name: str,
    setup_name: str = "",
    pid: int | None = None,
    port: int | None = None,
    timeout: float | None = None,
) -> dict[str, Any]:
    """Return running state and setup metadata for one explicit HFSS design."""
    return await _worker_call(
        "analysis_status",
        pid=pid,
        port=port,
        arguments={
            "project_name": project_name,
            "design_name": design_name,
            "setup_name": setup_name,
        },
        timeout=timeout,
    )


@mcp.resource("aedt://status")
def aedt_status() -> str:
    """Return discovery-only status without attaching to any AEDT process."""
    return json.dumps(
        {
            "connected": False,
            "selection_required": True,
            "sessions": session_discovery.list_sessions(),
        },
        ensure_ascii=False,
        indent=2,
    )


@mcp.resource("aedt://agent-instructions")
def agent_instructions() -> str:
    return INSTRUCTIONS


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
