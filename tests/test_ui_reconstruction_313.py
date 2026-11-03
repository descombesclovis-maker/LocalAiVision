"""Regression coverage for changed UI and commercial isolation contracts."""
from pathlib import Path
import shutil
import subprocess
import unittest
import tempfile
from unittest.mock import Mock
from local_app import server

ROOT=Path(__file__).resolve().parents[1]

class Reconstruction313(unittest.TestCase):
    def test_google_project_stores_only_place_reference_and_waits_for_user_brief(self):
        from local_app import web_builder, web_google_maps
        with tempfile.TemporaryDirectory() as tmp:
            store=web_builder.LocalAiWebStore(Path(tmp),lambda *_:'{}')
            original={'google_place_id':'PLACE_TEST_ID_313','name':'Restricted Google name',
                      'address':'Restricted address','phone':'0123456789',
                      'website':'https://restricted.example','lat':46.6,'lon':2.28}
            payload,reference=web_google_maps.create_reference_project(store,original)
            self.assertEqual(payload['project']['business']['google_place_id'],'PLACE_TEST_ID_313')
            self.assertEqual(payload['project']['initial_generation']['status'],'brief_required')
            self.assertNotIn('address',reference)
            for file in Path(tmp).rglob('*.json'):
                text=file.read_text()
                for forbidden in ['Restricted Google name','Restricted address','0123456789','restricted.example']:
                    self.assertNotIn(forbidden,text)
            self.assertFalse(store.claim_initial_generation(payload['project']['id'])['ready'])

    @unittest.skipUnless(shutil.which('node'), 'Node required for browser adapter test')
    def test_google_selection_cannot_reuse_stale_or_mismatched_tokens(self):
        result=subprocess.run(['node','tests/ui313_google_map.cjs'],cwd=ROOT,capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_commercial_origin_only_adds_named_shared_ui_assets(self):
        handler=object.__new__(server.Handler)
        handler.headers={'Host':'ventes.localhost:3000'}
        handler.send_json=Mock()
        for asset in ['studio-system.css','studio-qcm-v1.css','studio-qcm-shell.js']:
            self.assertTrue(handler._sales_surface('/assets/'+asset))
        for denied in ['/assets/app.js','/api/web/generate','/localaiweb/editor','/api/studio/brands','/service-worker.js']:
            self.assertFalse(handler._sales_surface(denied),denied)

    def test_new_shared_style_excludes_reserved_workspace(self):
        style=(ROOT/'local_app/web/studio-system.css').read_text()
        self.assertIn('body[data-studio-page]:not(.nsfw-active)',style)
        vision=(ROOT/'local_app/web/studio-qcm-vision.js').read_text()
        self.assertIn("importButton.append(svg)",vision)
        self.assertIn("viewer.hidden=true;clear();return",vision)

if __name__=='__main__':
    unittest.main()
