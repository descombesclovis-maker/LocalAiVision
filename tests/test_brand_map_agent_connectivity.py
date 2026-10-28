"""Correct brand separation, usable composers, real map providers and agent login."""
from pathlib import Path
import os
import tempfile
import unittest
from unittest.mock import patch

from local_app import integrations_cli
ROOT=Path(__file__).resolve().parents[1]
WEB=ROOT/"local_app"/"web"

class BrandMapAgentTests(unittest.TestCase):
    def test_vision_and_web_have_different_slogans_and_crisp_svg(self):
        vision=(WEB/"brand-identity.svg").read_text(encoding="utf-8")
        web=(WEB/"brand-web-identity.svg").read_text(encoding="utf-8")
        self.assertIn("CRÉATIONS VISUELLES",vision)
        self.assertNotIn("CRÉATION DE SITES WEB",vision)
        self.assertIn("CRÉATIONS DE SITES WEBS",web)
        self.assertNotIn("CRÉATIONS VISUELLES",web)
        for value in (vision,web):
            self.assertNotIn("data:image/webp;base64",value)
            self.assertIn("<svg",value)
        main=(WEB/"index.html").read_text(encoding="utf-8")
        hub=(WEB/"localaiweb-projects.html").read_text(encoding="utf-8")
        self.assertIn('src="/assets/brand-identity.svg"',main)
        self.assertIn('src="/assets/brand-web-identity.svg"',hub)
        self.assertNotIn('src="/assets/brand-identity.svg"',hub)

    def test_composer_and_responsive_layout_not_absolute_clipped(self):
        css=(WEB/"studio-redesign.css").read_text(encoding="utf-8")
        suite=(WEB/"studio-suite.css").read_text(encoding="utf-8")
        self.assertIn("height:100dvh",css)
        self.assertIn("env(safe-area-inset-bottom",css)
        self.assertIn(".composer-wrap{position:relative",css)
        self.assertIn(".chat-composer{flex:0 0 auto",suite)
        self.assertIn("max-height:45dvh",suite)

    def test_map_two_colors_and_independent_official_geo_api(self):
        source=(WEB/"localaiweb-map.js").read_text(encoding="utf-8")
        provider=(ROOT/"local_app/web_map_no_website.py").read_text(encoding="utf-8")
        for check in ("'#36d77f'","'#ef535e'","website_recorded"):
            self.assertIn(check,source)
        self.assertIn("recherche-entreprises.api.gouv.fr/near_point",provider)
        self.assertIn("inconnu_registre",provider)
        self.assertIn("CACHE_DIR",provider)
        html=(WEB/"localaiweb-map.html").read_text(encoding="utf-8")
        self.assertIn("legend-green",html)
        self.assertIn("legend-red",html)

    def test_claude_cli_detects_standard_user_installs_without_path(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            executable=root/".local"/"bin"/"claude.exe"
            executable.parent.mkdir(parents=True,exist_ok=True)
            executable.write_bytes(b"test-only")
            with patch.object(integrations_cli,"_which",return_value=None):
                with patch("pathlib.Path.home",return_value=root):
                    with patch.dict(os.environ,{"APPDATA":str(root/"AppData"/"Roaming"),
                                               "LOCALAPPDATA":str(root/"AppData"/"Local")}):
                        self.assertEqual(integrations_cli._claude_cmd(),[str(executable)])

    def test_claude_connect_is_explicit_not_silent(self):
        source=(WEB/"localaiweb-agent.js").read_text(encoding="utf-8")
        editor=(WEB/"localaiweb.html").read_text(encoding="utf-8")
        hub=(WEB/"localaiweb-projects.html").read_text(encoding="utf-8")
        self.assertIn("provider:'claude'",source)
        self.assertIn("/api/web/capabilities",source)
        self.assertIn("/api/web/integrations/connect",source)
        self.assertIn('id="connectClaude"',editor)
        self.assertIn('id="connectClaude"',hub)
        script=(ROOT/"local_app/integrations_cli.py").read_text(encoding="utf-8")
        self.assertIn('elif provider == "claude":',script)

    def test_real_local_model_repair_command_is_available(self):
        page=(WEB/"index.html").read_text(encoding="utf-8")
        js=(WEB/"studio-redesign.js").read_text(encoding="utf-8")
        self.assertIn('id="engineRecoveryButton"',page)
        self.assertIn("byId('retrySetup')?.click()",js)
        self.assertIn("window.confirm(",js)
        self.assertIn("updateEngineHealth()",js)

if __name__=="__main__":unittest.main()
