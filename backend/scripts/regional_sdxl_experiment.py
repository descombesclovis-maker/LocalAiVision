"""Experiment (not used by the app): SDXL regional prompting with ComfyUI core nodes.

Variants (same checkpoint, size, steps, CFG, sampler, scheduler and seeds):
  base_fr    single French prompt of the existing benchmark (corpus case photo_spatial_product, A0_raw)
  base_en    the same content as one English prompt (control for language)
  region_en  global prompt + bottle region (centre) + cap region (right), combined with ConditioningCombine

Ollama is unloaded before rendering so timings are not skewed by VRAM sharing. Renders run one at a time.
Outputs go to backend/bench_runs/regional_sdxl/<stamp>/ (gitignored). No subjective scores are written here.

Usage: python scripts/regional_sdxl_experiment.py [--seeds 1001 1002 ...]
"""

import argparse
import datetime
import json
import pathlib
import sys
import time
import urllib.request
import uuid

import os  # noqa: E402

BACKEND = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
# lib.comfy imports the DB layer at import time; no connection is opened by this script.
os.environ.setdefault("MONGO_URL", "mongodb://127.0.0.1:27017")
os.environ.setdefault("DB_NAME", "localaistudio_nextgen_original")
from lib.comfy import NEGATIVE  # noqa: E402  (same negative prompt as the app)

COMFY = "http://127.0.0.1:8188"
OLLAMA = "http://127.0.0.1:11434"
CKPT = "sd_xl_base_1.0.safetensors"
SIZE = 1024
STEPS = 30
CFG = 6.5
SAMPLER = "dpmpp_2m"
SCHEDULER = "karras"

FR_PROMPT = ("Un flacon de parfum bleu au centre avec son bouchon doré posé séparément à droite, "
             "sur une surface en marbre blanc.")
EN_SINGLE = ("a blue perfume bottle in the center with a separate gold cap on the right, "
             "on a white marble surface, photorealistic")
EN_GLOBAL = "product photo on a white marble surface, soft studio lighting, photorealistic, sharp focus"
EN_BOTTLE = "a blue perfume bottle, photorealistic, sharp focus"
EN_CAP = "a separate gold perfume bottle cap, lying on the marble to the right of the bottle"
# Region boxes in pixels of the 1024x1024 image (multiples of 8): bottle = centre column, cap = right band.
BOTTLE_BOX = {"width": 512, "height": 768, "x": 256, "y": 128}
CAP_BOX = {"width": 256, "height": 256, "x": 768, "y": 448}


def _json(url, body=None, timeout=30):
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"} if data else {})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8") or "null")


def unload_ollama():
    ps = _json(f"{OLLAMA}/api/ps")
    models = [m["name"] for m in (ps or {}).get("models", [])]
    for name in models:
        _json(f"{OLLAMA}/api/generate", {"model": name, "keep_alive": 0})
    still = [m["name"] for m in (_json(f"{OLLAMA}/api/ps") or {}).get("models", [])]
    print(f"ollama: unloaded={models} remaining={still}")
    if still:
        raise SystemExit("Ollama still holds VRAM; aborting measurements")


def base_workflow(text, seed, prefix):
    return {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": CKPT}},
        "2": {"class_type": "CLIPTextEncode", "inputs": {"text": text, "clip": ["1", 1]}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"text": NEGATIVE, "clip": ["1", 1]}},
        "4": {"class_type": "EmptyLatentImage", "inputs": {"width": SIZE, "height": SIZE, "batch_size": 1}},
        "5": {"class_type": "KSampler", "inputs": {
            "model": ["1", 0], "positive": ["2", 0], "negative": ["3", 0], "latent_image": ["4", 0],
            "seed": seed, "steps": STEPS, "cfg": CFG, "sampler_name": SAMPLER, "scheduler": SCHEDULER,
            "denoise": 1.0}},
        "6": {"class_type": "VAEDecode", "inputs": {"samples": ["5", 0], "vae": ["1", 2]}},
        "7": {"class_type": "SaveImage", "inputs": {"filename_prefix": prefix, "images": ["6", 0]}},
    }


def regional_workflow(seed, prefix):
    wf = base_workflow(EN_GLOBAL, seed, prefix)
    wf["8"] = {"class_type": "CLIPTextEncode", "inputs": {"text": EN_BOTTLE, "clip": ["1", 1]}}
    wf["9"] = {"class_type": "CLIPTextEncode", "inputs": {"text": EN_CAP, "clip": ["1", 1]}}
    wf["10"] = {"class_type": "ConditioningSetArea", "inputs": {
        "conditioning": ["8", 0], "strength": 1.0, **BOTTLE_BOX}}
    wf["11"] = {"class_type": "ConditioningSetArea", "inputs": {
        "conditioning": ["9", 0], "strength": 1.0, **CAP_BOX}}
    wf["12"] = {"class_type": "ConditioningCombine", "inputs": {"conditioning_1": ["10", 0], "conditioning_2": ["11", 0]}}
    wf["13"] = {"class_type": "ConditioningCombine", "inputs": {"conditioning_1": ["12", 0], "conditioning_2": ["2", 0]}}
    wf["5"]["inputs"]["positive"] = ["13", 0]
    return wf


VARIANTS = {
    "base_fr": lambda seed, p: base_workflow(FR_PROMPT, seed, p),
    "base_en": lambda seed, p: base_workflow(EN_SINGLE, seed, p),
    "region_en": lambda seed, p: regional_workflow(seed, p),
}


def render(workflow, out_file):
    t0 = time.time()
    resp = _json(f"{COMFY}/prompt", {"prompt": workflow, "client_id": str(uuid.uuid4())})
    pid = resp["prompt_id"]
    while True:
        time.sleep(0.5)
        hist = _json(f"{COMFY}/history/{pid}", timeout=30)
        if pid in hist:
            entry = hist[pid]
            status = entry.get("status", {})
            if status.get("status_str") == "error":
                raise RuntimeError(f"ComfyUI error for {pid}: {str(status)[:300]}")
            outputs = [img for node in entry.get("outputs", {}).values() for img in node.get("images", [])]
            if not outputs:
                continue
            img = outputs[0]
            qs = f"filename={img['filename']}&subfolder={img.get('subfolder', '')}&type={img.get('type', 'output')}"
            with urllib.request.urlopen(f"{COMFY}/view?{qs}", timeout=60) as r:
                out_file.write_bytes(r.read())
            return time.time() - t0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", nargs="+", type=int, default=[1001, 1002, 1003, 1004, 1005, 1006, 1007, 1008])
    args = ap.parse_args()
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    out = BACKEND / "bench_runs" / "regional_sdxl" / stamp
    out.mkdir(parents=True, exist_ok=True)
    unload_ollama()
    results = []
    for seed in args.seeds:
        for name, build in VARIANTS.items():
            file = out / f"{name}_{seed}.png"
            prefix = f"regional_exp/{name}_{seed}"
            dur = render(build(seed, prefix), file)
            results.append({"variant": name, "seed": seed, "seconds": round(dur, 2), "file": file.name})
            print(f"{name:10s} seed={seed} {dur:6.1f}s", flush=True)
    (out / "results.json").write_text(json.dumps({
        "stamp": stamp, "ckpt": CKPT, "size": SIZE, "steps": STEPS, "cfg": CFG, "sampler": SAMPLER,
        "scheduler": SCHEDULER, "bottle_box": BOTTLE_BOX, "cap_box": CAP_BOX, "runs": results,
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    print("out:", out)


if __name__ == "__main__":
    main()
