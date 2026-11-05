"""Decoder tests use synthetic files, never stand in for real AI benchmarks."""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from local_app.media_validation import inspect_output


class MediaValidationTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)

    def test_image_pixels_decoded_and_dimensions_observed(self):
        from PIL import Image
        path = self.root/'image.png'
        Image.new('RGB', (32, 24), (80, 100, 120)).save(path)
        report = inspect_output(path)
        self.assertTrue(report['verified'])
        self.assertEqual((report['width'], report['height']), (32, 24))
        self.assertEqual(report['visual_quality'], 'not_reviewed')

    def test_nonempty_corrupt_image_is_not_verified(self):
        path = self.root/'image.png'
        path.write_bytes(b'not a decodable picture')
        report = inspect_output(path)
        self.assertFalse(report['verified'])
        self.assertEqual(report['status'], 'failed')

    def test_empty_and_unsupported_files_fail_explicitly(self):
        path = self.root/'output.unknown'
        path.touch()
        self.assertEqual(inspect_output(path)['status'], 'failed')
        path.write_bytes(b'nonempty unknown format')
        self.assertEqual(inspect_output(path)['status'], 'unavailable')
        self.assertFalse(inspect_output(path)['verified'])

    def test_video_tools_missing_does_not_certify_output(self):
        path = self.root/'video.mp4'
        path.write_bytes(b'nonempty')
        with patch('local_app.media_validation.shutil.which', return_value=None):
            report = inspect_output(path)
        self.assertEqual(report['status'], 'unavailable')
        self.assertFalse(report['verified'])

    @unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'Existing FFmpeg/FFprobe required')
    def test_real_video_decoder_checks_synthetic_clip_and_rejects_corruption(self):
        path = self.root/'video.mp4'
        subprocess.run([shutil.which('ffmpeg'), '-nostdin', '-v', 'error', '-f', 'lavfi',
                        '-i', 'color=c=blue:s=32x24:r=5:d=1', '-c:v', 'mpeg4', str(path)],
                       capture_output=True, check=True, timeout=30)
        report = inspect_output(path)
        self.assertTrue(report['verified'], report)
        self.assertEqual((report['width'], report['height']), (32, 24))
        self.assertAlmostEqual(report['duration_seconds'], 1, places=1)
        path.write_bytes(b'not a video stream')
        self.assertFalse(inspect_output(path)['verified'])
