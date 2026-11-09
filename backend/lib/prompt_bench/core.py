"""V2-B: build the three prompt approaches compared on the same corpus, and check them mechanically.

Approaches (text only; no generator is called here):
- A  legacy   : text really sent today (image tasks get the legacy quality suffix; video is raw).
- B  v2a      : V2-A prepare_prompt(mode=BALANCED, enabled=True). Without a reachable local LLM it
                falls back to the exact original text, which is reported as such.
- C  ordered  : experimental. Same words as A, but clauses carrying explicit constraints (colour,
                position, negation, camera, identity, exact text) are moved first, so they fall
                inside the CLIP 77-token window. Hypothesis only, to be verified on the GPU.

Checks are text-level proxies. They do NOT measure visual fidelity.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any, Awaitable, Callable, Optional

from lib.prompt_preparation import FidelityMode, PromptTask, prepare_prompt
from lib.prompt_preparation.engine import split_clauses

from .corpus import IMAGE_TASKS

LEGACY_IMAGE_SUFFIX = ", highly detailed, professional photography, sharp focus, premium quality"
CONSTRAINT_RE = re.compile(
    r"\b(noir|noire|noirs|blanc|blanche|rouge|rouges|bleu|bleue|bleus|vert|verte|verts|jaune|gris|grise|doré|dorée|"
    r"beige|crème|cobalt|bordeaux|orange|ne |n'|sans|pas de|pas |immobile|fixe|exact|exactement|identique|même|conserv|"
    r"garder|uniquement|devant|derrière|gauche|droite|centre|haut|bas|texte|lettres|interdit|doit)\w*",
    re.IGNORECASE,
)
CLIP_TOKENS_PER_WORD = 1.3  # rough estimate; the real CLIP tokenizer is NOT used here
CLIP_WINDOW = 75  # usable tokens before the 77-token context limit


def _norm(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.replace("’", "'"))
    return re.sub(r"\s+", " ", "".join(c for c in decomposed if not unicodedata.combining(c)).lower()).strip()


def legacy_text(prompt: str, task: str) -> str:
    return prompt + LEGACY_IMAGE_SUFFIX if task in IMAGE_TASKS else prompt


def ordered_text(prompt: str, task: str) -> str:
    clauses = split_clauses(prompt)
    constrained = [c.text for c in clauses if CONSTRAINT_RE.search(c.text)]
    others = [c.text for c in clauses if not CONSTRAINT_RE.search(c.text)]
    text = " ".join(constrained + others)
    return text + LEGACY_IMAGE_SUFFIX if task in IMAGE_TASKS else text


def _unavailable_analyzer(system: str, payload: str) -> Awaitable[str]:
    raise ConnectionError("LLM local non lancé ou non sélectionné pour ce benchmark")


async def v2a_text(prompt: str, task: str, analyzer: Optional[Callable] = None) -> tuple[str, str]:
    """Return (prepared_text, status). Falls back to the original exact text on any failure."""
    prepared = await prepare_prompt(
        prompt, task=PromptTask(task), mode=FidelityMode.BALANCED, enabled=True,
        analyzer=analyzer or _unavailable_analyzer, timeout=120,
        # Declared as the real pipeline would: I2V always has a reference image; retouch has no mask in the app.
        reference_provided=task == "image-to-video",
    )
    return prepared.prepared_prompt, prepared.status.value


def check_text(text: str, original: str, item: dict) -> dict[str, Any]:
    low = _norm(text)
    original_low = _norm(original)
    missing, late = [], []
    for must in item["must"]:
        key = _norm(must)
        idx = low.find(key)
        if idx < 0:
            missing.append(must)
            continue
        words_before = len(re.findall(r"\w+", low[:idx]))
        if words_before * CLIP_TOKENS_PER_WORD >= CLIP_WINDOW:
            late.append(must)
    added = [f for f in item.get("forbidden", []) if _norm(f) in low and _norm(f) not in original_low]
    return {
        "words": len(re.findall(r"\w+", text)),
        "approx_clip_tokens": round(len(re.findall(r"\w+", text)) * CLIP_TOKENS_PER_WORD),
        "must_missing": missing,
        "must_beyond_clip_window": late,
        "forbidden_added": added,
        "pass": not (missing or late or added),
    }


async def build_item(item: dict, analyzer: Optional[Callable] = None) -> dict[str, Any]:
    prompt, task = item["prompt"], item["task"]
    prepared, status = await v2a_text(prompt, task, analyzer)
    texts = {
        "A0_raw": prompt,  # isolates the legacy quality suffix (A vs A0)
        "A_legacy": legacy_text(prompt, task),
        "B_v2a_balanced": prepared,
        "C_constraint_first": ordered_text(prompt, task),
    }
    return {
        "id": item["id"], "task": task, "original": prompt,
        "expect_conflict": bool(item.get("expect_conflict")),
        "v2a_status": status,
        "approaches": {
            name: {"text": text, "checks": check_text(text, prompt, item)} for name, text in texts.items()
        },
    }


def summarize(results: list[dict]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    names = list(results[0]["approaches"]) if results else []
    for name in names:
        checks = [r["approaches"][name]["checks"] for r in results]
        summary[name] = {
            "pass": sum(c["pass"] for c in checks),
            "total": len(checks),
            "missing": sum(len(c["must_missing"]) for c in checks),
            "beyond_clip_window": sum(len(c["must_beyond_clip_window"]) for c in checks),
            "forbidden_added": sum(len(c["forbidden_added"]) for c in checks),
        }
    return summary
