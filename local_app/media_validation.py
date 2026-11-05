"""Technical checks for PUBLIC benchmark outputs; no aesthetic certification.

Uses existing Pillow/FFmpeg installations only. Missing tools leave validation
unavailable rather than certifying a nonempty, potentially corrupt file.
"""
import json
import math
import shutil
import subprocess
from pathlib import Path


def inspect_output(path, *, timeout=120):
    path = Path(path)
    report = {'status': 'failed', 'verified': False,
              'visual_quality': 'not_reviewed', 'size_bytes': None}
    try:
        report['size_bytes'] = path.stat().st_size
        if not report['size_bytes']:
            raise ValueError('Sortie vide.')
        if path.suffix.lower() in ('.png', '.jpg', '.jpeg', '.webp', '.gif', '.bmp', '.tif', '.tiff'):
            try:
                from PIL import Image
            except ImportError:
                return {**report, 'status': 'unavailable', 'error': 'Pillow absent ; décodage image non exécuté.'}
            with Image.open(path) as image:
                image.verify()
            # verify checks containers; load also forces real pixel decoding.
            with Image.open(path) as image:
                width, height = image.size
                frames = getattr(image, 'n_frames', 1)
                for index in range(frames):
                    image.seek(index)
                    image.load()
            if width <= 0 or height <= 0:
                raise ValueError('Dimensions image invalides.')
            report.update(kind='image', width=width, height=height, decoded_frames=frames)
        elif path.suffix.lower() in ('.mp4', '.webm', '.mov', '.mkv', '.avi'):
            ffprobe, ffmpeg = shutil.which('ffprobe'), shutil.which('ffmpeg')
            if not ffprobe or not ffmpeg:
                return {**report, 'status': 'unavailable', 'error': 'FFprobe/FFmpeg absents ; décodage vidéo non exécuté.'}
            probe = subprocess.run([ffprobe, '-v', 'error', '-select_streams', 'v:0',
                                    '-show_entries', 'stream=width,height,avg_frame_rate,duration:format=duration',
                                    '-of', 'json', str(path)], capture_output=True, text=True,
                                   timeout=timeout, check=True)
            metadata = json.loads(probe.stdout)
            streams = metadata.get('streams') or []
            if not streams:
                raise ValueError('Aucune piste vidéo.')
            stream = streams[0]
            width, height = int(stream['width']), int(stream['height'])
            duration = float(stream.get('duration') or metadata.get('format', {}).get('duration') or 0)
            if width <= 0 or height <= 0 or not math.isfinite(duration) or duration <= 0:
                raise ValueError('Dimensions ou durée vidéo invalides.')
            # Probe alone accepts some truncated files. Decode all video frames,
            # abort on an actual decoder error, never synthesize/repair frames.
            subprocess.run([ffmpeg, '-nostdin', '-v', 'error', '-xerror', '-i', str(path),
                            '-map', '0:v:0', '-an', '-f', 'null', '-'],
                           capture_output=True, timeout=timeout, check=True)
            report.update(kind='video', width=width, height=height, duration_seconds=duration,
                          frame_rate=stream.get('avg_frame_rate'), full_decode=True)
        else:
            return {**report, 'status': 'unavailable', 'error': 'Format sans décodeur de validation.'}
        report.update(status='passed', verified=True)
    except (OSError, ValueError, KeyError, EOFError, subprocess.SubprocessError) as exc:
        # Keep local paths and decoder stderr out of reusable benchmark receipts.
        report['error'] = 'Décodage technique impossible : ' + type(exc).__name__
    return report
