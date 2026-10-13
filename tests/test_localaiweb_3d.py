"""Regression coverage for LocalAiWeb's optional WebGL3D path."""
import base64
import io
import tempfile
import unittest
import zipfile
from pathlib import Path

from local_app import web_builder

ROOT = Path(__file__).resolve().parent.parent


def minimal_glb():
    """Small syntactically valid GLB 2.0 with a JSON asset chunk."""
    payload = b'{"asset":{"version":"2.0"}}'
    payload += b' ' * ((-len(payload)) % 4)
    total = 20 + len(payload)
    return (b'glTF' + (2).to_bytes(4, 'little') + total.to_bytes(4, 'little')
            + len(payload).to_bytes(4, 'little') + b'JSON' + payload)


class Cinematic3DTemplateTests(unittest.TestCase):
    def test_default_projects_remain_simple_and_3d_is_explicit(self):
        with tempfile.TemporaryDirectory() as temp:
            store = web_builder.LocalAiWebStore(temp, lambda *_: '{}')
            plain = store.create('Site classique')
            immersive = store.create('Site 3D', template='cinematic3d')
            self.assertIn('Ton prochain site', plain['files']['index.html'])
            self.assertNotIn('three@', plain['files']['index.html'])
            self.assertEqual(plain['project']['settings']['art_direction'], 'auto')
            self.assertIn('three@0.186.1', immersive['files']['index.html'])
            self.assertIn('data-model-src=', immersive['files']['index.html'])
            self.assertIn('GLTFLoader', immersive['files']['app.js'])
            self.assertIn('prefers-reduced-motion', immersive['files']['styles.css'])
            self.assertEqual(immersive['project']['template'], 'cinematic3d')
            self.assertEqual(immersive['project']['settings']['art_direction'], 'spatial3d')
            self.assertEqual(immersive['project']['settings']['site_kind'], 'landing')
            self.assertNotEqual(plain['project']['id'], immersive['project']['id'])
            self.assertNotEqual(store.project_dir(plain['project']['id']),
                                store.project_dir(immersive['project']['id']))
            report = store.preflight(immersive['project']['id'])
            self.assertTrue(report['ok'], report['blockers'])

    def test_glb_import_is_checked_and_exported_only_with_its_project(self):
        with tempfile.TemporaryDirectory() as temp:
            store = web_builder.LocalAiWebStore(temp, lambda *_: '{}')
            site = store.create('Experience', template='cinematic3d')
            other = store.create('Autre site')
            pid = site['project']['id']
            valid = 'data:model/gltf-binary;base64,' + base64.b64encode(minimal_glb()).decode()
            asset = store.save_asset(pid, 'objet.glb', valid)
            self.assertEqual(asset['path'], 'assets/objet.glb')
            self.assertNotIn('assets/objet.glb', other['assets'])
            with zipfile.ZipFile(io.BytesIO(store.export_zip(pid))) as archive:
                self.assertIn('assets/objet.glb', archive.namelist())
            with zipfile.ZipFile(io.BytesIO(store.export_zip(other['project']['id']))) as archive:
                self.assertNotIn('assets/objet.glb', archive.namelist())
            with self.assertRaisesRegex(ValueError, 'GLB'):
                store.save_asset(pid, 'fake.glb', 'data:application/octet-stream;base64,' + base64.b64encode(b'bad').decode())
            with self.assertRaisesRegex(ValueError, 'non pris en charge'):
                store.save_asset(pid, 'evil.html', valid)

    def test_modes_are_independent_and_validated(self):
        with tempfile.TemporaryDirectory() as temp:
            store = web_builder.LocalAiWebStore(temp, lambda *_: '{}')
            first = store.create('Boutique')
            second = store.create('Portfolio')
            a, b = first['project']['id'], second['project']['id']
            changed = store.update_settings(a, {'site_kind':'store','art_direction':'cinematic'})
            self.assertEqual(changed['project']['settings']['site_kind'], 'store')
            self.assertEqual(changed['project']['settings']['art_direction'], 'cinematic')
            self.assertEqual(store.meta(b)['settings']['art_direction'], 'auto')
            desc = web_builder.generation_direction(changed['project']['settings'])
            self.assertIn('Boutique', desc)
            self.assertIn('Cinematique', desc)
            with self.assertRaises(ValueError):
                store.update_settings(a, {'art_direction':'not-real'})
            with self.assertRaises(ValueError):
                store.create('Not real', template='nonexistent')

    def test_frontend_wiring_and_three_demo_exist(self):
        html = (ROOT / 'local_app/web/localaiweb.html').read_text(encoding='utf-8')
        js = (ROOT / 'local_app/web/localaiweb.js').read_text(encoding='utf-8')
        self.assertIn('id="lawNew3d"', html)
        self.assertIn('id="lawArtDirection"', html)
        self.assertIn('id="lawSiteKind"', html)
        self.assertIn('create3dProject', js)
        self.assertIn('template:\'cinematic3d\'', js)
        self.assertIn('saveCreativeBrief', js)
        self.assertIn('data-model-src=', js)
        self.assertTrue((ROOT / 'local_app/web/templates/cinematic3d/app.js').is_file())


if __name__ == '__main__':
    unittest.main()
