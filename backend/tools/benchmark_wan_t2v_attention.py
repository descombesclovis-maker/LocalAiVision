import asyncio
import ctypes
import hashlib
import json
import os
import subprocess
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import httpx
import websockets

BASE = "http://127.0.0.1:8188"
PROMPT = "Un chien noir saute par-dessus une petite barrière rouge, de gauche à droite, puis s'assoit devant la barrière. Plan fixe, sans autre animal."
OUT = Path(__file__).resolve().parents[1] / "bench_runs" / "v2s"
MODEL_ROOT = Path(os.environ.get("COMFY_SHARED_MODELS", str(Path.home() / "AppData/Local/Comfy-Desktop/ComfyUI-Shared/models")))

class MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]

def mem_sample():
    s = MEMORYSTATUSEX(); s.dwLength = ctypes.sizeof(s)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(s))
    return {"ram_used_mib": round((s.ullTotalPhys-s.ullAvailPhys)/1048576),
            "ram_available_mib": round(s.ullAvailPhys/1048576)}

def gpu_sample():
    try:
        out = subprocess.check_output(["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total,power.draw", "--format=csv,noheader,nounits"], text=True, timeout=3).strip().splitlines()[0]
        u,m,t,p = [x.strip() for x in out.split(",")]
        return {"gpu_util_pct": int(u), "vram_used_mib": int(m), "vram_total_mib": int(t), "power_w": float(p)}
    except Exception as e:
        return {"gpu_sample_error": str(e)}

def workflow(backend, steps, suffix):
    # Diagnostic-only tiny latent (not a quality sample): 256x256, 5 frames.
    seed = 20261110
    wf = {
      "1": {"class_type":"UNETLoader","inputs":{"unet_name":"wan2.1_t2v_1.3B_fp16.safetensors","weight_dtype":"default"}},
      "2": {"class_type":"CLIPLoader","inputs":{"clip_name":"umt5_xxl_fp8_e4m3fn_scaled.safetensors","type":"wan","device":"default"}},
      "3": {"class_type":"VAELoader","inputs":{"vae_name":"wan_2.1_vae.safetensors"}},
      "4": {"class_type":"ModelSamplingSD3","inputs":{"model":["1",0],"shift":8.0}},
      "5": {"class_type":"CLIPTextEncode","inputs":{"text":PROMPT,"clip":["2",0]}},
      "6": {"class_type":"CLIPTextEncode","inputs":{"text":"static, blurry, low quality, distorted, watermark, text, jitter, deformed","clip":["2",0]}},
      "7": {"class_type":"WanImageToVideo","inputs":{"positive":["5",0],"negative":["6",0],"vae":["3",0],"width":256,"height":256,"length":5,"batch_size":1}},
      "9": {"class_type":"KSampler","inputs":{"model":["4",0],"positive":["7",0],"negative":["7",1],"latent_image":["7",2],"seed":seed,"steps":steps,"cfg":6.0,"sampler_name":"uni_pc","scheduler":"simple","denoise":1.0}},
      "8": {"class_type":"VAEDecode","inputs":{"samples":["9",0],"vae":["3",0]}},
      "20": {"class_type":"CreateVideo","inputs":{"images":["8",0],"fps":24}},
      "21": {"class_type":"SaveVideo","inputs":{"video":["20",0],"filename_prefix":f"v2s/{suffix}","format":"mp4","codec":"h264"}},
    }
    if backend == "Comfy Kitchen attention":
        wf["12"] = {"class_type":"ModelAttentionBackend","inputs":{"model":["1",0],"attention":backend}}
        wf["4"]["inputs"]["model"] = ["12",0]
    return wf

async def run_one(backend, steps, suffix, timeout_s=90):
    client_id = uuid.uuid4().hex
    ws_uri = f"ws://127.0.0.1:8188/ws?clientId={client_id}"
    result = {"backend":backend,"steps_requested":steps,"prompt_fr":PROMPT,"seed":20261110,
              "started_utc":datetime.now(timezone.utc).isoformat(),"samples":[],"step_events":[],"node_events":[]}
    start = time.perf_counter()
    async with httpx.AsyncClient(timeout=20) as client:
      async with websockets.connect(ws_uri, max_size=None) as ws:
        r = await client.post(f"{BASE}/prompt", json={"prompt":workflow(backend,steps,suffix),"client_id":client_id})
        r.raise_for_status(); posted = r.json(); result["prompt_id"] = posted.get("prompt_id")
        result["http_post_s"] = round(time.perf_counter()-start,3)
        next_sample = 0.0
        while time.perf_counter()-start < timeout_s:
            elapsed = time.perf_counter()-start
            if elapsed >= next_sample:
                result["samples"].append({"elapsed_s":round(elapsed,3),**mem_sample(),**gpu_sample()})
                next_sample = elapsed + 1.5
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=0.35)
            except asyncio.TimeoutError:
                continue
            if not isinstance(raw,str): continue
            try: msg=json.loads(raw)
            except Exception: continue
            typ=msg.get("type"); data=msg.get("data",{})
            if data.get("prompt_id") not in (None,result["prompt_id"]): continue
            if typ == "progress":
                result["step_events"].append({"elapsed_s":round(time.perf_counter()-start,3),"value":data.get("value"),"max":data.get("max"),"node":data.get("node")})
            elif typ == "executing":
                result["node_events"].append({"elapsed_s":round(time.perf_counter()-start,3),"node":data.get("node")})
            elif typ in ("execution_success","execution_error","execution_interrupted"):
                result["terminal_event"]={"type":typ,"elapsed_s":round(time.perf_counter()-start,3),"data":data}
                break
        if "terminal_event" not in result:
            result["timed_out"] = True
            try:
                await client.post(f"{BASE}/interrupt", timeout=5)
                result["cancel_requested"] = True
            except Exception as exc:
                result["cancel_error"] = str(exc)
    result["total_s"] = round(time.perf_counter()-start,3)
    result["ended_utc"] = datetime.now(timezone.utc).isoformat()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT/f"{suffix}.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"suffix":suffix,"backend":backend,"steps":steps,"total_s":result["total_s"],"terminal":result.get("terminal_event"),"progress_events":result["step_events"],"max_ram_used_mib":max((x.get("ram_used_mib",0) for x in result["samples"]),default=None),"max_vram_used_mib":max((x.get("vram_used_mib",0) for x in result["samples"]),default=None),"max_gpu_util_pct":max((x.get("gpu_util_pct",0) for x in result["samples"]),default=None)},ensure_ascii=False),flush=True)
    return result

async def main():
    model_paths = [
      MODEL_ROOT / "diffusion_models/wan2.1_t2v_1.3B_fp16.safetensors",
      MODEL_ROOT / "text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors",
      MODEL_ROOT / "vae/wan_2.1_vae.safetensors",
    ]
    for path in model_paths:
        if not path.is_file(): raise SystemExit(f"Missing model: {path} (set COMFY_SHARED_MODELS if needed)")
    checkpoint=model_paths[0]
    print("checkpoint_sha256",hashlib.file_digest(checkpoint.open('rb'),'sha256').hexdigest(),flush=True)
    statuses = httpx.get(f"{BASE}/queue",timeout=5).json()
    if statuses.get("queue_running") or statuses.get("queue_pending"):
        raise SystemExit("ComfyUI busy; refusing to contend with another job")
    # One denoise iteration only: measures compatibility + cost on a deliberately
    # tiny, non-quality workload. It cannot be used to claim production speed.
    baseline=await run_one("pytorch attention",1,"baseline_256_5f_1step",timeout_s=90)
    if baseline.get("terminal_event",{}).get("type") != "execution_success":
        print("Tiny baseline did not complete; stop. No attention A/B.",flush=True); return
    await asyncio.sleep(8)
    await run_one("Comfy Kitchen attention",1,"int8_256_5f_1step",timeout_s=90)

if __name__ == "__main__": asyncio.run(main())
