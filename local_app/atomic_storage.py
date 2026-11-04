"""Durable same-directory atomic file replacement (no new dependencies)."""
import os
import tempfile
from pathlib import Path


def atomic_write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, pending = tempfile.mkstemp(prefix='.' + path.name + '-', suffix='.pending', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(pending, path)
        # Persist the directory entry where supported; Windows has no O_DIRECTORY.
        if hasattr(os, 'O_DIRECTORY'):
            directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
    finally:
        if os.path.exists(pending):
            os.unlink(pending)
