"""The Windows icon is the whole locked master, at every embedded size."""
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image, ImageChops
from scripts import prepare_windows_brand as branding

ROOT = Path(__file__).resolve().parents[1]


class LockedWindowsIconTests(unittest.TestCase):
    def test_all_archived_masters_match_the_supplied_checksums(self):
        folder = branding.MASTER.parent
        for line in (folder / 'SHA256SUMS.txt').read_text(encoding='utf-8').splitlines():
            digest, name = line.split('  ', 1)
            with self.subTest(file=name):
                self.assertEqual(hashlib.sha256((folder / name).read_bytes()).hexdigest(), digest)

    def test_every_ico_frame_is_the_uncropped_original_scaled_once(self):
        original_bytes = branding.MASTER.read_bytes()
        with Image.open(branding.MASTER) as image:
            original = image.convert('RGBA')
        with tempfile.TemporaryDirectory() as tmp:
            output = branding.prepare(Path(tmp))
            with Image.open(output / 'LocalAiStudio.ico') as ico:
                self.assertEqual(ico.ico.sizes(), {(s, s) for s in branding.ICON_SIZES})
                for size in branding.ICON_SIZES:
                    expected = original.resize((size, size), Image.Resampling.LANCZOS)
                    actual = ico.ico.getimage((size, size)).convert('RGBA')
                    with self.subTest(size=size):
                        self.assertIsNone(ImageChops.difference(actual, expected).getbbox(alpha_only=False))
        self.assertEqual(branding.MASTER.read_bytes(), original_bytes)

    def test_a_changed_master_is_rejected_before_any_output_is_written(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            altered = root / 'altered.png'
            altered.write_bytes(b'not the approved master')
            with patch.object(branding, 'MASTER', altered):
                with self.assertRaises(RuntimeError):
                    branding.prepare(root / 'output')
            self.assertFalse((root / 'output').exists())

    def test_runtime_icon_and_both_build_paths_use_the_full_studio_ico(self):
        from local_app import launcher
        with Image.open(launcher.APPLICATION_ICON) as ico, Image.open(branding.MASTER) as original:
            expected = original.convert('RGBA').resize((256, 256), Image.Resampling.LANCZOS)
            self.assertEqual(ico.ico.getimage((256, 256)).convert('RGBA').tobytes(), expected.tobytes())
        for name in ['BUILD_LOCALVISIONAI.bat', '.github/workflows/build-windows.yml']:
            source = (ROOT / name).read_text(encoding='utf-8')
            self.assertIn('--icon "build\\branding\\LocalAiStudio.ico"', source)
            self.assertIn('build\\branding\\LocalAiStudio.ico;local_app\\assets', source)

    def test_windows_evidence_waits_for_nonblank_webview_content(self):
        source = (ROOT / 'scripts/verify_windows_icon.py').read_text(encoding='utf-8')
        self.assertIn("deadline=time.monotonic()+60", source)
        self.assertIn('stats.stddev[0]>8', source)
        self.assertIn("native-window-content.png", source)
        self.assertIn("native-window-blank.png", source)
        self.assertIn('WebView content stayed blank', source)


if __name__ == '__main__':
    unittest.main()
