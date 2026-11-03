"""Brand-identity and public-menu regressions after the Codex 314 handoff."""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "local_app" / "web"
BRAND = WEB / "assets" / "brand-reference"
STUDIO = "/assets/assets/brand-reference/LocalAIStudio_Official_Original.png"
WEB_LOGO = "/assets/assets/brand-reference/LocalAIWeb_Official_Original.png"
VISION = "/assets/assets/brand-reference/LocalAIVision_Official_Original.png"


class Completion314Tests(unittest.TestCase):
    def test_three_locked_originals_exist_and_are_used_by_pages(self):
        for name in ["Studio", "Web", "Vision"]:
            path = BRAND / ("LocalAI" + name + "_Official_Original.png")
            self.assertTrue(path.is_file(), path)
            self.assertGreater(path.stat().st_size, 10000)
        self.assertIn(STUDIO, (WEB / "localai-studio.html").read_text(encoding="utf-8"))
        self.assertIn(STUDIO, (WEB / "studio-brands.html").read_text(encoding="utf-8"))
        self.assertIn(WEB_LOGO, (WEB / "localaiweb.html").read_text(encoding="utf-8"))
        self.assertIn(VISION, (WEB / "studio-qcm-vision.js").read_text(encoding="utf-8"))

    def test_web_and_vision_installable_icons_are_official_untouched_pngs(self):
        web = json.loads((WEB / "localaiweb.webmanifest").read_text(encoding="utf-8"))
        vision = json.loads((WEB / "manifest.webmanifest").read_text(encoding="utf-8"))
        for manifest, icon in [(web, WEB_LOGO), (vision, VISION)]:
            self.assertEqual(manifest["icons"][0]["src"], icon)
            self.assertEqual(manifest["icons"][0]["type"], "image/png")
            self.assertEqual(manifest["icons"][0]["sizes"], "724x724")
            self.assertEqual(manifest["icons"][0]["purpose"], "any")

    def test_public_vision_only_two_text_only_teal_menu_actions(self):
        css = (WEB / "studio-system.css").read_text(encoding="utf-8")
        self.assertIn('.studio-navigation .nav-glyph{display:inline-flex', css)
        self.assertIn('#visionAdvancedToggle .nav-glyph{display:none!important}', css)
        self.assertIn('#newConversation', css)
        self.assertIn('background:linear-gradient(122deg,#16475a,#0f3545)', css)
        self.assertIn(':not(.nsfw-active)', css)
        self.assertIn('popover', (WEB / "index.html").read_text(encoding="utf-8")
                      + (WEB / "app.js").read_text(encoding="utf-8"))

    def test_clipboard_platform_line_endings_do_not_mask_modified_prompts(self):
        qa = (ROOT / "scripts" / "qa_ui_314.cjs").read_text(encoding="utf-8")
        self.assertIn('normaliseClipboardLines', qa)
        self.assertIn('assert.equal(raw,ids.prompt', qa)
        self.assertIn('navigator.clipboard.readText()', qa)

    def test_motion_is_scoped_and_stops_when_hidden_or_gpu_is_busy(self):
        css = (WEB / "studio-system.css").read_text(encoding="utf-8")
        self.assertIn('studio314-light-rivers', css)
        self.assertIn('studio314-ambient-drift', css)
        self.assertIn('[data-gpu-busy="true"]', css)
        self.assertIn('[data-motion-paused="true"]', css)
        self.assertIn('prefers-reduced-motion:reduce', css)
        js = (WEB / "studio-activity.js").read_text(encoding="utf-8")
        self.assertIn('document.hidden', js)
        self.assertIn('dataset.gpuBusy', js)


if __name__ == "__main__":
    unittest.main()
