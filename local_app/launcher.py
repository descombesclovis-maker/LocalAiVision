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
        existing = probe()
        if existing and existing.get('app') == 'LocalVisionAI':
            if existing.get('version') != server.VERSION:
                raise RuntimeError('Une autre version de LocalVisionAI occupe déjà le port 3000. Ferme cette ancienne version une fois, puis relance celle-ci.')
            # The running instance owns the HTTP server. Opening a second native
            # window would leave it orphaned if the owner is closed first.
            try:
                import ctypes
                ctypes.windll.user32.MessageBoxW(
                    0,
                    'LocalVisionAI est déjà ouvert.\n\nUtilise la fenêtre déjà lancée.',
                    'LocalVisionAI',
                    0x40,
                )
            except Exception:
                pass
            return
        else:
            try:
                httpd = server.ThreadingHTTPServer((server.HOST, server.PORT), server.Handler)
            except OSError as exc:
                raise RuntimeError('Le port 3000 est occupé. Ferme l’ancienne instance de LocalVisionAI ou le programme qui utilise ce port.') from exc
            threading.Thread(target=httpd.serve_forever, daemon=True).start()
            if os.environ.get('LOCALVISIONAI_SKIP_SETUP') != '1':
                server.start_setup()
        try:
            import webview
            webview.create_window('LocalVisionAI', URL, width=1440, height=920,
                                  min_size=(900, 650), background_color='#090909')
            webview.start(debug=False, private_mode=False, storage_path=str(DATA / 'webview'))
        except Exception:
            # A missing WebView2 runtime must not make the entire app unusable.
            traceback.print_exc()
            webbrowser.open(URL)
            if httpd:
                print('Interface ouverte dans le navigateur. Fermer ce processus pour arrêter le serveur.', flush=True)
                if os.name == 'nt':
                    import ctypes
                    ctypes.windll.user32.MessageBoxW(0, 'L’interface est ouverte dans ton navigateur.\n\nGarde cette boîte ouverte pendant l’utilisation. Clique sur OK pour arrêter LocalVisionAI.', 'LocalVisionAI — mode navigateur', 0x40)
                else:
                    while True:
                        time.sleep(1)
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
