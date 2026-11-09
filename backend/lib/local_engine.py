"""Local, free AI engine: Ollama (native API) or any OpenAI-compatible server (LM Studio, llama.cpp, vLLM)."""
import json
from typing import Awaitable, Callable, Optional

import httpx

from lib.db import db

DEFAULTS = {"kind": "ollama", "base_url": "http://localhost:11434", "model": "qwen2.5-coder:14b", "num_ctx": 16384}


class LocalEngineError(RuntimeError):
    """Base error for the local text engine (Ollama / LM Studio / OpenAI-compatible)."""


class EngineUnreachable(LocalEngineError):
    """The local text engine server is not running or not reachable."""


class ModelMissing(LocalEngineError):
    """The configured text model is not installed on the server."""


async def get_settings() -> dict:
    doc = await db.settings.find_one({"id": "local_engine"}, {"_id": 0, "id": 0}) or {}
    return {**DEFAULTS, **doc}


async def save_settings(data: dict) -> dict:
    data = {**data, "base_url": data["base_url"].rstrip("/")}
    await db.settings.update_one({"id": "local_engine"}, {"$set": data}, upsert=True)
    return await get_settings()


def _unreachable(s: dict) -> str:
    app = "Ollama (commande « ollama serve »)" if s["kind"] == "ollama" else "LM Studio (onglet Developer → Start server)"
    return (
        f"Moteur local injoignable à {s['base_url']}. Lancez {app} sur la machine qui exécute LocalAiStudio, "
        f"vérifiez que le modèle « {s['model']} » est installé, puis relancez."
    )


def _engine_http_error(s: dict, status: int, body: str) -> LocalEngineError:
    """Categorise an HTTP error from the local engine: a missing model vs a generic server error."""
    blob = body.lower()
    if status == 404 or "not found" in blob or "try pulling" in blob or "model not found" in blob:
        cmd = f"ollama pull {s['model']}" if s["kind"] == "ollama" else "chargez-le dans LM Studio"
        return ModelMissing(
            f"Modèle de texte « {s['model']} » absent du serveur. Téléchargez-le : {cmd}, "
            "ou choisissez un modèle présent dans Moteurs → Configurer."
        )
    return LocalEngineError(f"Moteur local : erreur {status} — {body[:200]}")


async def list_models(s: dict) -> list[str]:
    async with httpx.AsyncClient(timeout=httpx.Timeout(6, connect=4)) as c:
        if s["kind"] == "ollama":
            r = await c.get(f"{s['base_url']}/api/tags")
            r.raise_for_status()
            return [m["name"] for m in r.json().get("models", [])]
        r = await c.get(f"{s['base_url']}/models")
        r.raise_for_status()
        return [m["id"] for m in r.json().get("data", [])]


async def test(s: dict) -> dict:
    try:
        models = await list_models(s)
    except Exception:
        return {"ok": False, "models": [], "message": _unreachable(s)}
    if s["model"] not in models:
        hint = f"ollama pull {s['model']}" if s["kind"] == "ollama" else "chargez-le dans LM Studio"
        return {"ok": False, "models": models, "message": f"Serveur joignable, mais le modèle « {s['model']} » est absent ({hint})."}
    return {"ok": True, "models": models, "message": f"Moteur local prêt : {s['model']}"}


async def complete_local(
    system: str, prompt: str, max_tokens: int, on_progress: Optional[Callable[[int], Awaitable[None]]] = None
) -> str:
    s = await get_settings()
    messages = [{"role": "system", "content": system}, {"role": "user", "content": prompt}]
    out: list[str] = []
    size = last = 0

    async def push(piece: str) -> None:
        nonlocal size, last
        out.append(piece)
        size += len(piece)
        if on_progress and size - last > 3000:
            last = size
            await on_progress(size)

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(900, connect=8)) as c:
            if s["kind"] == "ollama":
                body = {"model": s["model"], "messages": messages, "stream": True,
                        "options": {"num_ctx": s["num_ctx"], "num_predict": max_tokens, "temperature": 0.6}}
                async with c.stream("POST", f"{s['base_url']}/api/chat", json=body) as r:
                    if r.status_code >= 400:
                        raise _engine_http_error(s, r.status_code, (await r.aread()).decode()[:200])
                    async for line in r.aiter_lines():
                        if not line.strip():
                            continue
                        ev = json.loads(line)
                        await push(ev.get("message", {}).get("content", ""))
                        if ev.get("done"):
                            break
            else:
                body = {"model": s["model"], "messages": messages, "stream": True, "max_tokens": max_tokens, "temperature": 0.6}
                async with c.stream("POST", f"{s['base_url']}/chat/completions", json=body) as r:
                    if r.status_code >= 400:
                        raise _engine_http_error(s, r.status_code, (await r.aread()).decode()[:200])
                    async for line in r.aiter_lines():
                        if not line.startswith("data:"):
                            continue
                        data = line[5:].strip()
                        if data == "[DONE]":
                            break
                        delta = json.loads(data)["choices"][0].get("delta", {})
                        await push(delta.get("content") or "")
    except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
        raise EngineUnreachable(_unreachable(s)) from exc
    return "".join(out)
