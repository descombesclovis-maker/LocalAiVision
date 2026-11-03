"""User-approved 261-answer QCM V1: non-destructive multi-page acceptance tests.

These are structural contracts, not a substitute for actual screenshot/GPU QA.
"""
import json
from pathlib import Path
from unittest import TestCase

ROOT=Path(__file__).resolve().parents[1]
WEB=ROOT/"local_app"/"web"

class ApprovedQcmV1(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec=json.loads((ROOT/"docs/LOCALAI_STUDIO_QCM_V1_APPROVED.json").read_text(encoding="utf-8"))
        cls.answers={key:val for section in cls.spec["sections"] for key,val in section["answers"].items()}

    def test_all_261_decisions_in_19_sections_are_preserved(self):
        self.assertEqual(self.spec["completed"],261)
        self.assertEqual(self.spec["essential"],83)
        self.assertEqual(len(self.spec["sections"]),19)
        self.assertEqual(len(self.answers),261)
        self.assertEqual(self.answers["home_macro"],"Menu radial / orbites")
        self.assertEqual(self.answers["web_chat_width"],"Redimensionnable, départ 32 %")
        self.assertEqual(self.answers["map_camera"],"France entière")
        self.assertEqual(self.answers["adult_gallery"],"Fermable avec croix")
        self.assertEqual(self.answers["agents_rollout"],"Afficher seulement si opérationnelles")
        self.assertTrue(self.spec["policy"]["preserveProjects"])
        self.assertTrue(self.spec["policy"]["doNotChangeNsfwUI"])

    def test_new_assets_are_referenced_from_real_pages(self):
        mapping={
          "localai-studio.html":["studio-qcm-v1.css","studio-qcm-shell.js","studio-qcm-home.js","qcm-orbit-center"],
          "localaiweb.html":["studio-qcm-v1.css","studio-qcm-shell.js","studio-qcm-editor.js"],
          "localaiweb-projects.html":["studio-qcm-v1.css","studio-qcm-shell.js","studio-qcm-projects.js"],
          "localaiweb-map.html":["studio-qcm-v1.css","studio-qcm-shell.js","studio-qcm-map.js"],
          "index.html":["studio-qcm-v1.css","studio-qcm-vision.css","studio-qcm-shell.js","studio-qcm-vision.js"],
        }
        for path,assets in mapping.items():
            html=(WEB/path).read_text(encoding="utf-8")
            for asset in assets:
                with self.subTest(page=path,asset=asset):
                    self.assertIn(asset,html)
                    if asset.endswith((".css",".js")):
                        self.assertTrue((WEB/asset).is_file(),asset)

    def test_orbit_is_responsive_and_dock_routes_are_real(self):
        css=(WEB/"studio-qcm-v1.css").read_text(encoding="utf-8")
        home=(WEB/"localai-studio.html").read_text(encoding="utf-8")
        nav=(WEB/"studio-qcm-shell.js").read_text(encoding="utf-8")
        self.assertIn("qcm-orbit-center",css)
        self.assertIn("@keyframes qcm-orbit-float",css)
        self.assertIn("prefers-reduced-motion",css)
        self.assertIn("href=\"/localaiweb\"",home)
        self.assertIn("href=\"/localaivision\"",home)
        self.assertIn("'/studio'",nav)
        self.assertIn("'/localaiweb/map'",nav)
        self.assertIn("e.key.toLowerCase()==='k'",nav)

    def test_editor_real_split_and_existing_rename(self):
        js=(WEB/"studio-qcm-editor.js").read_text(encoding="utf-8")
        self.assertIn("32",js)
        self.assertIn("pointermove",js)
        self.assertIn("ArrowRight",js)
        self.assertIn("/api/web/project/rename",js)
        self.assertIn("data-qcm-rename",js)

    def test_project_cards_trigger_existing_workflows(self):
        js=(WEB/"studio-qcm-projects.js").read_text(encoding="utf-8")
        self.assertIn("addCreationTile('projectsGrid'",js)
        self.assertIn("create.click()",js)
        self.assertIn("fromMap.click()",js)
        self.assertIn("localaiweb_qcm_project_tab",js)

    def test_map_filters_only_truthfully_and_google_dark_style(self):
        base=(WEB/"localaiweb-map.js").read_text(encoding="utf-8")
        google=(WEB/"localaiweb-google-map.js").read_text(encoding="utf-8")
        html=(WEB/"localaiweb-map.html").read_text(encoding="utf-8")
        self.assertIn('id="qcmWebsiteFilter"',html)
        self.assertIn('id="qcmWebsiteBadge"',html)
        self.assertIn("matchesWebsite",base)
        self.assertIn("if(config.places_enabled&&siteFilter)",base)
        self.assertIn("siteFilter.disabled=true",base)
        self.assertIn("window.StudioMapRecenter",base)
        self.assertIn("window.StudioMapRecenter",google)
        self.assertIn("color:'#171d28'",google)

    def test_web_editor_real_panels_versions_and_media(self):
        html=(WEB/"localaiweb.html").read_text(encoding="utf-8")
        js=(WEB/"studio-qcm-editor-rail.js").read_text(encoding="utf-8")
        for resource in ("studio-qcm-editor-rail.js","studio-qcm-editor.js"):
            self.assertIn(resource,html)
        for contract in ("/api/web/project?id=", "/api/web/version/restore",
                         "data.assets", "data.versions", "data.files",
                         "confirm(", "location.reload()",
                         "qcm-select-source"):
            self.assertIn(contract,js)

    def test_public_vision_library_has_no_fake_media_or_adult_leak(self):
        html=(WEB/"index.html").read_text(encoding="utf-8")
        js=(WEB/"studio-qcm-library.js").read_text(encoding="utf-8")
        css=(WEB/"studio-qcm-library.css").read_text(encoding="utf-8")
        for asset in ("studio-qcm-library.js","studio-qcm-library.css"):
            self.assertIn(asset,html)
        for contract in ("const isAdult=", "card.querySelector('img,video')",
                         "validSrc", "node.src=href", "qcm-library-list"):
            self.assertIn(contract,js)
        self.assertIn("body.nsfw-active .qcm-library-dialog",css)
        self.assertNotIn("/api/studio/media/start",js)

    def test_acceptance_spec_covers_each_choice_and_is_honest_about_status(self):
        spec=(ROOT/"docs/LOCALAI_STUDIO_FINAL_QCM_ACCEPTANCE_261.md").read_text(encoding="utf-8")
        self.assertIn("261/261",spec)
        self.assertIn("CI",spec)
        for key in self.answers:
            self.assertIn("`"+key+"`",spec)
        self.assertIn("À développer",spec)
        self.assertIn("Aucun build CI vert",spec)

    def test_vision_uses_real_results_only_and_never_modifies_adult_ui(self):
        js=(WEB/"studio-qcm-vision.js").read_text(encoding="utf-8")
        css=(WEB/"studio-qcm-vision.css").read_text(encoding="utf-8")
        self.assertIn("messages.querySelectorAll('.generation-frame .result-media')",js)
        self.assertIn("isAdult()",js)
        self.assertIn("viewer.hidden=true;clear();return",js)
        self.assertIn("body.nsfw-active .qcm-vision-viewer",css)
        self.assertNotIn("/api/loras/install",js)
