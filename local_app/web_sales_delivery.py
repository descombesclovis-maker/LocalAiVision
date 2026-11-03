"""Read-only verification of the linked deployment, domain and public HTTPS endpoint."""
import http.client
import ipaddress
import json
import socket
import ssl
from urllib.parse import quote, urlencode, urlsplit
from urllib.request import Request

from local_app.web_sales_orders import _request, setting


def _https(host):
    # Pin the public address we inspected. Do not follow redirects to private hosts.
    addresses=socket.getaddrinfo(host,443,type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
        raise ValueError("Le domaine doit résoudre exclusivement vers des adresses publiques.")
    with socket.create_connection((addresses[0][4][0],443),timeout=8) as conn:
        with ssl.create_default_context().wrap_socket(conn,server_hostname=host) as tls:
            tls.sendall(("GET / HTTP/1.1\r\nHost: "+host+"\r\nConnection: close\r\n\r\n").encode("ascii"))
            response=http.client.HTTPResponse(tls)
            response.begin()
            if not 200<=response.status<300:
                raise ValueError("La page d’accueil HTTPS n’a pas répondu par un succès.")
            return {"http":response.status,"certificate_until":tls.getpeercert().get("notAfter")}


def verify(store,pid):
    meta=store.meta(pid)
    deployment=meta.get("deployment") or {}
    live=urlsplit(deployment.get("production_url") or "")
    if live.scheme!="https" or not live.hostname:
        raise ValueError("Aucune publication HTTPS confirmée pour ce projet.")
    config=store.project_dir(pid)/"site"/".vercel"/"project.json"
    token=setting("LOCALAI_VERCEL_READ_TOKEN")
    if not token or not config.is_file():
        raise ValueError("Projet Vercel lié et LOCALAI_VERCEL_READ_TOKEN requis pour la recette.")
    linked=json.loads(config.read_text(encoding="utf-8"))
    def get(path):
        return _request(Request("https://api.vercel.com"+path+"?"+urlencode({"teamId":linked["orgId"]}),
                                headers={"Authorization":"Bearer "+token}))
    def deployment_for(host):
        record=get("/v13/deployments/"+quote(host,safe=""))
        if record.get("projectId")!=linked["projectId"] or record.get("readyState")!="READY" or record.get("target")!="production" or not record.get("id"):
            raise ValueError("Déploiement de production non vérifié pour le projet lié.")
        return record["id"]
    target=deployment_for(live.hostname)
    host=deployment.get("custom_domain") or live.hostname
    if host!=live.hostname:
        domain=get("/v9/projects/"+quote(linked["projectId"],safe="")+"/domains/"+quote(host,safe=""))
        if domain.get("verified") is not True or deployment_for(host)!=target:
            raise ValueError("Domaine ou routage encore en attente de vérification.")
    return {"url":"https://"+host,"deployment_id":target,**_https(host)}


def database_change(store,pid,reference,approved_digest=None):
    """Dry-run or apply the reviewed SQL snapshot to an already linked project."""
    import hashlib
    import re
    import tempfile
    from pathlib import Path
    from local_app import integrations_cli

    site=store.project_dir(pid)/"site"
    folder=site/"supabase"
    if not re.fullmatch(r"[a-z0-9]{20}",str(reference or "")):
        raise ValueError("Référence Supabase attendue.")
    files=sorted((folder/"migrations").glob("*.sql"))
    if not files:
        raise ValueError("Aucune migration SQL à appliquer à ce site.")
    link=folder/".temp"/"project-ref"
    if not link.is_file() or link.read_text().strip()!=reference:
        raise ValueError("Le projet Supabase lié diffère de la cible.")
    cmd=integrations_cli._supabase_cmd()
    if not cmd:
        raise ValueError("Supabase CLI indisponible.")
    with tempfile.TemporaryDirectory() as temp:
        dest=Path(temp)/"supabase"
        digest=hashlib.sha256(reference.encode())
        # The CLI receives an immutable copy. Never follow a generated symlink.
        inputs=[folder/"config.toml",*files,*sorted((folder/".temp").glob("*"))]
        for f in inputs:
            if not f.is_file() or not f.resolve().is_relative_to(site.resolve()) or f.stat().st_size>4_000_000:
                raise ValueError("Fichier de migration ou de liaison non valide.")
            content=f.read_bytes()
            name=f.relative_to(folder).as_posix()
            target=dest/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(content)
            digest.update(name.encode()+b"\0"+hashlib.sha256(content).digest())
        fingerprint=digest.hexdigest()
        if approved_digest is not None and approved_digest!=fingerprint:
            raise ValueError("Les fichiers ou le projet ont changé. Refaire la préparation.")
        args=cmd+["db","push","--linked"]+([] if approved_digest else ["--dry-run"])
        proc=integrations_cli._run(args,cwd=temp,timeout=300)
        if proc.returncode:
            raise RuntimeError("Supabase CLI n’a pas confirmé l’opération. Vérifie l’accès et les migrations dans le projet.")
        return {"reference":reference,"files":[f.name for f in files],"digest":fingerprint,
                "applied":bool(approved_digest)}
