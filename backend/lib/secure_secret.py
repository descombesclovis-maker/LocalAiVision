"""Windows user-scoped DPAPI storage for provider credentials; never stores plaintext secrets."""
import ctypes
import os
from ctypes import wintypes


class _Blob(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_ubyte))]


def _dpapi(data: bytes, *, protect: bool) -> bytes:
    if os.name != "nt":
        raise RuntimeError("Le stockage DPAPI des secrets est disponible uniquement sous Windows.")
    crypt32 = ctypes.WinDLL("crypt32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    blob_ptr = ctypes.POINTER(_Blob)
    crypt32.CryptProtectData.argtypes = [blob_ptr, wintypes.LPCWSTR, blob_ptr, ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, blob_ptr]
    crypt32.CryptProtectData.restype = wintypes.BOOL
    crypt32.CryptUnprotectData.argtypes = [blob_ptr, ctypes.POINTER(wintypes.LPWSTR), blob_ptr, ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, blob_ptr]
    crypt32.CryptUnprotectData.restype = wintypes.BOOL
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    kernel32.LocalFree.restype = ctypes.c_void_p
    source_buf = (ctypes.c_ubyte * len(data)).from_buffer_copy(data)
    source = _Blob(len(data), source_buf)
    result = _Blob()
    if protect:
        ok = crypt32.CryptProtectData(ctypes.byref(source), "LocalAiStudio Hugging Face", None, None, None, 1, ctypes.byref(result))
    else:
        description = wintypes.LPWSTR()
        ok = crypt32.CryptUnprotectData(ctypes.byref(source), ctypes.byref(description), None, None, None, 1, ctypes.byref(result))
        if description:
            kernel32.LocalFree(description)
    if not ok:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        return ctypes.string_at(result.pbData, result.cbData)
    finally:
        kernel32.LocalFree(result.pbData)


def encrypt_secret(value: str) -> str:
    import base64
    return base64.b64encode(_dpapi(value.encode("utf-8"), protect=True)).decode("ascii")


def decrypt_secret(value: str) -> str:
    import base64
    return _dpapi(base64.b64decode(value, validate=True), protect=False).decode("utf-8")
