# -*- coding: utf-8 -*-
"""
AEDT MCP Bridge - raw TCP JSON bridge for Ansys Electronics Desktop.

Run this file inside Ansys Electronics Desktop 2026 R1 through Tools > Run
Script or the script editor. It starts a localhost socket bridge used by the
external MCP server.
"""

from __future__ import print_function

import json
import os
import platform
import socket
try:
    import socketserver
except ImportError:  # pragma: no cover
    import SocketServer as socketserver
import sys
import tempfile
import threading
import time
import traceback

try:
    from StringIO import StringIO
except ImportError:  # pragma: no cover
    from io import StringIO


__version__ = "0.1.0"

HOST = os.environ.get("AEDT_MCP_HOST", "127.0.0.1")
PORT = int(os.environ.get("AEDT_MCP_PORT", "48252"))
TOKEN = os.environ.get("AEDT_MCP_TOKEN", "")
DEFAULT_TIMEOUT = float(os.environ.get("AEDT_MCP_TIMEOUT", "60"))
MAX_MESSAGE_BYTES = int(os.environ.get("AEDT_MCP_MAX_MESSAGE_BYTES", str(32 * 1024 * 1024)))
LOG_PATH = os.environ.get("AEDT_MCP_LOG", os.path.join(tempfile.gettempdir(), "aedt_mcp_socket_bridge.log"))

_SERVER = None
_SERVER_THREAD = None
_START_TIME = None
_PROCESSED = 0
_NAMESPACE = {"__name__": "__aedt_mcp_exec__", "__doc__": None}
_NAMESPACE_BASE_KEYS = set(_NAMESPACE.keys())


def _log(message):
    try:
        with open(LOG_PATH, "a") as handle:
            handle.write("%s %s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), message))
    except Exception:
        pass


def _send(sock, payload):
    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n"
    try:
        sock.sendall(data)
    except TypeError:
        sock.sendall(data.encode("utf-8"))


def _chunk_to_text(chunk):
    try:
        return chunk.decode("utf-8")
    except Exception:
        pass
    try:
        return "".join(chr(item) for item in bytearray(chunk))
    except Exception:
        pass
    return str(chunk)


def _recv(sock):
    chunks = []
    total = 0
    while True:
        chunk = sock.recv(4096)
        if not chunk:
            raise RuntimeError("socket closed before a complete message was received")
        chunk = _chunk_to_text(chunk)
        newline = chunk.find("\n")
        if newline >= 0:
            chunks.append(chunk[:newline])
            break
        chunks.append(chunk)
        total += len(chunk)
        if total > MAX_MESSAGE_BYTES:
            raise RuntimeError("message exceeded %d bytes" % MAX_MESSAGE_BYTES)
    message = json.loads("".join(chunks))
    if not isinstance(message, dict):
        raise RuntimeError("protocol message must be a JSON object")
    return message


def _ensure_script_env_path():
    if "ScriptEnv" in sys.modules:
        return
    roots = []
    for key, value in os.environ.items():
        if key.startswith("ANSYSEM_ROOT") and value:
            roots.append(value)
    for root in roots:
        candidate = os.path.join(root, "PythonFiles", "DesktopPlugin")
        if os.path.isdir(candidate) and candidate not in sys.path:
            sys.path.insert(0, candidate)


def _desktop():
    desktop = globals().get("oDesktop")
    if desktop is not None:
        try:
            desktop.GetProjectList()
            return desktop
        except Exception:
            pass

    root = os.environ.get("ANSYSEM_ROOT261", r"G:\ANSYS206\ANSYS Inc\v261\AnsysEM")
    if root and root not in sys.path:
        sys.path.insert(0, root)
    import clr

    clr.AddReference("Ansys.Ansoft.CoreCOMScripting")
    import Ansys.Ansoft.CoreCOMScripting as CoreCOMScripting

    app = CoreCOMScripting.COM.StandalonePyScriptWrapper.CreateObject("Ansoft.ElectronicsDesktop.2026.1")
    desktop = app.GetAppDesktop()
    globals()["oDesktop"] = desktop
    globals()["oAnsoftApplication"] = app
    return desktop


def _name(obj):
    if obj is None:
        return None
    try:
        return obj.GetName()
    except Exception:
        return None


def _active_project():
    try:
        return _desktop().GetActiveProject()
    except Exception:
        return None


def _active_design():
    project = _active_project()
    if project is None:
        return None
    try:
        return project.GetActiveDesign()
    except Exception:
        return None


def _project_names():
    try:
        return list(_desktop().GetProjectList())
    except Exception:
        return []


def _design_names(project):
    if project is None:
        return []
    for method_name in ("GetTopDesignList", "GetDesignList"):
        try:
            return list(getattr(project, method_name)())
        except Exception:
            pass
    return []


def _jsonable(value):
    try:
        json.dumps(value, ensure_ascii=False)
        return value
    except Exception:
        return {"repr": repr(value), "type": "%s.%s" % (type(value).__module__, type(value).__name__)}


def _execute(code):
    namespace = _NAMESPACE
    desktop = _desktop()
    project = _active_project()
    design = _active_design()
    namespace.update(
        {
            "oDesktop": desktop,
            "oProject": project,
            "oDesign": design,
            "os": os,
            "sys": sys,
            "json": json,
        }
    )

    stdout = StringIO()
    stderr = StringIO()
    returned = None
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    try:
        sys.stdout = stdout
        sys.stderr = stderr
        exec(compile(code, "<aedt-mcp>", "exec"), namespace, namespace)
        returned = namespace.get("result")
    except Exception:
        return {
            "ok": False,
            "stdout": stdout.getvalue(),
            "stderr": stderr.getvalue(),
            "traceback": traceback.format_exc(),
        }
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr
    return {"ok": True, "return_value": _jsonable(returned), "stdout": stdout.getvalue(), "stderr": stderr.getvalue()}


def _ping():
    desktop = _desktop()
    project = _active_project()
    design = _active_design()
    version = None
    pid = None
    try:
        version = desktop.GetVersion()
    except Exception:
        pass
    try:
        pid = desktop.GetProcessID()
    except Exception:
        pass
    return {
        "aedt_version": version,
        "pid": pid,
        "projects": _project_names(),
        "active_project": _name(project),
        "active_design": _name(design),
        "cwd": os.getcwd(),
        "python": sys.version,
        "platform": platform.platform(),
        "bridge": {
            "version": __version__,
            "host": HOST,
            "port": PORT,
            "transport": "raw-tcp-json",
            "processed": _PROCESSED,
            "uptime_seconds": int(time.time() - _START_TIME) if _START_TIME else 0,
            "log": LOG_PATH,
        },
    }


def _project_info():
    project = _active_project()
    design = _active_design()
    design_type = None
    if design is not None:
        try:
            design_type = design.GetDesignType()
        except Exception:
            pass
    return {
        "projects": _project_names(),
        "active_project": _name(project),
        "active_design": _name(design),
        "active_design_type": design_type,
        "designs": _design_names(project),
    }


def _create_hfss_design(params):
    desktop = _desktop()
    project_name = params.get("project_name") or "codex_aedt_project"
    design_name = params.get("design_name") or "CodexHFSSDesign"
    solution_type = params.get("solution_type") or "DrivenModal"

    if project_name in _project_names():
        desktop.SetActiveProject(project_name)
        project = desktop.GetActiveProject()
    else:
        project = desktop.NewProject(project_name)

    designs = _design_names(project)
    if design_name in designs:
        project.SetActiveDesign(design_name)
    else:
        project.InsertDesign("HFSS", design_name, solution_type, "")
        project.SetActiveDesign(design_name)

    return _project_info()


def _save_project(params):
    project = _active_project()
    if project is None:
        raise RuntimeError("No active AEDT project to save")
    path = (params.get("path") or "").strip()
    if path:
        project.SaveAs(path, True)
    else:
        project.Save()
    return {"success": True, "path": path, "active_project": _name(project)}


def _handle(method, params):
    if TOKEN and params.get("token") != TOKEN:
        raise RuntimeError("invalid AEDT MCP token")
    if method == "ping":
        return _ping()
    if method == "execute":
        code = params.get("code")
        if not isinstance(code, str) or not code.strip():
            raise ValueError("params.code must be a non-empty string")
        return _execute(code)
    if method == "project_info":
        return _project_info()
    if method == "create_hfss_design":
        return _create_hfss_design(params)
    if method == "save_project":
        return _save_project(params)
    if method == "stop":
        threading.Thread(target=stop_bridge, name="AedtMcpStopper").start()
        return {"success": True, "message": "stop requested"}
    raise ValueError("unknown method: %r" % method)


class AedtBridgeHandler(socketserver.BaseRequestHandler):
    def handle(self):
        global _PROCESSED
        request_id = None
        try:
            message = _recv(self.request)
            request_id = message.get("id")
            method = message.get("method")
            params = message.get("params") or {}
            _log("request method=%s id=%s" % (method, request_id))
            result = _handle(method, params)
            _PROCESSED += 1
            _send(self.request, {"id": request_id, "ok": True, "result": result})
        except Exception as exc:
            _log("response error id=%s error=%s" % (request_id, exc))
            _send(
                self.request,
                {
                    "id": request_id,
                    "ok": False,
                    "error": {
                        "message": str(exc),
                        "type": "%s.%s" % (type(exc).__module__, type(exc).__name__),
                        "traceback": traceback.format_exc(),
                    },
                },
            )


class AedtBridgeServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True


def start_bridge():
    global _SERVER, _SERVER_THREAD, _START_TIME
    if _SERVER is not None:
        return "AEDT MCP bridge is already running on %s:%s" % (HOST, PORT)
    _desktop()
    _SERVER = AedtBridgeServer((HOST, PORT), AedtBridgeHandler)
    _SERVER_THREAD = threading.Thread(target=_SERVER.serve_forever, name="AedtMcpSocketBridge")
    # Do not let the background listener keep AEDT alive if the user closes AEDT
    # before pressing the Stop toolbar button.
    _SERVER_THREAD.daemon = True
    _SERVER_THREAD.start()
    _START_TIME = time.time()
    message = "AEDT MCP bridge listening on %s:%s" % (HOST, PORT)
    _log(message)
    print(message)
    print("AEDT MCP log: %s" % LOG_PATH)
    return message


def _clear_execution_namespace():
    """Release COM references captured by executed MCP scripts."""
    for key in list(_NAMESPACE.keys()):
        if key not in _NAMESPACE_BASE_KEYS:
            try:
                del _NAMESPACE[key]
            except Exception:
                pass


def stop_bridge():
    global _SERVER, _SERVER_THREAD, _START_TIME
    server = _SERVER
    if server is None:
        _clear_execution_namespace()
        globals()["_AEDT_MCP_BRIDGE_STARTED"] = False
        return "AEDT MCP bridge is not running"
    thread = _SERVER_THREAD
    try:
        server.shutdown()
        server.server_close()
    finally:
        _SERVER = None
        _SERVER_THREAD = None
        _START_TIME = None
        _clear_execution_namespace()
        globals()["_AEDT_MCP_BRIDGE_STARTED"] = False
    if thread is not None and thread is not threading.current_thread():
        try:
            thread.join(2.0)
        except Exception:
            pass
    _log("stopped bridge")
    return "AEDT MCP bridge stopped"


if not globals().get("_AEDT_MCP_BRIDGE_STARTED"):
    start_bridge()
    globals()["_AEDT_MCP_BRIDGE_STARTED"] = True
