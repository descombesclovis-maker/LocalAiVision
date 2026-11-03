"""Local, checksum-verified presentation photographs, stored as text-safe WebP.

This bundle is independent from user projects and requires no network at runtime.
"""
import base64
import hashlib
import json
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=4)
def photograph(web_root, name):
    root = Path(web_root) / 'presentation'
    manifest = json.loads((root / 'manifest.json').read_text(encoding='utf-8'))
    if name not in manifest:
        raise FileNotFoundError('Photographie de présentation inconnue.')
    raw = base64.b64decode((root / (name + '.base64')).read_text().strip(), validate=True)
    if hashlib.sha256(raw).hexdigest() != manifest[name]['sha256']:
        raise ValueError('Photographie de présentation endommagée.')
    return raw
