from __future__ import annotations

from dotenv import load_dotenv
from fastmcp import FastMCP

from tools.workbench_bridge import (
    detect_workbench_environment,
    get_workbench_job_status,
    launch_mechanical_script,
    launch_workbench_journal,
    list_workbench_jobs,
    read_workbench_job_log,
)
from tools.workbench_file_queue import (
    list_queue as queue_list,
    queue_execute_python,
    queue_get_state,
    queue_install_info,
    queue_ping,
    read_response as queue_read_response,
    submit_request as queue_submit_request,
    trigger_socket_process_queue,
)
from tools.workbench_socket_timer import (
    socket_timer_execute_python,
    socket_timer_ping,
    socket_timer_state,
    socket_timer_stop,
)


load_dotenv()

mcp = FastMCP("Ansys Workbench MCP")


@mcp.tool()
def workbench_detect_tool() -> dict:
    """Detect RunWB2.exe, PyMechanical CLI, ANSYS_ROOT, and job directories."""
    return detect_workbench_environment()


@mcp.tool()
def workbench_run_journal_tool(
    journal_path: str,
    cwd: str | None = None,
    batch: bool = True,
    extra_args: list[str] | None = None,
) -> dict:
    """Launch a Workbench journal asynchronously."""
    return launch_workbench_journal(journal_path=journal_path, cwd=cwd, batch=batch, extra_args=extra_args)


@mcp.tool()
def mechanical_run_script_tool(
    script_path: str,
    revision: int = 261,
    graphical: bool = False,
    project_file: str | None = None,
    script_args: str | None = None,
) -> dict:
    """Launch ansys-mechanical.exe for a Mechanical Python script."""
    return launch_mechanical_script(
        script_path=script_path,
        revision=revision,
        graphical=graphical,
        project_file=project_file,
        script_args=script_args,
    )


@mcp.tool()
def workbench_job_status_tool(job_id: str) -> dict:
    """Return status for a Workbench or Mechanical job launched by this MCP."""
    return get_workbench_job_status(job_id)


@mcp.tool()
def workbench_job_log_tool(job_id: str, stream: str = "stdout", tail_chars: int = 12000) -> dict:
    """Read stdout or stderr for a Workbench or Mechanical job."""
    return read_workbench_job_log(job_id=job_id, stream=stream, tail_chars=tail_chars)


@mcp.tool()
def workbench_list_jobs_tool(limit: int = 20) -> dict:
    """List recent Workbench or Mechanical jobs."""
    return list_workbench_jobs(limit=limit)


@mcp.tool()
def workbench_queue_install_info_tool() -> dict:
    """Show paths and instructions for the Mechanical file queue bridge."""
    return queue_install_info()


@mcp.tool()
def workbench_queue_list_tool() -> dict:
    """List pending queue requests, responses, and recent archive entries."""
    return queue_list()


@mcp.tool()
def workbench_queue_submit_tool(action: str, payload: dict | None = None) -> dict:
    """Submit a raw request to the Mechanical file queue."""
    return queue_submit_request(action=action, payload=payload)


@mcp.tool()
def workbench_queue_response_tool(request_id: str) -> dict:
    """Read a queued Mechanical response by request id."""
    return queue_read_response(request_id)


@mcp.tool()
def workbench_queue_ping_tool(wait_timeout: float = 2.0) -> dict:
    """Submit a queue ping and wait briefly for the Mechanical-side response."""
    return queue_ping(wait_timeout=wait_timeout)


@mcp.tool()
def workbench_queue_state_tool(wait_timeout: float = 2.0) -> dict:
    """Read project state through the Mechanical queue bridge."""
    return queue_get_state(wait_timeout=wait_timeout)


@mcp.tool()
def workbench_queue_execute_python_tool(code: str, wait_timeout: float = 2.0) -> dict:
    """Execute Python inside Mechanical through the queue bridge."""
    return queue_execute_python(code=code, wait_timeout=wait_timeout)


@mcp.tool()
def workbench_queue_process_with_socket_timer_tool(timeout: float = 2.0) -> dict:
    """Ask the socket timer bridge to process pending queue requests."""
    return trigger_socket_process_queue(timeout=timeout)


@mcp.tool()
def workbench_socket_timer_ping_tool(timeout: float = 10.0) -> dict:
    """Ping the Mechanical socket timer bridge."""
    return socket_timer_ping(timeout=timeout)


@mcp.tool()
def workbench_socket_timer_state_tool(timeout: float = 10.0) -> dict:
    """Read state from the Mechanical socket timer bridge."""
    return socket_timer_state(timeout=timeout)


@mcp.tool()
def workbench_socket_timer_execute_python_tool(code: str, timeout: float = 60.0) -> dict:
    """Execute Python inside Mechanical through the socket timer bridge."""
    return socket_timer_execute_python(code=code, timeout=timeout)


@mcp.tool()
def workbench_socket_timer_stop_tool(timeout: float = 10.0) -> dict:
    """Stop the Mechanical socket timer bridge."""
    return socket_timer_stop(timeout=timeout)


if __name__ == "__main__":
    mcp.run()
