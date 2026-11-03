"""Exercise the real local application with a deterministic generation adapter."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
from unittest.mock import patch
from http.server import ThreadingHTTPServer

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
with tempfile.TemporaryDirectory() as work:
    os.environ["LOCALVISIONAI_DATA"]=work
    os.environ["LOCALVISIONAI_SKIP_SETUP"]="1"
    from local_app import server, web_business_map, web_hybrid, integrations_cli

    source=web_business_map._result({"name":"Atelier des Tilleuls · démo","lat":45.76,"lon":4.84,
        "osm_id":"demo/55","source":"google","category":"florist","city":"Lyon","phone":"04 00 00 00 00"})
    def draft(store,pid,*args,**kwargs):
        time.sleep(2)
        style="body{background:#183d38;color:#fff;font:22px Georgia;padding:9vw}a{color:#f1d8ad}"
        store.write_files(pid,{"index.html":"<!doctype html><html lang='fr'><head><meta name='viewport' content='width=device-width'><title>Les Tilleuls</title><link rel='stylesheet' href='styles.css'></head><body><main><h1>Les Tilleuls</h1><p>Maquette privée de recette</p><a href='bouquets.html'>Découvrir les bouquets</a></main></body></html>",
            "bouquets.html":"<!doctype html><html lang='fr'><title>Bouquets</title><main><h1>Nos bouquets</h1></main></html>","styles.css":style})
        store.snapshot(pid,"Recette de génération")
        return {"summary":"Deux pages de présentation.","quality":{"ok":True}}
    http=ThreadingHTTPServer(("127.0.0.1",0),server.Handler)
    server.PORT=http.server_port
    thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start()
    try:
        with patch.object(web_hybrid,"build_with_agent",draft),patch.object(integrations_cli,"coding_agent_status",
                return_value={"codex":{"installed":True,"ready":True}}):
            subprocess.run(["node",str(ROOT/"scripts/review_sales_55.cjs")],cwd=ROOT,check=True,
                env=dict(os.environ,SALES_TEST_URL=f"http://127.0.0.1:{http.server_port}",TEST_SELECTION=source["selection_token"]))
    finally:
        http.shutdown();http.server_close();thread.join()
