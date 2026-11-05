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


# Synchronize journal recovery with writers in OTHER processes (e.g. a local
# helper and the HTTP server). A live transaction must never be "recovered".
import threading
from contextlib import contextmanager

_held=threading.local()


@contextmanager
def project_lock(project):
    project=Path(project);project.mkdir(parents=True,exist_ok=True)
    key=str(project.resolve())
    held=getattr(_held,'paths',{})
    if key in held:
        held[key]+=1
        try:yield
        finally:held[key]-=1
        return
    stream=(project/'.project-write.lock').open('a+b')
    try:
        if os.name=='nt':
            import msvcrt
            if stream.seek(0,os.SEEK_END)==0:stream.write(b'0');stream.flush()
            stream.seek(0)
            msvcrt.locking(stream.fileno(),msvcrt.LK_LOCK,1)
        else:
            import fcntl
            fcntl.flock(stream.fileno(),fcntl.LOCK_EX)
        held[key]=1;_held.paths=held
        try:yield
        finally:
            held.pop(key,None)
            if os.name=='nt':
                stream.seek(0);msvcrt.locking(stream.fileno(),msvcrt.LK_UNLCK,1)
            else:fcntl.flock(stream.fileno(),fcntl.LOCK_UN)
    finally:stream.close()


def install_file(pending, destination):
    """Install a completed same-directory temporary file without buffering it."""
    pending, destination=Path(pending),Path(destination)
    if pending.parent.resolve()!=destination.parent.resolve():
        raise ValueError('Le fichier temporaire doit être sur le même répertoire.')
    with pending.open('rb') as stream:os.fsync(stream.fileno())
    os.replace(pending,destination)
    if hasattr(os,'O_DIRECTORY'):
        directory=os.open(destination.parent,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(directory)
        finally:os.close(directory)


def atomic_copy(source, destination):
    import shutil
    destination=Path(destination);destination.parent.mkdir(parents=True,exist_ok=True)
    fd,pending=tempfile.mkstemp(prefix='.'+destination.name+'-',suffix='.pending',dir=destination.parent)
    try:
        with os.fdopen(fd,'wb') as target,Path(source).open('rb') as stream:
            shutil.copyfileobj(stream,target,length=1024*1024)
            target.flush();os.fsync(target.fileno())
        install_file(pending,destination)
    finally:
        if os.path.exists(pending):os.unlink(pending)


def file_sha256(path):
    import hashlib
    digest=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):digest.update(chunk)
    return digest.hexdigest()
