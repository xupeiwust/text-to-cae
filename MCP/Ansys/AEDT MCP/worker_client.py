from __future__ import annotations

import asyncio
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
from typing import Any

from aedt_target import AedtTarget
from worker_protocol import WorkerProtocolError, WorkerRequest, WorkerResponse


class WorkerClientError(RuntimeError):
    pass


class WorkerTimeoutError(WorkerClientError):
    pass


class WorkerProcessError(WorkerClientError):
    pass


class WorkerProtocolOutputError(WorkerClientError):
    pass


class WorkerRemoteError(WorkerClientError):
    def __init__(self, code: str, message: str, detail: Any = None) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message
        self.detail = detail


class WorkerClient:
    def __init__(
        self,
        *,
        worker_script: str | Path | None = None,
        python_executable: str | Path | None = None,
        log_dir: str | Path | None = None,
        default_timeout: float | None = None,
    ) -> None:
        self.worker_script = Path(worker_script or Path(__file__).with_name("pyaedt_worker.py"))
        self.python_executable = Path(python_executable or sys.executable)
        configured_log_dir = log_dir or os.environ.get("AEDT_LOG_DIR")
        self.log_dir = Path(configured_log_dir or Path(tempfile.gettempdir()) / "aedt-mcp")
        self.default_timeout = float(
            default_timeout
            if default_timeout is not None
            else os.environ.get("AEDT_WORKER_TIMEOUT", "60")
        )
        self._locks: dict[str, asyncio.Lock] = {}
        self._locks_guard = threading.Lock()

    def execute(
        self,
        target: AedtTarget,
        command: str,
        arguments: dict[str, Any] | None = None,
        *,
        timeout: float | None = None,
    ) -> Any:
        effective_timeout = self.default_timeout if timeout is None else timeout
        request = WorkerRequest.create(
            command,
            target,
            arguments or {},
            effective_timeout,
        )
        process = subprocess.Popen(
            [str(self.python_executable), str(self.worker_script)],
            cwd=str(self.worker_script.parent),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=self._worker_environment(),
            creationflags=self._creation_flags(),
        )
        try:
            stdout, stderr = process.communicate(
                request.to_json() + "\n",
                timeout=effective_timeout,
            )
        except subprocess.TimeoutExpired as exc:
            process.terminate()
            try:
                stdout, stderr = process.communicate(timeout=2.0)
            except subprocess.TimeoutExpired:
                process.kill()
                stdout, stderr = process.communicate()
            self._write_log(request.request_id, stderr)
            raise WorkerTimeoutError(
                f"AEDT worker timed out after {effective_timeout:g}s for {target.key}"
            ) from exc

        self._write_log(request.request_id, stderr)
        lines = [line for line in stdout.splitlines() if line.strip()]
        if len(lines) != 1:
            if process.returncode:
                raise WorkerProcessError(
                    f"AEDT worker exited with code {process.returncode} without a valid response"
                )
            raise WorkerProtocolOutputError(
                f"AEDT worker must emit exactly one JSON response line; received {len(lines)}"
            )
        try:
            response = WorkerResponse.from_json(lines[0])
        except WorkerProtocolError as exc:
            if process.returncode:
                raise WorkerProcessError(
                    f"AEDT worker exited with code {process.returncode} and invalid output"
                ) from exc
            raise WorkerProtocolOutputError(f"invalid AEDT worker response: {exc}") from exc

        if response.request_id != request.request_id:
            raise WorkerProtocolOutputError("AEDT worker response request_id does not match")
        if not response.ok:
            error = response.error or {}
            raise WorkerRemoteError(
                str(error.get("code", "worker_error")),
                str(error.get("message", "AEDT worker failed")),
                error.get("detail"),
            )
        if process.returncode:
            raise WorkerProcessError(
                f"AEDT worker exited with code {process.returncode} after a success response"
            )
        return response.result

    async def execute_async(
        self,
        target: AedtTarget,
        command: str,
        arguments: dict[str, Any] | None = None,
        *,
        timeout: float | None = None,
    ) -> Any:
        lock = self._target_lock(target.key)
        async with lock:
            return await asyncio.to_thread(
                self.execute,
                target,
                command,
                arguments,
                timeout=timeout,
            )

    def _target_lock(self, key: str) -> asyncio.Lock:
        with self._locks_guard:
            lock = self._locks.get(key)
            if lock is None:
                lock = asyncio.Lock()
                self._locks[key] = lock
            return lock

    def _worker_environment(self) -> dict[str, str]:
        environment = dict(os.environ)
        environment.pop("PYTHONINSPECT", None)
        environment.pop("PYTHONSTARTUP", None)
        environment["PYTHONUTF8"] = "1"
        return environment

    @staticmethod
    def _creation_flags() -> int:
        if os.name == "nt":
            return subprocess.CREATE_NO_WINDOW
        return 0

    def _write_log(self, request_id: str, stderr: str) -> None:
        if not stderr:
            return
        self.log_dir.mkdir(parents=True, exist_ok=True)
        (self.log_dir / f"{request_id}.log").write_text(stderr, encoding="utf-8")
