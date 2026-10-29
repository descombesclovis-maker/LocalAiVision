"""Brand assets and Windows release identity regression checks.

The supplied logos are embedded locally; no remote runtime image provider.
Branding cannot, by itself, confer trusted Windows publisher reputation.
"""
import base64
from pathlib import Path
import re
import struct
import unittest
import xml.etree.ElementTree as ET

BASE=Path(__file__).resolve().parents[1]
WEB=BASE/"local_app"/"web"


class BrandTests(unittest.TestCase):
    def test_crisp_vector_branding_and_separate_slogans(self):
        for name in ("brand-studio.svg","brand-vision.svg","brand-identity.svg","brand-web.svg","brand-web-identity.svg"):
            with self.subTest(name=name):
                content=(WEB/name).read_text(encoding="utf-8")
                root=ET.fromstring(content)
                self.assertIn("viewBox",root.attrib)
                self.assertNotIn("data:image/webp;base64",content)
                self.assertIn("<path",content)
        vision=(WEB/"brand-identity.svg").read_text(encoding="utf-8")
        web=(WEB/"brand-web-identity.svg").read_text(encoding="utf-8")
        self.assertIn("CRÉATIONS VISUELLES",vision)
        self.assertNotIn("CRÉATION DE SITES WEB",vision)
        self.assertIn("SITES &amp; IDENTITÉS",web)
        self.assertNotIn("CRÉATIONS VISUELLES",web)

    def test_studios_use_the_correct_symbols_and_master_identity(self):
        vision=(WEB/"index.html").read_text(encoding="utf-8")
        projects=(WEB/"localaiweb-projects.html").read_text(encoding="utf-8")
        editor=(WEB/"localaiweb.html").read_text(encoding="utf-8")
        map_html=(WEB/"localaiweb-map.html").read_text(encoding="utf-8")
        manifest=(WEB/"manifest.webmanifest").read_text(encoding="utf-8")
        self.assertIn('src="/assets/brand-vision.svg"',vision)
        self.assertIn('src="/assets/brand-vision.svg"',vision)
        self.assertIn('Décris ton image, ta vidéo ou ta publicité.',vision)
        self.assertIn('src="/assets/brand-web-identity.svg"',projects)
        self.assertNotIn('src="/assets/brand-identity.svg"',projects)
        for web_ui in (projects,editor,map_html):
            self.assertIn('src="/assets/brand-web.svg"',web_ui)
        self.assertIn("/assets/app-icon.svg",manifest)
        self.assertIn("brand-studio.svg",
                      (BASE/"scripts/prepare_windows_brand.py").read_text(encoding="utf-8"))

    def test_windows_embeds_icon_and_only_signs_with_real_certificate(self):
        workflow=(BASE/".github/workflows/build-windows.yml").read_text(encoding="utf-8")
        self.assertIn("python scripts/prepare_windows_brand.py",workflow)
        self.assertIn('--icon "build\\branding\\LocalAiVision.ico"',workflow)
        self.assertIn("Get-AuthenticodeSignature",workflow)
        self.assertIn("WINDOWS_SIGN_CERT_B64",workflow)
        self.assertIn("LocalVisionAI-Windows.sha256",workflow)


if __name__=="__main__":
    unittest.main()
