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
    from local_app import server, web_business_map, web_hybrid, integrations_cli, web_sales_source, web_sales_orders
    from email.message import Message

    source=web_business_map._result({"name":"Atelier des Tilleuls · démo","lat":45.76,"lon":4.84,
        "website":"https://atelier-demo.example/","osm_id":"demo/55","source":"google","category":"florist","city":"Lyon","phone":"04 00 00 00 00"})
    def draft(store,pid,*args,**kwargs):
        time.sleep(2)
        style="body{background:#183d38;color:#fff;font:22px Georgia;padding:9vw}a{color:#f1d8ad}"
        store.write_files(pid,{"index.html":"<!doctype html><html lang='fr'><head><meta name='viewport' content='width=device-width'><title>Les Tilleuls</title><link rel='stylesheet' href='styles.css'></head><body><main><h1>Les Tilleuls</h1><p>Maquette privée de recette</p><a href='bouquets.html'>Découvrir les bouquets</a></main></body></html>",
            "bouquets.html":"<!doctype html><html lang='fr'><title>Bouquets</title><main><h1>Nos bouquets</h1></main></html>","styles.css":style})
        attack="""<script>
window.securityProbe=(async()=>{
 const base=location.protocol+'//127.0.0.1:'+location.port;
 const results=[];
 for(const path of ['/api/web/crm/overview','/api/web/project?id='+location.hostname.slice(8,-10),'/api/web/invoice/file?number=FORMA-2026-00001']){
  try{const r=await fetch(base+path);results.push(await r.text())}catch{results.push('blocked')}
 }
 try{parent.document.body.dataset.compromised='yes';results.push('escaped')}catch{results.push('isolated')}
 for(const path of ['/api/web/crm/client/upsert','/api/web/project/pro/authorize']){
  try{await fetch(base+path,{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});results.push('write-readable')}catch{results.push('write-blocked')}
  try{await fetch(base+path,{method:'POST',headers:{'Content-Type':'text/plain'},body:'{}'});results.push('simple-write-readable')}catch{results.push('simple-write-blocked')}
 }
 return results;
})();</script>"""
        root=store.project_dir(pid)/"site"/"index.html"
        root.write_text(root.read_text().replace("</body>",attack+"</body>"))
        store.snapshot(pid,"Recette de génération")
        return {"summary":"Deux pages de présentation.","quality":{"ok":True}}
    def official_page(url):
        headers=Message()
        if url.endswith("robots.txt"):
            return 404,headers,b""
        headers["Content-Type"]="text/html; charset=utf-8"
        return 200,headers,"<h1>Atelier des Tilleuls</h1><h2>Fleurs pour les entreprises</h2>".encode()
    signature_polls=0
    def signature_provider(request):
        # A deterministic provider double, never an authenticated sandbox call.
        global signature_polls
        ref="d"*40
        if request.full_url=="https://api.hellosign.com/v3/signature_request/send":
            return {"signature_request":{"signature_request_id":ref}}
        if request.full_url=="https://api.hellosign.com/v3/signature_request/"+ref:
            import hashlib
            from local_app import web_crm
            root=server.LOCALAIWEB_DATA/"crm"
            quote=web_crm._read(root)["quotes"][-1]
            signature_polls+=1
            return {"signature_request":{"signature_request_id":ref,"is_complete":False,
                "is_declined":signature_polls>1,"has_error":False,
                "metadata":{"sales_mode":"test","quote_number":quote["quote_number"],
                    "quote_sha256":hashlib.sha256(web_crm.quote_file(root,quote["quote_number"]).read_bytes()).hexdigest()},
                "signatures":[{"signer_email_address":quote["customer"]["email"],"status_code":"awaiting_signature"}]}}
        raise AssertionError("Unexpected external provider request")
    http=ThreadingHTTPServer(("127.0.0.1",0),server.Handler)
    server.PORT=http.server_port
    thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start()
    try:
        with patch.dict(web_sales_orders._private_config,{"DROPBOX_SIGN_API_KEY":"fixture-key","LOCALAI_SALES_APPROVAL_CODE":"fixture-operator-55"}),patch.dict(os.environ,{"LOCALAI_SALES_MODE":"test"}),patch.object(web_sales_orders,"_request",signature_provider),patch.object(web_sales_source,"_read",official_page),patch.object(web_hybrid,"build_with_agent",draft),patch.object(integrations_cli,"coding_agent_status",
                return_value={"codex":{"installed":True,"ready":True}}):
            subprocess.run(["node",str(ROOT/"scripts/review_sales_55.cjs")],cwd=ROOT,check=True,
                env=dict(os.environ,SALES_TEST_URL=f"http://127.0.0.1:{http.server_port}",TEST_SELECTION=source["selection_token"]))
    finally:
        http.shutdown();http.server_close();thread.join()
