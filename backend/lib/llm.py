"""LLM helpers (Emergent universal key): streamed text completion, image generation, output parsers."""
import base64
import json
import os
import re
import uuid
from typing import Awaitable, Callable, Optional

from lib import comfy
from lib.local_engine import complete_local
try:  # paid fallback engines; optional when running 100 % local
    from emergentintegrations.llm.chat import ImageContent, LlmChat, StreamDone, TextDelta, UserMessage
except ImportError:  # pragma: no cover
    LlmChat = None  # type: ignore

TEXT_MODELS: dict[str, tuple[str, str]] = {
    "claude": ("anthropic", "claude-sonnet-4-5-20250929"),
    "gpt": ("openai", "gpt-5.2"),
    "gemini": ("gemini", "gemini-3.1-pro-preview"),
}
IMAGE_MODELS: dict[str, str] = {
    "nano-banana": "gemini-3.1-flash-image-preview",
    "nano-banana-pro": "gemini-3-pro-image-preview",
}


def _key() -> str:
    if LlmChat is None or not os.environ.get("EMERGENT_LLM_KEY"):
        raise RuntimeError("Moteurs en ligne non configurés (clé universelle absente) : utilisez le moteur local.")
    return os.environ["EMERGENT_LLM_KEY"]


async def complete(
    system: str,
    prompt: str,
    llm: str = "claude",
    max_tokens: int = 16000,
    on_progress: Optional[Callable[[int], Awaitable[None]]] = None,
) -> str:
    if llm == "local":
        return await complete_local(system, prompt, max_tokens, on_progress)
    provider, model = TEXT_MODELS.get(llm, TEXT_MODELS["claude"])
    chat = (
        LlmChat(api_key=_key(), session_id=str(uuid.uuid4()), system_message=system)
        .with_model(provider, model)
        .with_params(max_tokens=max_tokens)
    )
    out: list[str] = []
    size = 0
    last = 0
    async for ev in chat.stream_message(UserMessage(text=prompt)):
        if isinstance(ev, TextDelta):
            out.append(ev.content)
            size += len(ev.content)
            if on_progress and size - last > 3000:
                last = size
                await on_progress(size)
        elif isinstance(ev, StreamDone):
            break
    return "".join(out)


async def generate_image(
    prompt: str, model: str = "nano-banana", ref_b64: Optional[str] = None, aspect: str = "1:1", ref_mime: str = "image/png",
) -> tuple[bytes, str]:
    if model == "comfy":
        return await comfy.generate_image(prompt, aspect, (base64.b64decode(ref_b64), ref_mime) if ref_b64 else None)
    chat = (
        LlmChat(api_key=_key(), session_id=str(uuid.uuid4()), system_message="You are an expert image generator.")
        .with_model("gemini", IMAGE_MODELS.get(model, IMAGE_MODELS["nano-banana"]))
        .with_params(modalities=["image", "text"])
    )
    msg = UserMessage(text=prompt, file_contents=[ImageContent(ref_b64)]) if ref_b64 else UserMessage(text=prompt)
    _text, images = await chat.send_message_multimodal_response(msg)
    if not images:
        raise RuntimeError("Le modèle n'a renvoyé aucune image")
    img = images[0]
    return base64.b64decode(img["data"]), img.get("mime_type") or "image/png"


def parse_json(text: str) -> dict:
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t)
    start, end = t.find("{"), t.rfind("}")
    if start < 0 or end < 0:
        raise ValueError("Réponse JSON introuvable")
    return json.loads(t[start : end + 1])


def _strip_fences(body: str) -> str:
    b = body.strip("\n")
    m = re.match(r"^\s*```[a-zA-Z]*\n(.*?)\n?```\s*$", b, re.S)
    return (m.group(1) if m else b).strip("\n") + "\n"


FILE_RE = re.compile(r"===FILE:\s*([^\n=]+?)\s*===\n(.*?)(?=\n===FILE:|\n===EDIT:|\n===END===|\Z)", re.S)
EDIT_RE = re.compile(r"===EDIT:\s*([^\n=]+?)\s*===\n(.*?)(?=\n===FILE:|\n===EDIT:|\n===END===|\Z)", re.S)
BLOCK_RE = re.compile(r"<<<<<<< SEARCH\n(.*?)\n=======\n(.*?)\n>>>>>>> REPLACE", re.S)


def parse_files(text: str) -> dict[str, str]:
    return {m.group(1).strip(): _strip_fences(m.group(2)) for m in FILE_RE.finditer(text)}


def parse_edits(text: str) -> dict[str, list[tuple[str, str]]]:
    edits: dict[str, list[tuple[str, str]]] = {}
    for m in EDIT_RE.finditer(text):
        edits.setdefault(m.group(1).strip(), []).extend(BLOCK_RE.findall(m.group(2)))
    return edits


def apply_edit(content: str, search: str, replace: str) -> Optional[str]:
    if search in content:
        return content.replace(search, replace, 1)
    # tolerant match: compare line by line ignoring leading/trailing whitespace
    lines = content.split("\n")
    target = [s.strip() for s in search.strip("\n").split("\n")]
    n = len(target)
    for i in range(len(lines) - n + 1):
        if [x.strip() for x in lines[i : i + n]] == target:
            return "\n".join(lines[:i] + replace.split("\n") + lines[i + n :])
    return None


def friendly_error(exc: Exception) -> str:
    s = str(exc)
    if "budget" in s.lower() or "insufficient" in s.lower() or " 402" in s:
        return "Solde de la clé universelle insuffisant. Rechargez-le (Profil → Clé universelle → Ajouter du solde) puis cliquez sur « Reprendre »."
    return s[:300]
