"""Bounded, operator-initiated reading of a prospect's confirmed public website."""
from datetime import datetime, timezone
from html.parser import HTMLParser
import http.client
import ipaddress
import re
import socket
import ssl
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser

AGENT = "LocalAiWeb-CallSheet"
_LIMIT = 384_000
_DIRECTORIES = ("google.com","google.fr","goo.gl","facebook.com","fb.com","instagram.com",
                "linkedin.com","tiktok.com","youtube.com","maps.app.goo.gl")


class PublicHeadings(HTMLParser):
    def __init__(self):
        super().__init__()
        self.skip = None
        self.depth = 0
        self.heading = None
        self.headings = []

    def handle_starttag(self, tag, attrs):
        if self.skip:
            if tag==self.skip:self.depth+=1
            return
        if tag in ("area","base","br","col","embed","hr","img","input","link","meta","source","track","wbr"):
            return
        attrs=dict(attrs)
        if tag in ("script","style","noscript","template","svg","nav","footer") or "hidden" in attrs or attrs.get("aria-hidden")=="true":
            self.skip = tag
            self.depth = 1
            return
        if tag in ("h1","h2"):
            self.heading = (tag,[])

    def handle_endtag(self, tag):
        if self.skip:
            if tag == self.skip:
                self.depth-=1
                if not self.depth:self.skip=None
            return
        if self.heading and tag == self.heading[0]:
            label = " ".join(" ".join(self.heading[1]).split())
            if (5<=len(label)<=120 and label not in self.headings and label.casefold() not in ("accueil","bienvenue","nos services","contact","notre équipe") and
                    not re.search(r"cookie|newsletter|confidentialité|mentions légales|@|https?://", label, re.I)):
                self.headings.append(label)
            self.heading = None

    def handle_data(self,data):
        if self.heading and not self.skip:
            self.heading[1].append(data)


def _url(raw):
    url=urlsplit(str(raw or "").strip())
    host=(url.hostname or "").encode("idna").decode("ascii").lower()
    if (url.scheme!="https" or url.username or url.password or url.port not in (443,None)
        or not re.fullmatch(r"(?:[a-z0-9-]+\.)+[a-z]{2,63}",host)
        or any(host==d or host.endswith("."+d) for d in _DIRECTORIES)):
        raise ValueError("Une page HTTPS du site officiel du commerce est requise.")
    # Only request the public path, never tokens, query strings or fragments.
    return urlunsplit(("https",host,url.path or "/","",""))


def _read(raw):
    url=urlsplit(raw)
    addresses=socket.getaddrinfo(url.hostname,443,type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
        raise ValueError("Le site doit résoudre exclusivement vers des adresses publiques.")
    with socket.create_connection((addresses[0][4][0],443),timeout=6) as connection:
        with ssl.create_default_context().wrap_socket(connection,server_hostname=url.hostname) as tls:
            from urllib.parse import quote
            path=quote(url.path or "/",safe="/%:@!$&'()*+,;=-._~")
            tls.sendall((f"GET {path} HTTP/1.1\r\nHost: {url.hostname}\r\nUser-Agent: {AGENT}\r\nAccept-Encoding: identity\r\nConnection: close\r\n\r\n").encode("ascii"))
            reply=http.client.HTTPResponse(tls)
            reply.begin()
            content=reply.read(_LIMIT+1)
            if len(content)>_LIMIT:
                raise ValueError("Page trop volumineuse pour une vérification ciblée.")
            return reply.status,reply.headers,content


def scan(raw):
    origin=_url(raw)
    current=origin
    for _ in range(3):
        host=urlsplit(current).hostname
        if host.removeprefix("www.")!=urlsplit(origin).hostname.removeprefix("www."):
            raise ValueError("Redirection vers un autre site : vérifier l’identité avant utilisation.")
        robots_url="https://"+host+"/robots.txt"
        code,_,raw_rules=_read(robots_url)
        if code==200:
            rules=RobotFileParser(robots_url)
            rules.parse(raw_rules.decode("utf-8","replace").splitlines())
            if not rules.can_fetch(AGENT,current):
                raise ValueError("La page exclut cette consultation automatisée.")
        elif code not in (404,410):
            raise ValueError("Autorisation de lecture automatique non confirmée.")
        status,headers,data=_read(current)
        if status in (301,302,303,307,308):
            current=_url(urljoin(current,headers.get("Location","")))
            continue
        if status!=200 or headers.get_content_type()!="text/html":
            raise ValueError("La page publique ne fournit pas de contenu HTML vérifiable.")
        parser=PublicHeadings()
        try:
            parser.feed(data.decode(headers.get_content_charset() or "utf-8","replace"))
        except LookupError:
            raise ValueError("Encodage de la page non pris en charge.") from None
        if not parser.headings:
            raise ValueError("Aucun intitulé public exploitable. Utilise la maquette ou une information confirmée.")
        return {"url":current,"day":datetime.now(timezone.utc).date().isoformat(),"headings":parser.headings[:8]}
    raise ValueError("Trop de redirections : aucun intitulé retenu.")
