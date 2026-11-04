"""Studio 293 regression: cinematic landing, real Maps cards and measured Codex QA."""
from pathlib import Path
from unittest import TestCase
from local_app import web_experience_contract

ROOT=Path(__file__).resolve().parents[1]
WEB=ROOT/"local_app"/"web"


class LandingExperience(TestCase):
    def test_all_entrances_are_local_and_existing_paths_are_preserved(self):
        html=(WEB/"localai-studio.html").read_text(encoding="utf-8")
        for path in ('href="/localaiweb"', 'href="/localaivision"',
                     'href="/studio"'):
            self.assertIn(path,html)
        self.assertNotIn("images.unsplash.com",html)
        self.assertNotIn("http://",html)
        self.assertNotIn("https://",html)
        self.assertIn("studio-scene",html)
        self.assertIn('studio-system.css',html)
        self.assertIn('localai-studio-motion.js',html)
        self.assertIn('studio-activity.js',html)

    def test_cinematic_motion_respects_keyboard_and_accessibility(self):
        css=(WEB/"localai-studio-next.css").read_text(encoding="utf-8")
        js=(WEB/"localai-studio-motion.js").read_text(encoding="utf-8")
        self.assertIn("prefers-reduced-motion",css)
        self.assertIn("prefers-reduced-motion",js)
        self.assertIn("focus-visible",css)
        self.assertIn("qcm-reduce-motion",js)
        self.assertNotIn("card.style.transform",js)
        self.assertIn("document.body.classList.add('studio-entering')",js)
        self.assertIn("return",js)
        self.assertIn("190",js)
        self.assertIn("@keyframes",css)

    def test_logo_files_are_embedded_scalable_svg(self):
        import xml.etree.ElementTree as ET
        for name in ("brand-studio.svg","brand-web.svg","brand-vision.svg"):
            xml=(WEB/name).read_text(encoding="utf-8")
            root=ET.fromstring(xml)
            self.assertIn("viewBox",root.attrib)
            self.assertIn("<path",xml)
            self.assertNotIn("data:image",xml)


class WebQuality(TestCase):
    def test_animated_brief_requires_actual_renderable_motion_and_accessibility(self):
        files={"index.html":"<html lang='fr'><main>Un site spectaculaire</main></html>",
               "style.css":"body { color:#eee }"}
        issues=web_experience_contract.check(files,"Créer un site avec animations spectaculaires")
        codes={issue["id"] for issue in issues}
        self.assertEqual(codes,{"motion_missing","motion_accessibility","keyboard_interaction"})
        files["style.css"]="@keyframes appear{from{opacity:0}to{opacity:1}}\n"+\
          "@media(prefers-reduced-motion:reduce){*{animation:none!important}}\n"+\
          "a:focus-visible{outline:2px solid}"
        self.assertEqual(web_experience_contract.check(files,
            "Créer un site avec animations spectaculaires"),[])
        self.assertEqual(web_experience_contract.check({"index.html":"<main>Simple</main>"},
            "Site minimal sans animation"),[])

    def test_real_coding_pipeline_invokes_nonprompt_visual_gate(self):
        py=(ROOT/"local_app"/"web_hybrid.py").read_text(encoding="utf-8")
        self.assertIn("web_experience_contract.check(files, request)",py)
        self.assertIn("web_browser_qa.review(site",py)
        self.assertIn("contract_repair_prompt",py)


class MapAndAds(TestCase):
    def test_official_google_selection_and_original_card_are_available(self):
        google=(WEB/"localaiweb-google-map.js").read_text(encoding="utf-8")
        html=(WEB/"localaiweb-map.html").read_text(encoding="utf-8")
        self.assertIn("clickableIcons:true",google)
        self.assertIn("event.placeId",google)
        self.assertIn("/api/web/map/google/place?",google)
        self.assertIn('<gmp-place-details id="googlePlaceDetails">',html)
        self.assertIn('<gmp-place-all-content>',html)
        self.assertLess(html.index('</gmp-place-details>'),html.index('id="mapCreate"'))

    def test_ad_aspect_is_enforced_without_expert_panel(self):
        ads=(WEB/"studio-ads.js").read_text(encoding="utf-8")
        core=(WEB/"app.js").read_text(encoding="utf-8")
        self.assertIn("function activeAspect(task)",ads)
        self.assertIn("getBrands,activeAspect,endGeneration",ads)
        self.assertIn("campaignAspect||'auto'",core)
        self.assertIn("StudioAds?.endGeneration?.(task)",core)

