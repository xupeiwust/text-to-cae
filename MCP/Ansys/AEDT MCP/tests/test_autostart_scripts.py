from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class AutostartScriptTests(unittest.TestCase):
    def _read_script(self, name: str) -> str:
        return (ROOT / "scripts" / name).read_text(encoding="utf-8")

    def test_launcher_loads_bridge_through_aedt_runscript(self):
        script = self._read_script("launch_aedt_with_mcp_bridge.ps1")

        self.assertIn("reload_bridge_in_aedt.py", script)
        self.assertIn("RunScript", script)
        self.assertIn("Ansoft.ElectronicsDesktop.2026.1", script)
        self.assertIn("GetActiveObject", script)
        self.assertIn("AllowComCreate", script)
        self.assertIn("48252", script)
        self.assertIn("aedt_socket_protocol", script)

    def test_installer_points_shortcut_at_launcher(self):
        script = self._read_script("install_aedt_mcp_autostart.ps1")

        self.assertIn("launch_aedt_with_mcp_bridge.ps1", script)
        self.assertIn("WScript.Shell", script)
        self.assertIn("Desktop", script)
        self.assertIn("Start Menu", script)

    def test_aedt_menu_entry_executes_loader(self):
        script = self._read_script("start_aedt_mcp_bridge_in_aedt.py")

        self.assertIn("reload_bridge_in_aedt.py", script)
        self.assertIn("exec(compile", script)

    def test_aedt_stop_menu_entry_executes_stopper(self):
        script = self._read_script("stop_aedt_mcp_bridge_in_aedt.py")

        self.assertIn("stop_bridge_in_aedt.py", script)
        self.assertIn("exec(compile", script)

    def test_toolkit_button_installer_targets_hfss_and_project(self):
        script = self._read_script("install_aedt_toolkit_button.ps1")

        self.assertIn("syslib\\Toolkits", script)
        self.assertIn("HFSS", script)
        self.assertIn("Project", script)
        self.assertIn("Set-ToolkitButtons", script)
        self.assertIn("Remove-XmlNodes", script)
        self.assertIn("Start AEDT MCP Bridge", script)
        self.assertIn("Stop AEDT MCP Bridge", script)
        self.assertIn("stop_bridge_in_aedt.py", script)
        self.assertIn("TabConfig.xml", script)


if __name__ == "__main__":
    unittest.main()
