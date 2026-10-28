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
    def test_all_three_supplied_webp_images_are_valid_embedded_assets(self):
        for name in ("brand-vision.svg","brand-identity.svg","brand-web.svg"):
            with self.subTest(name=name):
                content=(WEB/name).read_text(encoding="utf-8")
                ET.fromstring(content)
                match=re.search(r'data:image/webp;base64,([A-Za-z0-9+/=]+)',content)
                self.assertIsNotNone(match)
                data=base64.b64decode(match.group(1),validate=True)
                self.assertGreater(len(data),1000)
                self.assertEqual(data[:4],b"RIFF")
                self.assertEqual(data[8:12],b"WEBP")
                self.assertEqual(struct.unpack("<I",data[4:8])[0]+8,len(data))

    def test_studios_use_the_correct_symbols_and_master_identity(self):
        vision=(WEB/"index.html").read_text(encoding="utf-8")
        projects=(WEB/"localaiweb-projects.html").read_text(encoding="utf-8")
        editor=(WEB/"localaiweb.html").read_text(encoding="utf-8")
        map_html=(WEB/"localaiweb-map.html").read_text(encoding="utf-8")
        manifest=(WEB/"manifest.webmanifest").read_text(encoding="utf-8")
        self.assertIn('src="/assets/brand-vision.svg"',vision)
        self.assertIn('src="/assets/brand-identity.svg"',vision)
        self.assertIn('src="/assets/brand-identity.svg"',projects)
        for web_ui in (projects,editor,map_html):
            self.assertIn('src="/assets/brand-web.svg"',web_ui)
        self.assertIn("/assets/app-icon.svg",manifest)
        self.assertIn("brand-identity.svg",
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
