import unittest

from aedt_target import AedtTarget
from pyaedt_backend import BackendCommandError, PyAedtBackend


class FakeDesign:
    def __init__(self, name="HFSSDesign1"):
        self.name = name

    def GetName(self):
        return self.name


class FakeProject:
    def __init__(self, name="Demo", design=None):
        self.name = name
        self.design = design or FakeDesign()

    def GetName(self):
        return self.name

    def GetActiveDesign(self):
        return self.design


class FakeDesktop:
    def __init__(self, *, fail_projects=False, **kwargs):
        self.kwargs = kwargs
        self.fail_projects = fail_projects
        self.releases = []
        self.saved = []
        self.aedt_version_id = "2026.1"
        self.aedt_process_id = kwargs.get("aedt_process_id", 4321)
        self.port = kwargs.get("port", 0)
        self.project = FakeProject()

    @property
    def project_list(self):
        if self.fail_projects:
            raise RuntimeError("project lookup failed")
        return ["Demo"]

    def active_project(self, name=None):
        return self.project

    def active_design(self, project=None):
        return self.project.design

    def design_type(self, project_name=None, design_name=None):
        return "HFSS"

    def save_project(self, project_name=None, project_path=None):
        self.saved.append((project_name, project_path))
        return True

    def release_desktop(self, close_projects=False, close_on_exit=False):
        self.releases.append((close_projects, close_on_exit))
        return True


class FakeHfss:
    def __init__(self, desktop, **kwargs):
        self.desktop_class = desktop
        self.kwargs = kwargs
        self.project_name = kwargs.get("project")
        self.design_name = kwargs.get("design")
        self.solution_type = kwargs.get("solution_type")
        self.analysis_calls = []
        self.are_there_simulations_running = False

    def analyze_setup(self, name=None, blocking=True):
        self.analysis_calls.append((name, blocking))
        return True

    def get_setups(self):
        return ["Setup1"]


class PyAedtBackendTests(unittest.TestCase):
    def setUp(self):
        self.desktops = []
        self.apps = []

        def desktop_factory(**kwargs):
            desktop = FakeDesktop(**kwargs)
            self.desktops.append(desktop)
            return desktop

        def hfss_factory(**kwargs):
            desktop = FakeDesktop(**kwargs)
            app = FakeHfss(desktop, **kwargs)
            self.desktops.append(desktop)
            self.apps.append(app)
            return app

        self.backend = PyAedtBackend(
            desktop_factory=desktop_factory,
            hfss_factory=hfss_factory,
        )

    def test_pid_connection_arguments_and_release(self):
        result = self.backend.execute(AedtTarget("pid", 66276), "ping", {})

        self.assertTrue(result["connected"])
        self.assertEqual(result["target"], {"kind": "pid", "value": 66276})
        self.assertEqual(self.desktops[0].kwargs["aedt_process_id"], 66276)
        self.assertNotIn("port", self.desktops[0].kwargs)
        self.assertEqual(self.desktops[0].releases, [(False, False)])

    def test_port_connection_arguments_and_release(self):
        self.backend.execute(AedtTarget("port", 50051), "ping", {})

        kwargs = self.desktops[0].kwargs
        self.assertEqual(kwargs["machine"], "localhost")
        self.assertEqual(kwargs["port"], 50051)
        self.assertNotIn("aedt_process_id", kwargs)
        self.assertEqual(self.desktops[0].releases, [(False, False)])

    def test_project_info_is_json_compatible(self):
        result = self.backend.execute(AedtTarget("port", 50051), "project_info", {})

        self.assertEqual(result["projects"], ["Demo"])
        self.assertEqual(result["active_project"], "Demo")
        self.assertEqual(result["active_design"], "HFSSDesign1")
        self.assertEqual(result["design_type"], "HFSS")

    def test_release_runs_when_command_raises(self):
        desktop = FakeDesktop(fail_projects=True)
        backend = PyAedtBackend(desktop_factory=lambda **kwargs: desktop)

        with self.assertRaisesRegex(RuntimeError, "project lookup failed"):
            backend.execute(AedtTarget("pid", 1234), "project_info", {})

        self.assertEqual(desktop.releases, [(False, False)])

    def test_unknown_command_does_not_connect(self):
        with self.assertRaisesRegex(BackendCommandError, "unsupported command"):
            self.backend.execute(AedtTarget("pid", 1234), "unknown", {})

        self.assertEqual(self.desktops, [])

    def test_create_hfss_design_uses_explicit_names_and_solution_mapping(self):
        result = self.backend.execute(
            AedtTarget("port", 50051),
            "create_hfss_design",
            {
                "project_name": "FilterProject",
                "design_name": "FilterDesign",
                "solution_type": "DrivenModal",
            },
        )

        app = self.apps[0]
        self.assertEqual(app.kwargs["project"], "FilterProject")
        self.assertEqual(app.kwargs["design"], "FilterDesign")
        self.assertEqual(app.kwargs["solution_type"], "Modal")
        self.assertEqual(result["project_name"], "FilterProject")
        self.assertEqual(result["design_name"], "FilterDesign")
        self.assertEqual(app.desktop_class.releases, [(False, False)])

    def test_hfss_commands_reject_missing_project_or_design_before_connect(self):
        for command, arguments in (
            ("create_hfss_design", {"project_name": "P"}),
            ("start_analysis", {"project_name": "P", "design_name": "D"}),
            ("analysis_status", {"project_name": "P"}),
        ):
            with self.subTest(command=command):
                with self.assertRaises(BackendCommandError):
                    self.backend.execute(AedtTarget("pid", 1234), command, arguments)
        self.assertEqual(self.apps, [])

    def test_save_project_uses_active_project_and_optional_path(self):
        result = self.backend.execute(
            AedtTarget("pid", 1234),
            "save_project",
            {"path": "C:/temp/demo.aedt"},
        )

        self.assertTrue(result["saved"])
        self.assertEqual(self.desktops[0].saved, [("Demo", "C:/temp/demo.aedt")])

    def test_start_analysis_is_non_blocking(self):
        result = self.backend.execute(
            AedtTarget("port", 50051),
            "start_analysis",
            {
                "project_name": "Demo",
                "design_name": "HFSSDesign1",
                "setup_name": "Setup1",
                "blocking": False,
            },
        )

        self.assertTrue(result["started"])
        self.assertEqual(self.apps[0].analysis_calls, [("Setup1", False)])
        self.assertEqual(self.apps[0].desktop_class.releases, [(False, False)])

    def test_analysis_status_reports_running_state_and_setups(self):
        result = self.backend.execute(
            AedtTarget("pid", 1234),
            "analysis_status",
            {"project_name": "Demo", "design_name": "HFSSDesign1"},
        )

        self.assertFalse(result["running"])
        self.assertEqual(result["setups"], ["Setup1"])
        self.assertEqual(result["project_name"], "Demo")
        self.assertEqual(result["design_name"], "HFSSDesign1")


if __name__ == "__main__":
    unittest.main()
