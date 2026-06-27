from __future__ import annotations

import contextlib
import sys
from typing import Any, Callable

from pyaedt_backend import BackendCommandError, PyAedtBackend
from worker_protocol import WorkerProtocolError, WorkerRequest, WorkerResponse


def run_request_line(
    payload: str,
    *,
    backend_factory: Callable[[], Any] = PyAedtBackend,
) -> tuple[WorkerResponse, int]:
    request_id = "unknown"
    try:
        request = WorkerRequest.from_json(payload.strip())
        request_id = request.request_id
    except WorkerProtocolError as exc:
        return WorkerResponse.failure(request_id, "invalid_request", str(exc)), 2

    try:
        backend = backend_factory()
        result = backend.execute(request.target, request.command, request.arguments)
        return WorkerResponse.success(request.request_id, result), 0
    except BackendCommandError as exc:
        return WorkerResponse.failure(request.request_id, "invalid_command", str(exc)), 1
    except Exception as exc:
        return WorkerResponse.failure(request.request_id, "backend_error", str(exc)), 1


def main() -> int:
    payload = sys.stdin.read()
    with contextlib.redirect_stdout(sys.stderr):
        response, exit_code = run_request_line(payload)
    sys.stdout.write(response.to_json() + "\n")
    sys.stdout.flush()
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
