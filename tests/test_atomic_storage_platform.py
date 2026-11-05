import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from local_app.atomic_storage import atomic_copy


class AtomicStoragePlatformTests(unittest.TestCase):
    @unittest.skipIf(os.name=='nt','Windows tests exercise the real writable-fsync requirement directly.')
    def test_windows_like_fsync_rejects_readonly_descriptor(self):
        import fcntl
        real_fsync=os.fsync
        def windows_like_fsync(fd):
            if not stat.S_ISDIR(os.fstat(fd).st_mode) and fcntl.fcntl(fd,fcntl.F_GETFL)&os.O_ACCMODE==os.O_RDONLY:
                raise OSError(9,'Bad file descriptor (Windows read-only fsync behavior)')
            return real_fsync(fd)
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp)/'source';target=Path(temp)/'target'
            source.write_bytes(b'new contents');target.write_bytes(b'previous contents')
            with patch('local_app.atomic_storage.os.fsync',side_effect=windows_like_fsync):
                atomic_copy(source,target)
            self.assertEqual(target.read_bytes(),b'new contents')
            self.assertEqual(source.read_bytes(),b'new contents')
