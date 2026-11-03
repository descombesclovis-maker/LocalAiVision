"""Open the interface first; engines install independently in the background."""
import json
import multiprocessing
import os
from pathlib import Path
import sys
import threading
import time
import traceback
import webbrowser
from urllib.request import urlopen

ROOT = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent.parent))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
DATA = Path(os.environ.get('LOCALVISIONAI_DATA', str(Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'LocalVisionAI')))
os.environ['LOCALVISIONAI_DATA'] = str(DATA)
URL = 'http://127.0.0.1:3000'


def probe():
    try:
        with urlopen(URL + '/api/ping', timeout=1) as r:
            return json.load(r)
    except Exception:
        return None


def running_instance_state(existing, expected):
    """Identify the exact active build, not only its shared semantic version."""
    if not isinstance(existing, dict) or existing.get("app") != "LocalVisionAI":
        return "none"
    for field in ("version", "build_tag"):
        if str(existing.get(field) or "") != str(expected.get(field) or ""):
            return "different"
    return "same"


def open_in_browser():
    """Keep the server alive when WebView2 is absent or browser mode is requested."""
    url = URL + "/studio"
    print("Opening LocalAI Studio in browser:", url, flush=True)
    if not webbrowser.open(url, new=2):
        show_error("Le navigateur ne s'est pas ouvert automatiquement.\n\n"
                   "Ouvre manuellement : " + url)
    if os.name == "nt":
        import ctypes
        ctypes.windll.user32.MessageBoxW(
            0, "LocalAI Studio fonctionne dans ton navigateur.\n"
               "Adresse : " + url + "\n\n"
               "Garde cette fenêtre ouverte pendant l'utilisation. "
               "Clique sur OK pour arrêter le serveur local.",
            "LocalAI Studio — navigateur", 0x40)
    else:
        while True:
            time.sleep(1)


def show_error(message):
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, message, 'LocalVisionAI', 0x10)
    except Exception:
        print(message)


def main():
    multiprocessing.freeze_support()
    logs = DATA / 'logs'
    logs.mkdir(parents=True, exist_ok=True)
    log = (logs / 'startup.log').open('a', encoding='utf-8', buffering=1)
    sys.stdout = sys.stderr = log
    print('\n=== LocalVisionAI ===', flush=True)
    httpd = None
    try:
        from local_app import server
        current = server.build_info()
        print("Executable:", sys.executable, "Build:", current.get("build_tag"),
              "Version:", current.get("version"), flush=True)
        existing = probe()
        state = running_instance_state(existing, current)
        if state == "different":
            raise RuntimeError(
                "Une autre version de LocalAI Studio utilise déjà le port 3000.\n\n"
                "Build déjà actif : " + str(existing.get("build_tag") or "inconnu") +
                " (version " + str(existing.get("version") or "?") + ")\n"
                "Build demandé : " + str(current.get("build_tag") or "inconnu") +
                " (version " + str(current.get("version") or "?") + ")\n\n"
                "Ferme l'ancien LocalVisionAI.exe dans le Gestionnaire des tâches, "
                "puis relance cette version. Tes projets restent conservés dans "
                "%LOCALAPPDATA%\\LocalVisionAI.")
        if state == "same":
            print("An identical build is already active; opening Studio in browser.", flush=True)
            if not webbrowser.open(URL + "/studio", new=2):
                show_error("Le navigateur ne s'est pas ouvert. Ouvre " + URL + "/studio")
            else:
                show_error("LocalVisionAI est déjà ouvert.\n\n"
                           "Le même build fonctionne sur ce PC ; sa page Studio "
                           "vient de s'ouvrir dans ton navigateur.")
            return
        else:
            try:
                httpd = server.ThreadingHTTPServer((server.HOST, server.PORT), server.Handler)
            except OSError as exc:
                raise RuntimeError('Le port 3000 est occupé. Ferme l’ancienne instance de LocalVisionAI ou le programme qui utilise ce port.') from exc
            threading.Thread(target=httpd.serve_forever, daemon=True).start()
            if os.environ.get('LOCALVISIONAI_SKIP_SETUP') != '1':
                server.start_setup()
            # In packaged Windows versions the PC can update itself while
            # this server stays running, with no desktop interaction.
            server.start_auto_updates()
        # CI health probe exercises the packaged PyInstaller binary (including
        # extraction/loading of python311.dll) without opening a GUI window.
        if os.environ.get('LOCALVISIONAI_UPDATE_SMOKE') == '1':
            print('Smoke test server ready:', URL, flush=True)
            while True:
                time.sleep(0.25)
        try:
            if os.environ.get("LOCALVISIONAI_BROWSER_ONLY") == "1":
                open_in_browser()
            else:
                import webview
                title = "LocalAI Studio · " + str(current.get("build_tag") or "source")
                webview.create_window(title, URL + "/studio", width=1440, height=920,
                                      min_size=(900, 650), background_color="#090909")
                webview.start(debug=False, private_mode=False, storage_path=str(DATA / "webview"))
        except Exception:
            # WebView2 might be absent or fail after starting the HTTP server.
            traceback.print_exc()
            open_in_browser()
    except KeyboardInterrupt:
        pass
    except Exception as exc:
        traceback.print_exc()
        show_error(str(exc) + '\n\nJournal : ' + str(logs / 'startup.log'))
    finally:
        if httpd:
            httpd.shutdown()
            httpd.server_close()
            server.stop_engines()


if __name__ == '__main__':
    main()
