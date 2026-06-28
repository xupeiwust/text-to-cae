from __future__ import annotations

from collections.abc import Callable, Mapping
import threading
from typing import Any

from aedt_target import AedtTarget


class BackendCommandError(ValueError):
    pass


_DESKTOP_COMMANDS = {"ping", "project_info", "save_project"}
_HFSS_COMMANDS = {"create_hfss_design", "start_analysis", "analysis_status"}
_SOLUTION_TYPES = {
    "DrivenModal": "Modal",
    "DrivenTerminal": "Terminal",
    "Modal": "Modal",
    "Terminal": "Terminal",
    "SBR+": "SBR+",
    "Transient": "Transient",
    "Eigenmode": "Eigenmode",
}


def _default_desktop_factory(**kwargs: Any) -> Any:
    from ansys.aedt.core import Desktop

    return Desktop(**kwargs)


def _default_hfss_factory(**kwargs: Any) -> Any:
    from ansys.aedt.core import Hfss

    return Hfss(**kwargs)


def _target_dict(target: AedtTarget) -> dict[str, Any]:
    return {"kind": target.kind, "value": target.value}


def _required_text(arguments: Mapping[str, Any], name: str) -> str:
    value = arguments.get(name)
    if not isinstance(value, str) or not value.strip():
        raise BackendCommandError(f"{name} must be a non-empty string")
    return value.strip()


def _optional_text(arguments: Mapping[str, Any], name: str, default: str = "") -> str:
    value = arguments.get(name, default)
    if not isinstance(value, str):
        raise BackendCommandError(f"{name} must be a string")
    return value.strip()


def _read_value(obj: Any, name: str, *args: Any) -> Any:
    value = getattr(obj, name)
    return value(*args) if callable(value) else value


def _object_name(obj: Any) -> str | None:
    if obj is None:
        return None
    get_name = getattr(obj, "GetName", None)
    if callable(get_name):
        return str(get_name())
    name = getattr(obj, "name", None)
    return str(name) if name is not None else None


def _release(handle: Any) -> bool:
    desktop = getattr(handle, "desktop_class", handle)
    return bool(desktop.release_desktop(close_projects=False, close_on_exit=False))


def _active_design(desktop: Any, project: Any) -> Any:
    if project is None:
        return None
    project_name = _object_name(project)
    try:
        designs = list(_read_value(desktop, "design_list", project_name))
    except AttributeError:
        designs = None
    if designs == []:
        return None
    return desktop.active_design(project)


class PyAedtBackend:
    def __init__(
        self,
        *,
        desktop_factory: Callable[..., Any] | None = None,
        hfss_factory: Callable[..., Any] | None = None,
        version: str = "2026.1",
    ) -> None:
        self._desktop_factory = desktop_factory or _default_desktop_factory
        self._hfss_factory = hfss_factory or _default_hfss_factory
        self._version = version
        self._desktop: Any = None
        self._bound_target: AedtTarget | None = None
        self._apps: dict[tuple[str, str, str | None], Any] = {}
        self._lock = threading.RLock()

    def execute(
        self,
        target: AedtTarget,
        command: str,
        arguments: Mapping[str, Any] | None,
    ) -> dict[str, Any]:
        with self._lock:
            return self._execute(target, command, arguments)

    def _execute(
        self,
        target: AedtTarget,
        command: str,
        arguments: Mapping[str, Any] | None,
    ) -> dict[str, Any]:
        if command not in _DESKTOP_COMMANDS | _HFSS_COMMANDS:
            raise BackendCommandError(f"unsupported command: {command}")
        if arguments is None:
            arguments = {}
        if not isinstance(arguments, Mapping):
            raise BackendCommandError("arguments must be an object")

        if command in _DESKTOP_COMMANDS:
            return self._execute_desktop(target, command, arguments)
        return self._execute_hfss(target, command, arguments)

    def release(self) -> bool:
        with self._lock:
            if self._desktop is None:
                return False
            desktop = self._desktop
            self._apps.clear()
            self._desktop = None
            self._bound_target = None
            return _release(desktop)

    @property
    def session_pid(self) -> int | None:
        with self._lock:
            if self._desktop is None:
                return None
            pid = getattr(self._desktop, "aedt_process_id", None)
            return pid if type(pid) is int and pid > 0 else None

    def close_for_user_request(self) -> bool:
        with self._lock:
            if self._desktop is None:
                return False
            desktop = self._desktop
            self._apps.clear()
            self._desktop = None
            self._bound_target = None
            desktop.odesktop.QuitApplication()
            return True

    def _desktop_for(self, target: AedtTarget) -> Any:
        if self._desktop is None:
            self._desktop = self._desktop_factory(**self._connection_kwargs(target))
            self._bound_target = target
            return self._desktop

        if not self._target_matches(target):
            raise BackendCommandError(
                f"broker is bound to {self._bound_target.key}; requested {target.key}"
            )
        return self._desktop

    def _target_matches(self, target: AedtTarget) -> bool:
        if target == self._bound_target:
            return True
        if target.kind == "pid":
            return getattr(self._desktop, "aedt_process_id", None) == target.value
        return getattr(self._desktop, "port", None) == target.value

    def _connection_kwargs(self, target: AedtTarget) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "version": self._version,
            "non_graphical": False,
            "new_desktop": False,
            "close_on_exit": False,
        }
        if target.kind == "pid":
            kwargs["aedt_process_id"] = target.value
        else:
            kwargs.update({"machine": "localhost", "port": target.value})
        return kwargs

    def _execute_desktop(
        self,
        target: AedtTarget,
        command: str,
        arguments: Mapping[str, Any],
    ) -> dict[str, Any]:
        desktop = self._desktop_for(target)
        if command == "ping":
            return self._ping(desktop, target)
        if command == "project_info":
            return self._project_info(desktop, target)
        return self._save_project(desktop, target, arguments)

    def _execute_hfss(
        self,
        target: AedtTarget,
        command: str,
        arguments: Mapping[str, Any],
    ) -> dict[str, Any]:
        project_name = _required_text(arguments, "project_name")
        design_name = _required_text(arguments, "design_name")
        self._desktop_for(target)
        kwargs = self._connection_kwargs(self._bound_target or target)
        kwargs.update({"project": project_name, "design": design_name})

        if command == "create_hfss_design":
            requested = _optional_text(arguments, "solution_type", "DrivenModal")
            try:
                kwargs["solution_type"] = _SOLUTION_TYPES[requested]
            except KeyError as exc:
                raise BackendCommandError(f"unsupported HFSS solution_type: {requested}") from exc
        elif command == "start_analysis":
            kwargs["setup"] = _required_text(arguments, "setup_name")

        app_key = (project_name, design_name, kwargs.get("solution_type"))
        app = self._apps.get(app_key)
        if app is None:
            app = self._hfss_factory(**kwargs)
            self._apps[app_key] = app
        if command == "create_hfss_design":
            return {
                "target": _target_dict(target),
                "project_name": str(getattr(app, "project_name", project_name)),
                "design_name": str(getattr(app, "design_name", design_name)),
                "solution_type": str(getattr(app, "solution_type", kwargs["solution_type"])),
            }
        if command == "start_analysis":
            blocking = arguments.get("blocking", False)
            if not isinstance(blocking, bool):
                raise BackendCommandError("blocking must be a boolean")
            setup_name = kwargs["setup"]
            started = bool(app.analyze_setup(name=setup_name, blocking=blocking))
            return {
                "target": _target_dict(target),
                "project_name": project_name,
                "design_name": design_name,
                "setup_name": setup_name,
                "blocking": blocking,
                "started": started,
            }

        running = bool(_read_value(app, "are_there_simulations_running"))
        setups = list(app.get_setups())
        return {
            "target": _target_dict(target),
            "project_name": project_name,
            "design_name": design_name,
            "running": running,
            "setups": [str(item) for item in setups],
        }

    def _ping(self, desktop: Any, target: AedtTarget) -> dict[str, Any]:
        project = desktop.active_project()
        design = _active_design(desktop, project)
        return {
            "connected": True,
            "target": _target_dict(target),
            "aedt_version": str(getattr(desktop, "aedt_version_id", self._version)),
            "pid": getattr(desktop, "aedt_process_id", None),
            "port": getattr(desktop, "port", None),
            "active_project": _object_name(project),
            "active_design": _object_name(design),
        }

    def _project_info(self, desktop: Any, target: AedtTarget) -> dict[str, Any]:
        projects = list(_read_value(desktop, "project_list"))
        project = desktop.active_project()
        design = _active_design(desktop, project)
        project_name = _object_name(project)
        design_name = _object_name(design)
        design_type = None
        if project_name and design_name:
            design_type = desktop.design_type(project_name, design_name)
        return {
            "target": _target_dict(target),
            "projects": [str(item) for item in projects],
            "active_project": project_name,
            "active_design": design_name,
            "design_type": str(design_type) if design_type is not None else None,
        }

    def _save_project(
        self,
        desktop: Any,
        target: AedtTarget,
        arguments: Mapping[str, Any],
    ) -> dict[str, Any]:
        project = desktop.active_project()
        project_name = _object_name(project)
        if not project_name:
            raise BackendCommandError("AEDT has no active project to save")
        path = _optional_text(arguments, "path")
        saved = bool(desktop.save_project(project_name, path or None))
        return {
            "target": _target_dict(target),
            "project_name": project_name,
            "path": path or None,
            "saved": saved,
        }
