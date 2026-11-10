"""Guard the new Windows installation and launcher without changing existing services."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("las_wait_for_server", ROOT / "scripts/wait_for_server.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_new_installer_has_locked_independent_dependencies_and_private_defaults():
    text = (ROOT / "scripts/build-parallel-edition.ps1").read_text(encoding="utf-8")
    for expected in ("materialize_kit.py", "--require-hashes", "--only-binary=:all:",
                     "--frozen-lockfile", "check_new_db.py", "wait_for_server.py",
                     "--host 127.0.0.1", "--strictPort", "LAS_SESSION_COOKIE", 'set "LAS_VITE_EXPOSE="'):
        assert expected in text
    for forbidden in ("New-Item -ItemType Junction", "CopyVenvFrom", "CopyNodeModulesFrom", "ollama pull", "CORS_ORIGINS=*"):
        assert forbidden not in text
    assert 'las_v2f_$nonce' in text


class Clock:
    now = 0.0

    def clock(self):
        return self.now

    def sleep(self, n):
        self.now += n


class Response:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *_):
        pass


def test_wait_retries_until_both_servers_are_ready():
    clock = Clock()
    calls = {}

    def opener(url, timeout):
        calls[url] = calls.get(url, 0) + 1
        if calls[url] == 1:
            raise OSError("not ready")
        return Response()

    assert module.wait_until_ready(["backend", "frontend"], timeout=3, opener=opener, clock=clock.clock, sleep=clock.sleep)
    assert calls == {"backend": 2, "frontend": 2}


def test_wait_fails_when_a_server_never_starts():
    clock = Clock()

    def opener(url, timeout):
        raise OSError("down")

    assert not module.wait_until_ready(["backend"], timeout=1, opener=opener, clock=clock.clock, sleep=clock.sleep)
