"""Local, free image & video generation through a ComfyUI server (FLUX / SDXL images, Wan 2.2 / LTX-Video videos).

Built-in workflows use ComfyUI core nodes. Users may also paste their own workflow exported with
"Export (API)" and use the placeholders {{PROMPT}} {{NEGATIVE}} {{WIDTH}} {{HEIGHT}} {{SEED}} {{LENGTH}} {{IMAGE}}.
"""
import asyncio
import json
import random
import time
import uuid
from typing import Any, Awaitable, Callable, Optional

import httpx

from lib.db import db

IMAGE_PRESETS = {
    "flux-dev": {"label": "FLUX.1 dev (fp8)", "checkpoint": "flux1-dev-fp8.safetensors"},
    "flux-schnell": {"label": "FLUX.1 schnell (fp8, rapide)", "checkpoint": "flux1-schnell-fp8.safetensors"},
    "sdxl": {"label": "SDXL", "checkpoint": "sd_xl_base_1.0.safetensors"},
}
VIDEO_PRESETS = {
    "wan22": {"label": "Wan 2.2 TI2V 5B", "model": "wan2.2_ti2v_5B_fp16.safetensors", "text_encoder": "umt5_xxl_fp8_e4m3fn_scaled.safetensors", "vae": "wan2.2_vae.safetensors"},
    "ltxv": {"label": "LTX-Video 2B", "model": "ltx-video-2b-v0.9.5.safetensors", "text_encoder": "t5xxl_fp16.safetensors", "vae": ""},
}
DEFAULTS = {
    "base_url": "http://127.0.0.1:8188",
    "image_preset": "flux-dev",
    "image_checkpoint": IMAGE_PRESETS["flux-dev"]["checkpoint"],
    "video_preset": "wan22",
    "video_model": VIDEO_PRESETS["wan22"]["model"],
    "video_text_encoder": VIDEO_PRESETS["wan22"]["text_encoder"],
    "video_vae": VIDEO_PRESETS["wan22"]["vae"],
    "custom_image_workflow": "",
    "custom_video_workflow": "",
}
IMAGE_SIZES = {"1:1": (1024, 1024), "16:9": (1344, 768), "9:16": (768, 1344), "4:5": (896, 1120)}
VIDEO_SIZES = {"16:9": (832, 480), "9:16": (480, 832), "1:1": (640, 640)}
VIDEO_LENGTHS = {"3": 73, "5": 121}  # 24 fps, valid for both Wan (4n+1) and LTX (8n+1)
NEGATIVE = "blurry, low quality, deformed, watermark, text, logo, jpeg artifacts, oversaturated"

Progress = Optional[Callable[[str], Awaitable[None]]]


class ComfyError(RuntimeError):
    pass


async def get_settings() -> dict:
    doc = await db.settings.find_one({"id": "comfyui"}, {"_id": 0, "id": 0}) or {}
    return {**DEFAULTS, **doc}


async def save_settings(data: dict) -> dict:
    for key in ("custom_image_workflow", "custom_video_workflow"):
        if data.get(key, "").strip():
            try:
                json.loads(data[key])
            except ValueError as exc:
                raise ComfyError(f"Workflow personnalisé invalide (JSON attendu, export « API » de ComfyUI) : {exc}") from exc
    data = {**data, "base_url": data["base_url"].rstrip("/")}
    await db.settings.update_one({"id": "comfyui"}, {"$set": data}, upsert=True)
    return await get_settings()


def unreachable(s: dict) -> str:
    return (
        f"ComfyUI injoignable à {s['base_url']}. Lancez ComfyUI (Desktop ou « python main.py --listen ») sur la machine "
        "qui exécute LocalAiStudio, puis réessayez."
    )


def _client(timeout: float = 30) -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=httpx.Timeout(timeout, connect=5))


async def _choices(c: httpx.AsyncClient, base: str, node: str, field: str) -> list[str]:
    try:
        r = await c.get(f"{base}/object_info/{node}")
        r.raise_for_status()
        return list(r.json()[node]["input"]["required"][field][0])
    except Exception:
        return []


async def reachable() -> bool:
    s = await get_settings()
    try:
        async with _client(4) as c:
            return (await c.get(f"{s['base_url']}/system_stats")).status_code == 200
    except Exception:
        return False


async def test(s: dict) -> dict:
    base = s["base_url"].rstrip("/")
    try:
        async with _client(8) as c:
            r = await c.get(f"{base}/system_stats")
            r.raise_for_status()
            dev = (r.json().get("devices") or [{}])[0]
            ckpts = await _choices(c, base, "CheckpointLoaderSimple", "ckpt_name")
            unets = await _choices(c, base, "UNETLoader", "unet_name")
            clips = await _choices(c, base, "CLIPLoader", "clip_name")
    except Exception:
        return {"ok": False, "message": unreachable(s), "gpu": "", "checkpoints": [], "diffusion_models": [], "text_encoders": []}
    missing = [f for f in (s["image_checkpoint"],) if f not in ckpts]
    vid_needed = [s["video_model"], s["video_text_encoder"]]
    vid_have = (unets if s["video_preset"] == "wan22" else ckpts) + clips
    missing += [f for f in vid_needed if f and f not in vid_have]
    gpu = f"{dev.get('name', 'GPU')} · {round((dev.get('vram_total') or 0) / 1024**3, 1)} Go VRAM"
    msg = f"ComfyUI prêt ({gpu})" if not missing else f"ComfyUI joignable ({gpu}), fichiers manquants : {', '.join(missing)}"
    return {"ok": not missing, "message": msg, "gpu": gpu, "checkpoints": ckpts, "diffusion_models": unets, "text_encoders": clips}


# ------------------------------------------------------------------ workflows (ComfyUI API format)

def _image_workflow(s: dict, prompt: str, w: int, h: int, seed: int, image: Optional[str]) -> dict:
    flux = s["image_preset"].startswith("flux")
    schnell = s["image_preset"] == "flux-schnell"
    wf: dict[str, Any] = {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": s["image_checkpoint"]}},
        "2": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["1", 1]}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"text": "" if flux else NEGATIVE, "clip": ["1", 1]}},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["5", 0], "vae": ["1", 2]}},
        "9": {"class_type": "SaveImage", "inputs": {"filename_prefix": "LocalAiStudio", "images": ["8", 0]}},
    }
    positive: list = ["2", 0]
    if flux and not schnell:
        wf["4"] = {"class_type": "FluxGuidance", "inputs": {"conditioning": ["2", 0], "guidance": 3.5}}
        positive = ["4", 0]
    if image:
        wf["10"] = {"class_type": "LoadImage", "inputs": {"image": image}}
        wf["11"] = {"class_type": "ImageScaleToTotalPixels", "inputs": {"image": ["10", 0], "upscale_method": "lanczos", "megapixels": 1.0, "resolution_steps": 1}}
        wf["6"] = {"class_type": "VAEEncode", "inputs": {"pixels": ["11", 0], "vae": ["1", 2]}}
        denoise = 0.62
    else:
        wf["6"] = {"class_type": "EmptySD3LatentImage" if flux else "EmptyLatentImage", "inputs": {"width": w, "height": h, "batch_size": 1}}
        denoise = 1.0
    steps, cfg, sampler, sched = (4, 1.0, "euler", "simple") if schnell else (22, 1.0, "euler", "simple") if flux else (30, 6.5, "dpmpp_2m", "karras")
    wf["5"] = {"class_type": "KSampler", "inputs": {
        "model": ["1", 0], "positive": positive, "negative": ["3", 0], "latent_image": ["6", 0], "seed": seed,
        "steps": steps, "cfg": cfg, "sampler_name": sampler, "scheduler": sched, "denoise": denoise}}
    return wf


def _video_workflow(s: dict, prompt: str, w: int, h: int, length: int, seed: int, image: Optional[str]) -> dict:
    neg = "static, blurry, low quality, distorted, watermark, text, jitter, deformed"
    save = {
        "20": {"class_type": "CreateVideo", "inputs": {"images": ["8", 0], "fps": 24}},
        "21": {"class_type": "SaveVideo", "inputs": {"video": ["20", 0], "filename_prefix": "LocalAiStudio/video", "format": "mp4", "codec": "h264"}},
    }
    if s["video_preset"] == "wan22":
        wf: dict[str, Any] = {
            "1": {"class_type": "UNETLoader", "inputs": {"unet_name": s["video_model"], "weight_dtype": "default"}},
            "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": s["video_text_encoder"], "type": "wan", "device": "default"}},
            "3": {"class_type": "VAELoader", "inputs": {"vae_name": s["video_vae"]}},
            "4": {"class_type": "ModelSamplingSD3", "inputs": {"model": ["1", 0], "shift": 8.0}},
            "5": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["2", 0]}},
            "6": {"class_type": "CLIPTextEncode", "inputs": {"text": neg, "clip": ["2", 0]}},
            "7": {"class_type": "Wan22ImageToVideoLatent", "inputs": {"vae": ["3", 0], "width": w, "height": h, "length": length, "batch_size": 1}},
            "9": {"class_type": "KSampler", "inputs": {
                "model": ["4", 0], "positive": ["5", 0], "negative": ["6", 0], "latent_image": ["7", 0], "seed": seed,
                "steps": 30, "cfg": 5.0, "sampler_name": "uni_pc", "scheduler": "simple", "denoise": 1.0}},
            "8": {"class_type": "VAEDecode", "inputs": {"samples": ["9", 0], "vae": ["3", 0]}},
            **save,
        }
        if image:
            wf["10"] = {"class_type": "LoadImage", "inputs": {"image": image}}
            wf["7"]["inputs"]["start_image"] = ["10", 0]
        return wf
    # LTX-Video
    wf = {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": s["video_model"]}},
        "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": s["video_text_encoder"], "type": "ltxv", "device": "default"}},
        "5": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["2", 0]}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"text": neg, "clip": ["2", 0]}},
        "12": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "euler"}},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["14", 0], "vae": ["1", 2]}},
        **save,
    }
    if image:
        wf["10"] = {"class_type": "LoadImage", "inputs": {"image": image}}
        wf["7"] = {"class_type": "LTXVImgToVideo", "inputs": {
            "positive": ["5", 0], "negative": ["6", 0], "vae": ["1", 2], "image": ["10", 0],
            "width": w, "height": h, "length": length, "batch_size": 1, "strength": 1.0}}
        cond_pos, cond_neg, latent = ["7", 0], ["7", 1], ["7", 2]
    else:
        wf["7"] = {"class_type": "EmptyLTXVLatentVideo", "inputs": {"width": w, "height": h, "length": length, "batch_size": 1}}
        cond_pos, cond_neg, latent = ["5", 0], ["6", 0], ["7", 0]
    wf["11"] = {"class_type": "LTXVConditioning", "inputs": {"positive": cond_pos, "negative": cond_neg, "frame_rate": 24.0}}
    wf["13"] = {"class_type": "LTXVScheduler", "inputs": {"steps": 30, "max_shift": 2.05, "base_shift": 0.95, "stretch": True, "terminal": 0.1, "latent": latent}}
    wf["14"] = {"class_type": "SamplerCustom", "inputs": {
        "model": ["1", 0], "add_noise": True, "noise_seed": seed, "cfg": 3.0, "positive": ["11", 0], "negative": ["11", 1],
        "sampler": ["12", 0], "sigmas": ["13", 0], "latent_image": latent}}
    return wf


def _fill(node: Any, values: dict[str, Any]) -> Any:
    """Substitute {{PLACEHOLDERS}} in a user workflow; a value that is exactly a placeholder keeps its native type."""
    if isinstance(node, dict):
        return {k: _fill(v, values) for k, v in node.items()}
    if isinstance(node, list):
        return [_fill(v, values) for v in node]
    if isinstance(node, str):
        for k, v in values.items():
            tag = "{{" + k + "}}"
            if node == tag:
                return v
            if tag in node:
                node = node.replace(tag, str(v))
    return node


# ------------------------------------------------------------------ execution

async def _upload(c: httpx.AsyncClient, base: str, data: bytes, mime: str) -> str:
    ext = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}.get(mime, "png")
    r = await c.post(f"{base}/upload/image", files={"image": (f"las_{uuid.uuid4().hex[:10]}.{ext}", data, mime)}, data={"overwrite": "true"})
    r.raise_for_status()
    j = r.json()
    return f"{j['subfolder']}/{j['name']}" if j.get("subfolder") else j["name"]


def _first_file(outputs: dict, video: bool) -> Optional[dict]:
    files = [f for out in outputs.values() for v in out.values() if isinstance(v, list) for f in v if isinstance(f, dict) and f.get("filename")]
    if video:
        vids = [f for f in files if f["filename"].lower().endswith((".mp4", ".webm", ".mov"))]
        return (vids or files or [None])[0]
    return files[0] if files else None


async def run(
    workflow: dict, video: bool, progress: Progress = None, on_queued: Optional[Callable[[str], Awaitable[None]]] = None,
    s: Optional[dict] = None,
) -> tuple[bytes, str]:
    s = s or await get_settings()
    base = s["base_url"]
    started = time.monotonic()
    try:
        async with _client(60) as c:
            r = await c.post(f"{base}/prompt", json={"prompt": workflow, "client_id": "localaistudio"})
            if r.status_code >= 400:
                detail = r.json() if "json" in r.headers.get("content-type", "") else r.text
                err = detail.get("error", {}).get("message") if isinstance(detail, dict) else str(detail)
                nodes = detail.get("node_errors") if isinstance(detail, dict) else None
                hint = ""
                if nodes:
                    first = next(iter(nodes.values()))
                    hint = " — " + "; ".join(e.get("details") or e.get("message", "") for e in first.get("errors", [])[:2])
                raise ComfyError(f"ComfyUI a refusé le workflow : {err}{hint}"[:400])
            pid = r.json()["prompt_id"]
            if on_queued:
                await on_queued(pid)
            limit = 3600 if video else 900
            while time.monotonic() - started < limit:
                await asyncio.sleep(2)
                h = (await c.get(f"{base}/history/{pid}")).json().get(pid)
                elapsed = int(time.monotonic() - started)
                if not h:
                    if progress:
                        await progress(f"Rendu local sur votre GPU · {elapsed}s")
                    continue
                st = h.get("status", {})
                if st.get("status_str") == "error":
                    msgs = [m[1].get("exception_message", "") for m in st.get("messages", []) if m[0] == "execution_error"]
                    raise ComfyError(f"Erreur ComfyUI : {(msgs or ['exécution interrompue'])[0]}"[:400])
                f = _first_file(h.get("outputs", {}), video)
                if not f:
                    raise ComfyError("ComfyUI n'a produit aucun fichier")
                fr = await c.get(f"{base}/view", params={"filename": f["filename"], "subfolder": f.get("subfolder", ""), "type": f.get("type", "output")})
                fr.raise_for_status()
                mime = fr.headers.get("content-type", "video/mp4" if video else "image/png").split(";")[0]
                return fr.content, mime
            raise ComfyError("Délai de rendu local dépassé")
    except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
        raise ComfyError(unreachable(s)) from exc


async def generate_image(
    prompt: str, aspect: str = "1:1", ref: Optional[tuple[bytes, str]] = None, progress: Progress = None,
    on_queued: Optional[Callable[[str], Awaitable[None]]] = None,
) -> tuple[bytes, str]:
    s = await get_settings()
    w, h = IMAGE_SIZES.get(aspect, IMAGE_SIZES["1:1"])
    seed = random.randint(1, 2**31)
    image = None
    if ref:
        try:
            async with _client() as c:
                image = await _upload(c, s["base_url"], *ref)
        except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
            raise ComfyError(unreachable(s)) from exc
    if s["custom_image_workflow"].strip():
        wf = _fill(json.loads(s["custom_image_workflow"]), {"PROMPT": prompt, "NEGATIVE": NEGATIVE, "WIDTH": w, "HEIGHT": h, "SEED": seed, "IMAGE": image or ""})
    else:
        wf = _image_workflow(s, prompt, w, h, seed, image)
    return await run(wf, False, progress, on_queued, s=s)


async def generate_video(
    prompt: str, duration: str, aspect: str, ref: Optional[tuple[bytes, str]] = None, progress: Progress = None,
    on_queued: Optional[Callable[[str], Awaitable[None]]] = None,
) -> tuple[bytes, str]:
    s = await get_settings()
    w, h = VIDEO_SIZES.get(aspect, VIDEO_SIZES["16:9"])
    length = VIDEO_LENGTHS.get(duration, 73)
    seed = random.randint(1, 2**31)
    image = None
    if ref:
        try:
            async with _client() as c:
                image = await _upload(c, s["base_url"], *ref)
        except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
            raise ComfyError(unreachable(s)) from exc
    if s["custom_video_workflow"].strip():
        wf = _fill(json.loads(s["custom_video_workflow"]), {"PROMPT": prompt, "NEGATIVE": NEGATIVE, "WIDTH": w, "HEIGHT": h, "SEED": seed, "LENGTH": length, "IMAGE": image or ""})
    else:
        wf = _video_workflow(s, prompt, w, h, length, seed, image)
    return await run(wf, True, progress, on_queued, s=s)


async def cancel(prompt_id: str) -> None:
    s = await get_settings()
    async with _client(8) as c:
        await c.post(f"{s['base_url']}/queue", json={"delete": [prompt_id]})
        await c.post(f"{s['base_url']}/interrupt")
