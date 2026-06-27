import asyncio
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest

from aedt_target import AedtTarget
from pyaedt_worker import run_request_line
from worker_client import (
    WorkerClient,
    WorkerProcessError,
    WorkerProtocolOutputError,
    WorkerRemoteError,
    WorkerTimeoutError,
)
from worker_protocol import WorkerRequest, WorkerResponse


class FakeBackend:
    def __init__(self, result=None, error=None):
        self.result = result or {"connected": True}
        self.error = error
        self.calls = []

    def execute(self, target, command, arguments):
        self.calls.append((target, command, arguments))
        if self.error:
            raise self.error
        return self.result


class WorkerEntryPointTests(unittest.TestCase):
    def test_valid_request_returns_success(self):
        request = WorkerRequest.create(
            "ping", AedtTarget("port", 50051), {}, 5.0
        )
        backend = FakeBackend({"connected": True, "label": "测试"})

        response, exit_code = run_request_line(
            request.to_json(), backend_factory=lambda: backend
        )

        self.assertEqual(exit_code, 0)
        self.assertEqual(response.request_id, request.request_id)
        self.assertEqual(response.result["label"], "测试")
        self.assertEqual(backend.calls[0][1], "ping")

    def test_invalid_request_returns_protocol_error(self):
        response, exit_code = run_request_line("not-json", backend_factory=FakeBackend)

        self.assertEqual(exit_code, 2)
        self.assertFalse(response.ok)
        self.assertEqual(response.error["code"], "invalid_request")

    def test_backend_failure_returns_stable_error(self):
        request = WorkerRequest.create(
            "ping", AedtTarget("pid", 1234), {}, 5.0
        )
        backend = FakeBackend(error=RuntimeError("AEDT unavailable"))

        response, exit_code = run_request_line(
            request.to_json(), backend_factory=lambda: backend
        )

        self.assertEqual(exit_code, 1)
        self.assertEqual(response.request_id, request.request_id)
        self.assertEqual(response.error["code"], "backend_error")
        self.assertIn("AEDT unavailable", response.error["message"])


class WorkerClientTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def _script(self, name, source):
        path = self.root / name
        path.write_text(source, encoding="utf-8")
        return path

    def _client(self, script, timeout=2.0):
        return WorkerClient(
            worker_script=script,
            python_executable=sys.executable,
            log_dir=self.root / "logs",
            default_timeout=timeout,
        )

    def test_valid_subprocess_response_and_stderr_log(self):
        script = self._script(
            "valid_worker.py",
            """import json, sys
request = json.loads(sys.stdin.read())
sys.stderr.write("worker diagnostic\\n")
print(json.dumps({"request_id": request["request_id"], "ok": True, "result": {"pid": 7}, "error": None}))
""",
        )

        result = self._client(script).execute(
            AedtTarget("pid", 7), "ping", {}, timeout=1.0
        )

        self.assertEqual(result, {"pid": 7})
        logs = list((self.root / "logs").glob("*.log"))
        self.assertEqual(len(logs), 1)
        self.assertIn("worker diagnostic", logs[0].read_text(encoding="utf-8"))

    def test_timeout_terminates_only_worker(self):
        script = self._script(
            "sleep_worker.py",
            "import time, sys\nsys.stdin.read()\ntime.sleep(30)\n",
        )
        client = self._client(script, timeout=0.1)

        started = time.monotonic()
        with self.assertRaises(WorkerTimeoutError):
            client.execute(AedtTarget("pid", 7), "ping", {}, timeout=0.1)

        self.assertLess(time.monotonic() - started, 5.0)

    def test_invalid_stdout_is_rejected(self):
        script = self._script(
            "invalid_worker.py",
            "import sys\nsys.stdin.read()\nprint('not-json')\n",
        )

        with self.assertRaises(WorkerProtocolOutputError):
            self._client(script).execute(AedtTarget("pid", 7), "ping", {})

    def test_multiple_stdout_lines_are_rejected(self):
        script = self._script(
            "two_lines.py",
            "import sys\nsys.stdin.read()\nprint('{}')\nprint('{}')\n",
        )

        with self.assertRaisesRegex(WorkerProtocolOutputError, "exactly one"):
            self._client(script).execute(AedtTarget("pid", 7), "ping", {})

    def test_nonzero_without_valid_response_is_process_error(self):
        script = self._script(
            "failed_worker.py",
            "import sys\nsys.stdin.read()\nsys.stderr.write('failed')\nraise SystemExit(3)\n",
        )

        with self.assertRaises(WorkerProcessError):
            self._client(script).execute(AedtTarget("pid", 7), "ping", {})

    def test_remote_error_preserves_code_and_detail(self):
        script = self._script(
            "remote_error.py",
            """import json, sys
request = json.loads(sys.stdin.read())
print(json.dumps({"request_id": request["request_id"], "ok": False, "result": None, "error": {"code": "session_not_found", "message": "missing", "detail": {"pid": 7}}}))
raise SystemExit(1)
""",
        )

        with self.assertRaises(WorkerRemoteError) as caught:
            self._client(script).execute(AedtTarget("pid", 7), "ping", {})

        self.assertEqual(caught.exception.code, "session_not_found")
        self.assertEqual(caught.exception.detail, {"pid": 7})

    def test_mismatched_request_id_is_rejected(self):
        script = self._script(
            "wrong_id.py",
            "import sys\nsys.stdin.read()\nprint('{\"request_id\":\"wrong\",\"ok\":true,\"result\":{},\"error\":null}')\n",
        )

        with self.assertRaisesRegex(WorkerProtocolOutputError, "request_id"):
            self._client(script).execute(AedtTarget("pid", 7), "ping", {})


class WorkerLockTests(unittest.IsolatedAsyncioTestCase):
    async def test_same_target_is_serialized_and_distinct_targets_overlap(self):
        client = WorkerClient(worker_script=Path("unused.py"))
        active = 0
        max_by_pair = {"same": 0, "different": 0}

        def slow_execute(target, command, arguments, timeout=None):
            nonlocal active
            active += 1
            bucket = arguments["bucket"]
            max_by_pair[bucket] = max(max_by_pair[bucket], active)
            time.sleep(0.05)
            active -= 1
            return {"target": target.key}

        client.execute = slow_execute

        same = AedtTarget("pid", 1)
        await asyncio.gather(
            client.execute_async(same, "ping", {"bucket": "same"}),
            client.execute_async(same, "ping", {"bucket": "same"}),
        )
        self.assertEqual(max_by_pair["same"], 1)

        await asyncio.gather(
            client.execute_async(AedtTarget("pid", 2), "ping", {"bucket": "different"}),
            client.execute_async(AedtTarget("pid", 3), "ping", {"bucket": "different"}),
        )
        self.assertGreaterEqual(max_by_pair["different"], 2)


if __name__ == "__main__":
    unittest.main()
