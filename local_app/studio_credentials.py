"""LocalAI Studio user-scope Google API credentials.

Secrets are never written into the Git tree, browser storage or plaintext files.
The Windows desktop build protects values with DPAPI for the signed-in user.
Environment overrides remain available for managed/manual installations.
"""
from __future__ import annotations

import base64
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import sys
import tempfile
import threading

ENV_KEYS = {
    "maps_browser": "LOCALAIWEB_GOOGLE_MAPS_BROWSER_KEY",
    "places_server": "LOCALAIWEB_GOOGLE_PLACES_API_KEY",
}
_LOCK = threading.RLock()
_FILENAME = "google-api.dpapi"
_FLAG_UI_FORBIDDEN = 0x1


class _Blob(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_ubyte))]


def _location() -> Path:
    # Never eagerly evaluate Path.home(): tests and minimal Windows processes
    # may not provide HOME/USERPROFILE, even when LOCALAPPDATA is available.
    data_dir = os.environ.get("LOCALVISIONAI_DATA")
    if data_dir:
        root = Path(data_dir)
    elif os.environ.get("LOCALAPPDATA"):
        root = Path(os.environ["LOCALAPPDATA"]) / "LocalVisionAI"
    else:
        try:
            root = Path.home() / "LocalVisionAI"
        except RuntimeError:
            # An artificial environment with no user profile is not a valid
            # location for persistent credentials. Read as unconfigured and
            # refuse saving until the user profile is available.
            raise OSError("Profil utilisateur Windows indisponible.")
    return root / "connections" / _FILENAME


def _protect(raw: bytes, *, decrypt=False) -> bytes:
    if sys.platform != "win32":
        raise RuntimeError("Enregistrement chiffré disponible sur Windows uniquement. Utilisez les variables d'environnement sur ce système.")
    source = ctypes.create_string_buffer(raw)
    blob_in = _Blob(len(raw), ctypes.cast(source, ctypes.POINTER(ctypes.c_ubyte)))
    blob_out = _Blob()
    crypt = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    crypt.CryptProtectData.argtypes = [ctypes.POINTER(_Blob), wintypes.LPCWSTR, ctypes.c_void_p,
        ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(_Blob)]
    crypt.CryptUnprotectData.argtypes = [ctypes.POINTER(_Blob), ctypes.c_void_p, ctypes.c_void_p,
        ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(_Blob)]
    crypt.CryptProtectData.restype = wintypes.BOOL
    crypt.CryptUnprotectData.restype = wintypes.BOOL
    api = crypt.CryptUnprotectData if decrypt else crypt.CryptProtectData
    if decrypt:
        result = api(ctypes.byref(blob_in), None, None, None, None,
                     _FLAG_UI_FORBIDDEN, ctypes.byref(blob_out))
    else:
        result = api(ctypes.byref(blob_in), "LocalAiStudio Google Maps", None, None, None,
                     _FLAG_UI_FORBIDDEN, ctypes.byref(blob_out))
    if not result:
        raise OSError(ctypes.get_last_error(), "Windows n'a pas pu protéger ou lire les clés API.")
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    kernel.LocalFree.restype = ctypes.c_void_p
    try:
        return ctypes.string_at(blob_out.pbData, blob_out.cbData)
    finally:
        kernel.LocalFree(ctypes.cast(blob_out.pbData, ctypes.c_void_p))


def _load() -> dict:
    path = _location()
    if not path.is_file():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("format") != "win-dpapi-1":
        raise ValueError("Format des paramètres chiffrés inconnu.")
    raw = _protect(base64.b64decode(payload["encrypted"], validate=True), decrypt=True)
    data = json.loads(raw.decode("utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Configuration invalide.")
    return {key: value for key, value in data.items() if key in ENV_KEYS and isinstance(value, str)}


def _save(data: dict) -> None:
    path = _location()
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(data, ensure_ascii=False).encode("utf-8")
    encrypted = _protect(raw)
    content = json.dumps({"format": "win-dpapi-1", "encrypted": base64.b64encode(encrypted).decode("ascii")})
    fd, name = tempfile.mkstemp(prefix=".keys-", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def read_key(kind: str) -> str:
    if kind not in ENV_KEYS:
        raise ValueError("Identifiant de clé inconnu.")
    override = os.environ.get(ENV_KEYS[kind], "").strip()
    if override:
        return override
    with _LOCK:
        try:
            return _load().get(kind, "")
        except OSError:
            return ""


def status() -> dict:
    with _LOCK:
        try:
            data = _load()
        except OSError:
            data = {}
        return {
            key: {"configured": bool(os.environ.get(env, "").strip() or data.get(key)),
                  "environment_override": bool(os.environ.get(env, "").strip())}
            for key, env in ENV_KEYS.items()
        }


def modify(kind: str, action: str, value: str = "") -> dict:
    if kind not in ENV_KEYS:
        raise ValueError("Clé API inconnue.")
    if action not in ("save", "clear"):
        raise ValueError("Action inconnue.")
    if action == "save":
        value = str(value).strip()
        if not 16 <= len(value) <= 256 or any(ord(c) < 33 or ord(c) > 126 for c in value):
            raise ValueError("La clé doit contenir entre 16 et 256 caractères ASCII imprimables.")
    with _LOCK:
        data = _load()
        if action == "clear":
            data.pop(kind, None)
        else:
            data[kind] = value
        _save(data)
        return status()
