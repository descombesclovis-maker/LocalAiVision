"""Wait for the local backend and frontend before opening the browser."""
import sys
import time
from urllib.error import URLError
from urllib.request import urlopen


def wait_until_ready(urls, timeout=45, opener=urlopen, clock=time.monotonic, sleep=time.sleep):
    deadline = clock() + timeout
    remaining = set(urls)
    while remaining and clock() < deadline:
        for url in list(remaining):
            try:
                with opener(url, timeout=2) as response:
                    if response.status == 200:
                        remaining.remove(url)
            except (OSError, URLError):
                pass
        if remaining:
            sleep(0.5)
    return not remaining


def main():
    if len(sys.argv) != 3 or not all(p.isdigit() and 0 < int(p) < 65536 for p in sys.argv[1:]):
        print("Deux ports locaux valides sont requis.", file=sys.stderr)
        return 2
    backend, frontend = sys.argv[1:]
    if not wait_until_ready([f"http://127.0.0.1:{backend}/api/", f"http://127.0.0.1:{frontend}/"]):
        print("Le backend ou l'interface ne repond pas. Consultez leurs fenetres de demarrage.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
