"""Optional visual browser inspection for LocalAiWeb's agentic build-review-repair loop.

Headless Playwright is used only when explicitly installed on the user's PC.
Screenshots are stored in the isolated project's internal QA folder, which is
excluded from exports and GitHub publication.
"""
from __future__ import annotations
import contextlib
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit
import threading
import os
import shutil
import subprocess
import tempfile


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        return

    def do_GET(self):
        # Never expose .env files or private project internals to generated
        # JavaScript during the preview inspection.
        parts = Path(unquote(urlsplit(self.path).path)).parts
        if any(part.startswith(".") and part not in (".", "..") for part in parts):
            self.send_error(404)
            return
        if "node_modules" in parts or ".git" in parts:
            self.send_error(404)
            return
        return super().do_GET()


@contextlib.contextmanager
def serve(root: Path):
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=str(root)))
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        yield "http://127.0.0.1:%d/" % server.server_port
    finally:
        server.shutdown()
        worker.join(timeout=5)
        server.server_close()


def review(site_dir, *, build=None):
    """Read actual browser behavior, screenshots and mobile overflow.

    'unavailable' is not a passing visual test. The coding agent may still
    complete a build, but the UI must not promise verified visual quality.
    """
    site = Path(site_dir)
    root = Path((build or {}).get("output_dir") or site).resolve()
    if not (root / "index.html").is_file():
        return {"status": "failed", "issues": ["Aucun index.html dans l'aperçu construit."],
                "screenshots": [], "reviewed": False}
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return _browser_binary_review(root, site)
    folder = site / ".localaiweb-qa"
    folder.mkdir(parents=True, exist_ok=True)
    results, issues = [], []
    sizes = [("ordinateur", 1440, 900), ("tablette", 820, 1050), ("telephone", 390, 844)]
    try:
        with serve(root) as url, sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                for label, width, height in sizes:
                    page = browser.new_page(viewport={"width": width, "height": height},
                                            device_scale_factor=1)
                    errors = []
                    page.on("pageerror", lambda error: errors.append(str(error)[:320]))
                    try:
                        page.goto(url, wait_until="domcontentloaded", timeout=25000)
                        page.wait_for_timeout(1100)
                        dimensions = page.evaluate("""() => ({
                            text: (document.body?.innerText||'').trim().length,
                            width: document.documentElement.scrollWidth,
                            viewport: window.innerWidth,
                            headings: document.querySelectorAll('h1').length
                        })""")
                        screenshot = folder / (label + ".png")
                        page.screenshot(path=str(screenshot), full_page=True, animations="disabled", timeout=20000)
                        results.append({"mode": label, "path": ".localaiweb-qa/" + screenshot.name,
                                        "text_length": dimensions["text"],
                                        "page_errors": errors[:4]})
                        if dimensions["text"] < 70:
                            issues.append(label + ": page vide ou trop peu de texte visible.")
                        if dimensions["width"] > dimensions["viewport"] + 12:
                            issues.append(label + ": défilement horizontal, mise en page débordante.")
                        if errors:
                            issues.append(label + ": erreurs JavaScript : " + "; ".join(errors[:2]))
                    finally:
                        page.close()
            finally:
                browser.close()
    except Exception as exc:
        fallback = _browser_binary_review(root, site)
        if fallback["reviewed"]:
            return fallback
        return {"status": "unavailable", "issues": [],
                "detail": "Navigateur Playwright indisponible : " + str(exc)[:200],
                "screenshots": [], "reviewed": False}
    return {"status": "passed" if not issues else "failed", "issues": issues,
            "screenshots": results, "reviewed": True}


def _find_chromium():
    for name in ("msedge.exe", "chrome.exe", "chromium.exe", "msedge", "google-chrome", "chromium"):
        value = shutil.which(name)
        if value:
            return value
    if os.name == "nt":
        bases = [os.getenv("PROGRAMFILES", ""), os.getenv("PROGRAMFILES(X86)", ""),
                 os.getenv("LOCALAPPDATA", "")]
        for base in bases:
            if not base:
                continue
            for rel in ("Microsoft/Edge/Application/msedge.exe",
                        "Google/Chrome/Application/chrome.exe"):
                path = Path(base) / rel
                if path.is_file():
                    return str(path)
    return None


def _browser_binary_review(root, site):
    """Windows Edge/Chrome screenshots without installing Python Playwright.

    This is screenshot-only, not a successful functional browser test.
    """
    binary = _find_chromium()
    if not binary:
        return {"status": "unavailable", "issues": [],
                "detail": "Ni Playwright ni Edge/Chrome headless n'est disponible.",
                "screenshots": [], "reviewed": False}
    folder = site / ".localaiweb-qa"
    folder.mkdir(parents=True, exist_ok=True)
    images = []
    try:
        with serve(root) as url, tempfile.TemporaryDirectory(prefix="localaiweb-browser-") as profile:
            for name, width, height in (("ordinateur", 1440, 900),
                                         ("tablette", 820, 1050),
                                         ("telephone", 390, 844)):
                dest = folder / (name + ".png")
                if dest.exists():
                    dest.unlink()
                args = [binary, "--headless=new", "--disable-extensions",
                        "--no-first-run", "--no-default-browser-check",
                        "--hide-scrollbars", "--virtual-time-budget=2200",
                        "--user-data-dir=" + profile,
                        "--window-size=%d,%d" % (width, height),
                        "--screenshot=" + str(dest), url]
                result = subprocess.run(args, capture_output=True, timeout=45,
                                        check=False, text=True, errors="replace")
                if result.returncode or not dest.is_file() or dest.stat().st_size < 512:
                    raise RuntimeError((result.stderr or result.stdout or "Capture introuvable")[-300:])
                images.append({"mode": name, "path": ".localaiweb-qa/" + dest.name,
                               "text_length": None, "page_errors": []})
        return {"status": "captured", "issues": [],
                "detail": "Captures Edge/Chrome disponibles ; analyse visuelle déléguée à l'agent.",
                "screenshots": images, "reviewed": True}
    except Exception as exc:
        return {"status": "unavailable", "issues": [],
                "detail": "Capture navigateur impossible : " + str(exc)[:230],
                "screenshots": [], "reviewed": False}


def creative_review_prompt(request, browser):
    """Prompt an image-capable coding agent to inspect actual screenshots."""
    entries = browser.get("screenshots") or []
    references = "\n".join(
        "- " + row["mode"] + ": " + row["path"] for row in entries
    )
    errors = "\n".join("- " + issue for issue in browser.get("issues") or [])
    return (
        "QUALITY GATE: inspect ALL provided browser screenshots visually using your image-reading "
        "capability, not only the HTML source. The screenshots are local to this website project.\n"
        + references + "\n"
        "Judge whether the design is visually coherent, modern, professional, appropriately "
        "art-directed, true to the user's requested brand palette, with credible images, whitespace, "
        "legible text, and distinct hierarchy. If it looks like a plain old forum, an unfinished "
        "wireframe, an empty landing page or unstyled HTML, FIX IT. Preserve requested functions. "
        "For 3D requests, verify the scene is visible; do not invent absent model assets. "
        "Existing browser issues:\n" + (errors or "- none detected structurally") +
        "\nORIGINAL USER REQUEST:\n" + request
    )
