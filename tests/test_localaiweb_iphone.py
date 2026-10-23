from pathlib import Path
import json
import unittest

WEB = Path(__file__).resolve().parents[1] / "local_app" / "web"

class LocalAiWebIphoneContractTests(unittest.TestCase):
    def test_dedicated_iphone_manifest(self):
        manifest = json.loads((WEB / "localaiweb-mobile.webmanifest").read_text(encoding="utf-8"))
        self.assertEqual(manifest["id"], "/localaiweb")
        self.assertEqual(manifest["start_url"], "/localaiweb")
        self.assertEqual(manifest["scope"], "/localaiweb")
        self.assertEqual(manifest["display"], "standalone")

    def test_all_localaiweb_pages_use_own_manifest_and_mobile_assets(self):
        for filename in ("localaiweb.html", "localaiweb-projects.html", "localaiweb-map.html"):
            html = (WEB / filename).read_text(encoding="utf-8")
            with self.subTest(filename=filename):
                self.assertIn('href="/assets/localaiweb-mobile.webmanifest"', html)
                self.assertIn('href="/assets/localaiweb-mobile.css"', html)
                self.assertIn('src="/assets/localaiweb-mobile.js"', html)

    def test_original_server_routes_unchanged(self):
        server = (WEB.parent / "server.py").read_text(encoding="utf-8")
        self.assertIn('HOST = "127.0.0.1"', server)
        self.assertIn('"/localaiweb/editor"', server)
        self.assertIn('"/api/web/generate"', server)

    def test_no_fake_cloud_compute_in_mobile_adapter(self):
        js = (WEB / "localaiweb-mobile.js").read_text(encoding="utf-8")
        self.assertNotIn("OPENAI_API_KEY", js)
        self.assertNotIn("service_role", js)
        self.assertIn("server-owned", js)

if __name__ == "__main__":
    unittest.main()
