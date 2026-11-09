"""Reproducible prompt benchmark (V2-B). Run from `backend/`:

  .venv\\Scripts\\python.exe -m lib.prompt_bench                  # text-only, no GPU, no LLM
  .venv\\Scripts\\python.exe -m lib.prompt_bench --llm-model qwen2.5-coder:14b   # real local LLM (Ollama)
  .venv\\Scripts\\python.exe -m lib.prompt_bench --llm-model ... --render-photo --seed 1234   # needs ComfyUI

Everything is written to backend/bench_runs/<timestamp>/ (git-ignored). Nothing is uploaded.
Rendering never changes checkpoints, samplers, CFG, steps or resolutions: it reuses comfy.py builders
with their defaults, and only the prompt text varies between approaches.
"""
from __future__ import annotations

import argparse
import asyncio
import html
import json
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from lib.prompt_preparation import LocalAnalyzer, LocalLLMConfig

from .corpus import CORPUS, IMAGE_TASKS
from .core import build_item, summarize

APPROACHES = ("A0_raw", "A_legacy", "B_v2a_balanced", "C_constraint_first")


def _unload_ollama(url: str, model: str) -> str:
    """Ask Ollama to evict one model from VRAM (keep_alive=0). Only the named model is touched."""
    import httpx
    try:
        r = httpx.post(f"{url.rstrip('/')}/api/generate", json={"model": model, "keep_alive": 0}, timeout=30)
        return "unloaded" if r.status_code == 200 else f"http {r.status_code}"
    except Exception as exc:
        return f"error: {exc}"


def _comfy():
    """Import comfy lazily: text-only runs must not require MONGO_URL or a database."""
    import os
    os.environ.setdefault("MONGO_URL", "mongodb://127.0.0.1:1")  # never contacted by text-only runs
    os.environ.setdefault("DB_NAME", "localaistudio_bench_unused")
    from lib import comfy
    return comfy


class GpuSampler:
    """Polls nvidia-smi during a render; reports peak VRAM used above the pre-render baseline."""

    def __init__(self) -> None:
        self.baseline = self._used()
        self.peak = self.baseline
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, daemon=True)

    @staticmethod
    def _used() -> Optional[int]:
        try:
            out = subprocess.run(
                ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=5, check=True,
            ).stdout.strip().splitlines()[0]
            return int(out)
        except Exception:
            return None

    def _loop(self) -> None:
        while not self._stop.wait(0.5):
            used = self._used()
            if used is not None and (self.peak is None or used > self.peak):
                self.peak = used

    def __enter__(self) -> "GpuSampler":
        self._thread.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self._stop.set()
        self._thread.join(timeout=2)

    @property
    def peak_delta_mib(self) -> Optional[int]:
        if self.baseline is None or self.peak is None:
            return None
        return self.peak - self.baseline


def _workflow_params(workflow: dict) -> dict[str, Any]:
    params: dict[str, Any] = {}
    for node in workflow.values():
        cls = node.get("class_type", "")
        if cls in ("KSampler", "SamplerCustom", "LTXVScheduler", "CheckpointLoaderSimple", "UNETLoader"):
            params[cls] = {k: v for k, v in node.get("inputs", {}).items() if not isinstance(v, list)}
    return params


async def _render(comfy: Any, workflow: dict, video: bool, settings: dict) -> tuple[Optional[bytes], Optional[str], dict]:
    start = time.monotonic()
    with GpuSampler() as gpu:
        try:
            data, mime = await comfy.run(workflow, video, None, None, s=settings)
            error = None
        except comfy.ComfyError as exc:  # explicit ComfyUI errors (missing model, OOM, unreachable…)
            data, mime, error = None, None, f"{type(exc).__name__}: {exc}"
    return data, mime, {"duration_s": round(time.monotonic() - start, 1), "vram_peak_delta_mib": gpu.peak_delta_mib, "error": error}


def settings_for(comfy: Any, args: argparse.Namespace) -> dict:
    """Effective ComfyUI settings for a benchmark run: app defaults, overridden ONLY by explicit CLI choices."""
    settings = {**comfy.DEFAULTS, "base_url": args.comfy_url}
    if args.image_preset:
        if args.image_preset not in comfy.IMAGE_PRESETS:
            raise SystemExit(f"preset image inconnu : {args.image_preset} (choix : {', '.join(comfy.IMAGE_PRESETS)})")
        settings["image_preset"] = args.image_preset
        settings["image_checkpoint"] = comfy.IMAGE_PRESETS[args.image_preset]["checkpoint"]
    if args.image_checkpoint:
        settings["image_checkpoint"] = args.image_checkpoint  # explicit file name, verified by verify_ready
    return settings


async def run_bench(args: argparse.Namespace) -> Path:
    analyzer = None
    if args.llm_model:
        analyzer = LocalAnalyzer(LocalLLMConfig("ollama", args.llm_url, args.llm_model, 16384))
    if args.llm_model:
        analyzer = LocalAnalyzer(LocalLLMConfig("ollama", args.llm_url, args.llm_model, 16384))

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out = Path(args.out) / stamp
    (out / "renders").mkdir(parents=True, exist_ok=True)

    items = [i for i in CORPUS if not args.only or i["id"] in args.only]
    results = [await build_item(item, analyzer) for item in items]

    rendering = args.render_photo or args.render_video
    comfy = _comfy() if rendering else None
    settings: dict = {}
    preflight: dict = {"checked": False}
    if rendering:
        settings = settings_for(comfy, args)
        if args.unload_ollama and args.llm_model:
            preflight["ollama_unload"] = _unload_ollama(args.llm_url, args.llm_model)
        try:
            await comfy.verify_ready(settings, video=args.render_video and not args.render_photo)
            preflight.update(checked=True, ok=True, checkpoint=settings["image_checkpoint"], video_preset=settings["video_preset"])
        except comfy.ComfyError as exc:
            preflight.update(checked=True, ok=False, error=f"{type(exc).__name__}: {exc}")
    render_plan = []
    if args.render_photo and preflight.get("ok", not rendering):
        render_plan += [(i, "photo") for i in items if i["task"] in IMAGE_TASKS]
    if args.render_video and preflight.get("ok", not rendering):
        render_plan += [(i, "video") for i in items if i["task"] == "text-to-video"]
    if args.approach:
        approaches = tuple(a for a in APPROACHES if a in args.approach)
    else:
        approaches = APPROACHES

    renders: list[dict] = []
    for item, kind in render_plan:
        result = next(r for r in results if r["id"] == item["id"])
        for name in approaches:
            text = result["approaches"][name]["text"]
            for seed in args.seed:
                if kind == "photo":
                    w, h = comfy.IMAGE_SIZES["1:1"]
                    wf = comfy._image_workflow(settings, text, w, h, seed, None)
                    video = False
                else:
                    if item.get("task") == "image-to-video":
                        continue  # I2V needs a reference image; never fabricated here
                    w, h = comfy.VIDEO_SIZES["16:9"]
                    wf = comfy._video_workflow(settings, text, w, h, comfy.VIDEO_LENGTHS["3"], seed, None)
                    video = True
                data, mime, meta = await _render(comfy, wf, video, settings)
                ext = "mp4" if video else "png"
                rel = None
                if data is not None:
                    rel = f"renders/{item['id']}__{name}__s{seed}.{ext}"
                    (out / rel).write_bytes(data)
                renders.append({
                    "id": item["id"], "approach": name, "seed": seed, "kind": kind, "file": rel,
                    "prompt_sent": text, "params": _workflow_params(wf), "resolution": [w, h], **meta,
                })

    manifest = {
        "schema_version": 2, "created": stamp, "scope": "text_checks_and_optional_renders",
        "v2a_llm": args.llm_model or "none (fallback to original text)",
        "comfy_url": args.comfy_url if rendering else None,
        "preflight": preflight,
        "images_produced": sum(1 for r in renders if r.get("file")),
        "renders_failed": sum(1 for r in renders if r.get("error")),
        "rendered": any(r.get("file") for r in renders),
        "summary": summarize(results),
        "items": results, "renders": renders,
        "notes": [
            "Text checks are proxies (CLIP token count estimated at 1.3 tokens/word).",
            "Visual quality, fidelity and anatomy must be judged by eye on renders/ with the same seeds.",
            "A0_raw / A_legacy isolate the quality suffix ; B adds the V2-A template ; C only reorders clauses.",
        ],
    }
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "index.html").write_text(_gallery(manifest), encoding="utf-8")
    return out


def _gallery(m: dict) -> str:
    rows = []
    renders = {(r["id"], r["approach"], r["seed"]): r for r in m["renders"]}
    for item in m["items"]:
        cells = []
        for name in (n for n in APPROACHES if n in item["approaches"]):
            a = item["approaches"][name]
            media = ""
            for (rid, rname, seed), r in renders.items():
                if rid == item["id"] and rname == name and r.get("file"):
                    src = html.escape(r["file"])
                    media += (f'<video controls width="320" src="{src}"></video>' if r["kind"] == "video"
                              else f'<img width="320" src="{src}">')
                elif rid == item["id"] and rname == name and r.get("error"):
                    media += f'<p class="err">{html.escape(r["error"])}</p>'
            status = "PASS" if a["checks"]["pass"] else "FAIL " + html.escape(json.dumps({
                k: a["checks"][k] for k in ("must_missing", "must_beyond_clip_window", "forbidden_added")}, ensure_ascii=False))
            cells.append(f"<td><b>{name}</b><br>{status}<br><pre>{html.escape(a['text'])}</pre>{media}</td>")
        rows.append(f"<tr><th>{html.escape(item['id'])}<br><small>{html.escape(item['task'])}</small>"
                    f"<br><small>V2-A : {html.escape(item['v2a_status'])}</small></th>{''.join(cells)}</tr>")
    return ("<!doctype html><meta charset=utf-8><title>V2-B</title>"
            "<style>body{font-family:sans-serif}td{vertical-align:top;width:33%;padding:6px;border:1px solid #ccc}"
            "pre{white-space:pre-wrap;font-size:12px}.err{color:#b00}</style>"
            f"<h1>Benchmark V2-B — {html.escape(m['created'])}</h1><p>Vérification textuelle seulement ; "
            "jugez les images/vidéos à l'œil avec les mêmes seeds.</p>"
            f"<table>{''.join(rows)}</table>")


def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser(description="V2-B : comparaison reproductible A/B/C (locale).")
    p.add_argument("--out", default="bench_runs", help="Dossier de sortie (git-ignoré).")
    p.add_argument("--only", nargs="*", default=[], help="Identifiants de corpus à exécuter.")
    p.add_argument("--llm-model", help="Modèle Ollama DÉJÀ installé ; absent = repli sur l'original.")
    p.add_argument("--llm-url", default="http://127.0.0.1:11434")
    p.add_argument("--render-photo", action="store_true", help="Rend les prompts photo via ComfyUI (GPU).")
    p.add_argument("--render-video", action="store_true", help="Rend les T2V via ComfyUI (coûteux).")
    p.add_argument("--seed", type=int, action="append", default=None, help="Seed(s) ; répétable. Défaut : 1234.")
    p.add_argument("--comfy-url", default="http://127.0.0.1:8188")
    p.add_argument("--image-preset", help="flux-dev | flux-schnell | sdxl (définit aussi le checkpoint).")
    p.add_argument("--image-checkpoint", help="Nom exact du checkpoint installé dans ComfyUI (prioritaire).")
    p.add_argument("--approach", action="append", help=f"Restreindre aux approches : {', '.join(APPROACHES)}.")
    p.add_argument("--unload-ollama", action="store_true",
                   help="Décharge le modèle --llm-model de la VRAM avant le rendu (ne touche aucun autre modèle).")
    args = p.parse_args(argv)
    args.seed = args.seed or [1234]
    unknown = set(args.only) - {i["id"] for i in CORPUS}
    if unknown:
        p.error(f"identifiants inconnus : {sorted(unknown)}")
    if args.approach and set(args.approach) - set(APPROACHES):
        p.error(f"approches inconnues : {sorted(set(args.approach) - set(APPROACHES))}")
    out = asyncio.run(run_bench(args))
    print(f"Résultats : {out / 'index.html'}")
    manifest = json.loads((out / 'manifest.json').read_text(encoding='utf-8'))
    if manifest["preflight"].get("checked") and not manifest["preflight"].get("ok"):
        print(f"Rendu NON lancé (contrôle ComfyUI) : {manifest['preflight']['error']}")
    print(f"Images produites : {manifest['images_produced']} ; échecs : {manifest['renders_failed']}")
    print(json.dumps(manifest['summary'], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
