"""Mobile Safari should load the real LocalAiWeb client, not the desktop landing.

All tests run without accessing a private Tailscale network or changing files.
"""
import unittest
from pathlib import Path
from unittest.mock import Mock
from local_app import server

WEB = Path(__file__).resolve().parents[1] / "local_app" / "web"


class MobileRootEntryTests(unittest.TestCase):
    def handler(self, ua):
        handler = server.Handler.__new__(server.Handler)
        handler.path = "/"
        handler.headers = {"User-Agent": ua}
        handler.send_response = Mock()
        handler.send_header = Mock()
        handler.end_headers = Mock()
        handler.send_bytes = Mock()
        return handler

    def test_mobile_root_opens_actual_web_studio_even_without_js(self):
        for agent in (
            "Mozilla/5.0 (iPhone; CPU iPhone OS 26_6 like Mac OS X)",
            "Mozilla/5.0 (iPad; CPU OS 26_6 like Mac OS X)",
            "Mozilla/5.0 (Linux; Android 16; Pixel 10)",
        ):
            handler = self.handler(agent)
            handler.do_GET()
            handler.send_response.assert_called_once_with(302)
            handler.send_header.assert_any_call("Location", "/localaiweb")
            handler.send_header.assert_any_call("Cache-Control", "no-store, max-age=0")
            handler.send_bytes.assert_not_called()

    def test_desktop_root_keeps_localai_vision(self):
        handler = self.handler("Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
        handler.do_GET()
        handler.send_bytes.assert_called_once()
        handler.send_response.assert_not_called()

    def test_mobile_can_explicitly_open_full_localai_vision(self):
        handler = self.handler("Mozilla/5.0 (iPhone; CPU iPhone OS 26_6)")
        handler.path = "/?studio=vision"
        handler.do_GET()
        handler.send_bytes.assert_called_once()
        handler.send_response.assert_not_called()

    def test_homepage_button_is_real_accessible_link(self):
        html = (WEB / "index.html").read_text(encoding="utf-8")
        self.assertIn('id="localAiWebEntry"', html)
        self.assertIn('class="localaiweb-entry" href="/localaiweb"', html)
        self.assertIn('src="/assets/pwa-install.js"', html)

    def test_mobile_hub_displays_real_pc_build_and_pending_update(self):
        projects=(WEB / "localaiweb-projects.html").read_text(encoding="utf-8")
        updates=(WEB / "localaiweb-update.js").read_text(encoding="utf-8")
        self.assertIn('id="lawMobileBuildStatus"', projects)
        self.assertIn("fetch('/api/ping',{cache:'no-store'})", updates)
        self.assertIn("fetch('/api/update/check',{cache:'no-store'})", updates)
        self.assertIn("Mets à jour LocalAiVision sur le PC", updates)
        self.assertIn("window.location.reload()", updates)
        self.assertNotIn("✓ Mises à jour auto", updates)


if __name__ == "__main__":
    unittest.main()
