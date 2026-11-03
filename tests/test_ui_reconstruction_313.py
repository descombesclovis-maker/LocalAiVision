"""Regression coverage for changed UI and commercial isolation contracts."""
from pathlib import Path
import shutil
import subprocess
import unittest
from unittest.mock import Mock
from local_app import server

ROOT=Path(__file__).resolve().parents[1]

class Reconstruction313(unittest.TestCase):
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
