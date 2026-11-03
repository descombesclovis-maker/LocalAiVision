"""A Windows EXE must never silently reuse an older process with the same version."""
import inspect
import unittest

from local_app import launcher


class LauncherBuildIdentityTests(unittest.TestCase):
    CURRENT = {"app": "LocalVisionAI", "version": "3.1.0", "build_tag": "build-310"}

    def test_same_marketing_version_but_different_build_is_not_reused(self):
        previous = {"app": "LocalVisionAI", "version": "3.1.0", "build_tag": "build-295"}
        self.assertEqual(launcher.running_instance_state(previous, self.CURRENT), "different")

    def test_missing_build_is_not_falsely_treated_as_current(self):
        previous = {"app": "LocalVisionAI", "version": "3.1.0"}
        self.assertEqual(launcher.running_instance_state(previous, self.CURRENT), "different")

    def test_identical_build_can_reuse_the_server(self):
        previous = dict(self.CURRENT)
        self.assertEqual(launcher.running_instance_state(previous, self.CURRENT), "same")

    def test_foreign_service_cannot_be_mistaken_for_localai(self):
        self.assertEqual(launcher.running_instance_state({"app": "Other", "version": "3.1.0"}, self.CURRENT), "none")
        self.assertEqual(launcher.running_instance_state(None, self.CURRENT), "none")

    def test_window_title_and_browser_fallback_advertise_active_build(self):
        source = inspect.getsource(launcher.main)
        self.assertIn('current = server.build_info()', source)
        self.assertIn('running_instance_state(existing, current)', source)
        self.assertIn('LOCALVISIONAI_BROWSER_ONLY', source)
        self.assertIn('current.get("build_tag")', source)
        self.assertIn('webview.create_window(title, URL + "/studio"', source)

    def test_windows_artifact_has_browser_launcher_and_documented_diagnostics(self):
        from pathlib import Path
        root = Path(__file__).resolve().parents[1]
        script = root / "OUVRIR_DANS_NAVIGATEUR.bat"
        self.assertTrue(script.is_file())
        data = script.read_text(encoding="utf-8")
        self.assertIn('LOCALVISIONAI_BROWSER_ONLY=1', data)
        self.assertIn('LocalVisionAI.exe', data)
        self.assertIn('startup.log', data)
        workflow = (root / ".github/workflows/build-windows.yml").read_text(encoding="utf-8")
        self.assertIn('Copy-Item OUVRIR_DANS_NAVIGATEUR.bat', workflow)
        self.assertIn("'OUVRIR_DANS_NAVIGATEUR.bat'", workflow)


if __name__ == "__main__":
    unittest.main()
