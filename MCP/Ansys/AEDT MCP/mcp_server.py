#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import json
import os
from typing import Any

from mcp.server.fastmcp import FastMCP

from aedt_socket_protocol import request


DEFAULT_HOST = os.environ.get("AEDT_MCP_HOST", "127.0.0.1")
DEFAULT_PORT = int(os.environ.get("AEDT_MCP_PORT", "48252"))
DEFAULT_TIMEOUT = float(os.environ.get("AEDT_MCP_TIMEOUT", "60"))
MAX_MESSAGE_BYTES = int(os.environ.get("AEDT_MCP_MAX_MESSAGE_BYTES", str(32 * 1024 * 1024)))
TOKEN = os.environ.get("AEDT_MCP_TOKEN", "")

INSTRUCTIONS = """You are controlling a live Ansys Electronics Desktop session through MCP.

Prefer small validated script chunks. Inspect the active project and design before
changing state. For HFSS workflows, create named variables, designs, setups, and
reports so later automation can find and modify them reliably.
"""

mcp = FastMCP("ansys-aedt-mcp-server", instructions=INSTRUCTIONS)


def _with_token(params: dict[str, Any] | None = None) -> dict[str, Any]:
    merged = dict(params or {})
    if TOKEN:
        merged["token"] = TOKEN
    return merged


async def _bridge_request(method: str, params: dict[str, Any] | None = None, timeout: float | None = None) -> dict[str, Any]:
    effective_timeout = timeout if timeout is not None else DEFAULT_TIMEOUT
    try:
        return await asyncio.to_thread(
            request,
            DEFAULT_HOST,
            DEFAULT_PORT,
            method,
            _with_token(params),
            effective_timeout,
            MAX_MESSAGE_BYTES,
        )
    except ConnectionRefusedError as exc:
        raise RuntimeError(
            "Cannot connect to the AEDT socket bridge. Open Ansys Electronics Desktop, "
            "run aedt_mcp_bridge.py inside AEDT, and verify the bridge endpoint "
            f"{DEFAULT_HOST}:{DEFAULT_PORT}. Original error: {exc}"
        ) from exc
    except TimeoutError as exc:
        raise RuntimeError(
            "Timed out waiting for the AEDT socket bridge. AEDT may be busy or the "
            f"bridge may need to be restarted. Original error: {exc}"
        ) from exc


def _json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


@mcp.tool()
async def ping(timeout: float | None = None) -> dict[str, Any]:
    """Check whether the AEDT-side socket bridge is reachable."""
    return await _bridge_request("ping", timeout=timeout or 10.0)


@mcp.tool()
async def check_aedt_connection(timeout: float | None = None) -> str:
    """Return a concise human-readable AEDT bridge status."""
    info = await ping(timeout=timeout or 10.0)
    return (
        f"Connected to AEDT socket bridge at {DEFAULT_HOST}:{DEFAULT_PORT}.\n"
        f"AEDT version: {info.get('aedt_version', 'unknown')}\n"
        f"PID: {info.get('pid', 'unknown')}\n"
        f"Active project: {info.get('active_project') or '(none)'}\n"
        f"Active design: {info.get('active_design') or '(none)'}"
    )


@mcp.tool()
async def run_script(code: str, timeout: float | None = None) -> dict[str, Any]:
    """Execute Python code inside the live AEDT bridge namespace.

    Assign a variable named ``result`` to return structured data.
    """
    if not code.strip():
        raise ValueError("code must not be empty")
    result = await _bridge_request("execute", {"code": code}, timeout=timeout)
    if not result.get("ok", False):
        raise RuntimeError(_json(result))
    return result


@mcp.tool()
async def get_project_info(timeout: float | None = None) -> str:
    """Inspect active AEDT project and design metadata."""
    return _json(await _bridge_request("project_info", timeout=timeout or 20.0))


@mcp.tool()
async def create_hfss_design(project_name: str, design_name: str, solution_type: str = "DrivenModal", timeout: float | None = None) -> dict[str, Any]:
    """Create or activate an HFSS design in AEDT."""
    if not project_name.strip():
        raise ValueError("project_name must not be empty")
    if not design_name.strip():
        raise ValueError("design_name must not be empty")
    return await _bridge_request(
        "create_hfss_design",
        {
            "project_name": project_name.strip(),
            "design_name": design_name.strip(),
            "solution_type": solution_type.strip() or "DrivenModal",
        },
        timeout=timeout or 60.0,
    )


@mcp.tool()
async def save_project(path: str = "", timeout: float | None = None) -> dict[str, Any]:
    """Save the active AEDT project, optionally to a specific path."""
    return await _bridge_request("save_project", {"path": path.strip()}, timeout=timeout or 60.0)


@mcp.resource("aedt://status")
def aedt_status() -> str:
    """Live AEDT bridge status resource."""
    try:
        return _json(request(DEFAULT_HOST, DEFAULT_PORT, "ping", _with_token({}), timeout=5.0))
    except Exception as exc:
        return _json({"connected": False, "endpoint": f"{DEFAULT_HOST}:{DEFAULT_PORT}", "error": str(exc)})


@mcp.resource("aedt://agent-instructions")
def agent_instructions() -> str:
    """AEDT automation instructions for MCP clients."""
    return INSTRUCTIONS


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
