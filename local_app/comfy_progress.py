"""Real ComfyUI sampler progress and first *actual* preview via its WebSocket.

No estimated overall percent: "value/max" is scoped to the CURRENT sampling
node. The media output is complete only when /history confirms file creation.
A disconnected socket reports unavailable, not fictitious progress.
"""
from __future__ import annotations
import base64
import json
import os
import socket
import ssl
import struct
import threading
import time
import uuid
from urllib.parse import urlparse

CLIENT_ID = "localai-studio-" + uuid.uuid4().hex
_lock = threading.RLock()
_jobs = {}
_socket_thread = None
_endpoint = ""
_preview = {}

def register(prompt_id, kind="video"):
    key = str(prompt_id or "")
    if not key:
        return
    with _lock:
        _jobs[key] = {"prompt_id": key, "kind": kind, "state": "queued",
                      "started_at": time.time(), "step": 0,
                      "max_steps": 0, "node": None, "percent": None}

def update(prompt_id, *, value=None, maximum=None, node=None, state=None):
    with _lock:
        job = _jobs.get(str(prompt_id or ""))
        if job is None:
            return
        if state:
            job["state"] = state
        if node is not None and node != job["node"]:
            job.update(node=node,step=0,max_steps=0,percent=None)
        if value is not None and maximum is not None:
            try:
                step, total = int(value), int(maximum)
                if total>0 and 0<=step<=total:
                    job.update(step=step,max_steps=total,
                               percent=round(step*100/total))
            except (TypeError,ValueError,OverflowError):
                pass

def mark(prompt_id, state):
    with _lock:
        if prompt_id in _jobs:
            _jobs[prompt_id]["state"] = state
            if state in ("done","cancelled","error"):
                _preview.pop(prompt_id,None)
                if state=="done":
                    _jobs[prompt_id]["percent"]=100
                _jobs[prompt_id]["finished_at"]=time.time()

def status(prompt_id):
    with _lock:
        row = _jobs.get(str(prompt_id or ""))
        return dict(row) if row else None

def statuses():
    with _lock:
        now=time.time()
        # Avoid retaining long-lived personal task identifiers indefinitely.
        for pid,v in list(_jobs.items()):
            if v.get("finished_at") and now-v["finished_at"]>1800:
                _jobs.pop(pid,None);_preview.pop(pid,None)
        return [dict(v) for v in _jobs.values()]

def get_preview(prompt_id):
    with _lock:
        return _preview.get(str(prompt_id or ""))

def _read_exact(stream,count):
    data=bytearray()
    while len(data)<count:
        chunk=stream.recv(count-len(data))
        if not chunk:
            raise ConnectionError("Socket ComfyUI fermé")
        data.extend(chunk)
    return bytes(data)

def _receive(stream):
    while True:
        head=_read_exact(stream,2)
        opcode=head[0]&0x0f
        length=head[1]&0x7f
        if length==126:
            length=struct.unpack("!H",_read_exact(stream,2))[0]
        elif length==127:
            length=struct.unpack("!Q",_read_exact(stream,8))[0]
        if length>8_000_000:
            raise ValueError("Trame WebSocket trop grande.")
        mask=_read_exact(stream,4) if head[1]&128 else None
        data=_read_exact(stream,length)
        if mask:
            data=bytes(x^mask[i%4] for i,x in enumerate(data))
        if opcode==8:
            return
        if opcode==1:
            try:
                event=json.loads(data.decode("utf-8"))
            except (UnicodeError,ValueError):
                continue
            typ=event.get("type")
            payload=event.get("data") or {}
            pid=str(payload.get("prompt_id") or "")
            if typ=="executing" and pid:
                update(pid,node=payload.get("node"),state="running")
            elif typ=="progress" and pid:
                update(pid,value=payload.get("value"),maximum=payload.get("max"),
                       node=payload.get("node"),state="running")
            elif typ=="execution_error" and pid:
                mark(pid,"error")
            elif typ=="execution_interrupted" and pid:
                mark(pid,"cancelled")
        elif opcode==2 and len(data)>8:
            # ComfyUI preview_image: uint32 message type, uint32 image type,
            # then JPEG/PNG bytes. It may be disabled by a model/workflow.
            raw=data[8:]
            if raw.startswith(b"\\xff\\xd8\\xff"):
                mime="image/jpeg"
            elif raw.startswith(b"\\x89PNG\\r\\n\\x1a\\n"):
                mime="image/png"
            else:
                continue
            with _lock:
                current=[j for j in _jobs.values() if j["state"]=="running"]
                if len(current)==1:
                    _preview[current[0]["prompt_id"]]=(mime,raw[:3_000_000])

def _listen(endpoint):
    uri=urlparse(endpoint)
    if uri.scheme not in ("http","https"):
        return
    host=uri.hostname or "127.0.0.1"
    port=uri.port or (443 if uri.scheme=="https" else 80)
    path=(uri.path.rstrip("/") or "")+"/ws?clientId="+CLIENT_ID
    while True:
        try:
            sock=socket.create_connection((host,port),timeout=5)
            if uri.scheme=="https":
                sock=ssl.create_default_context().wrap_socket(sock,server_hostname=host)
            sock.settimeout(35)
            key=base64.b64encode(os.urandom(16)).decode()
            handshake=(f"GET {path} HTTP/1.1\\r\\nHost: {host}:{port}\\r\\n"
                       "Upgrade: websocket\\r\\nConnection: Upgrade\\r\\n"
                       f"Sec-WebSocket-Key: {key}\\r\\nSec-WebSocket-Version: 13\\r\\n\\r\\n")
            sock.sendall(handshake.encode("ascii"))
            response=bytearray()
            while b"\\r\\n\\r\\n" not in response and len(response)<10000:
                response+=sock.recv(1024)
            if not response.startswith(b"HTTP/1.1 101"):
                raise ConnectionError("ComfyUI WebSocket non disponible")
            # socket.recv may consume the first frame; keep data for parsing.
            remainder=bytes(response).split(b"\\r\\n\\r\\n",1)[1]
            if remainder:
                sock=BufferedSocket(sock,remainder)
            _receive(sock)
        except (OSError,ConnectionError,ValueError,TimeoutError):
            pass
        finally:
            try:sock.close()
            except (NameError,OSError):pass
        time.sleep(3)

class BufferedSocket:
    def __init__(self,stream,buffer):
        self.stream=stream
        self.buffer=buffer
    def recv(self,count):
        if self.buffer:
            result,self.buffer=self.buffer[:count],self.buffer[count:]
            return result
        return self.stream.recv(count)
    def close(self):
        self.stream.close()

def start(endpoint):
    global _socket_thread,_endpoint
    with _lock:
        if _socket_thread and _socket_thread.is_alive() and _endpoint==endpoint:
            return CLIENT_ID
        _endpoint=endpoint
        _socket_thread=threading.Thread(target=_listen,args=(endpoint,),
                                        name="ComfyUIRealProgress",daemon=True)
        _socket_thread.start()
    return CLIENT_ID
