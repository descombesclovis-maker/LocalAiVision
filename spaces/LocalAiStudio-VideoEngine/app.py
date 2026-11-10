"""Private LocalAiStudio video Space: SANA 2.0 T2V and remote GPU diagnostics.

The model is loaded only after a read-scoped HF_TOKEN secret is configured and
remote cache capacity passes a no-download preflight. The checkpoint is T2V-only.
"""
from __future__ import annotations

import os
import traceback

import spaces  # Must precede torch and CUDA-touching imports.
import gradio as gr
import torch

from engine_registry import engine_status, gpu_size_from_env
from storage_preflight import storage_report

GPU_SIZE = gpu_size_from_env()
SANA_GENERATE = None
SANA_LOAD_ERROR: str | None = None
STORAGE = storage_report()

# The Gemma text encoder is gated. Do not use a broader credential implicitly,
# and do not start large downloads unless the Space has enough disk headroom.
if os.environ.get("HF_TOKEN"):
    if not STORAGE["sufficient"]:
        SANA_LOAD_ERROR = "InsufficientStorage"
        print("SANA load skipped: remote model-cache disk preflight failed.", flush=True)
    else:
        try:
            from sana_runtime import generate as SANA_GENERATE  # noqa: F401
        except Exception as exc:  # Keep health/status endpoints available on startup failure.
            SANA_LOAD_ERROR = type(exc).__name__
            print(f"SANA runtime load failed: {type(exc).__name__}", flush=True)
            traceback.print_exc()


def health() -> dict[str, object]:
    return {
        "space": "clocltrrh/LocalAiStudio-VideoEngine",
        "app_ready": True,
        "generation_ready": SANA_GENERATE is not None,
        "model": "sana-video-2.0-5b-4step" if SANA_GENERATE is not None else None,
        "supported_tasks": ["t2v"] if SANA_GENERATE is not None else [],
    }


def status() -> dict[str, object]:
    result = engine_status(model_loaded=SANA_GENERATE is not None, load_error=SANA_LOAD_ERROR)
    result["storage"] = STORAGE
    return result


def storage_status() -> dict[str, object]:
    """Read-only remote disk preflight; never allocates a GPU or downloads files."""
    return storage_report()


@spaces.GPU(duration=15, size=GPU_SIZE)
@torch.inference_mode()
def gpu_check() -> dict[str, object]:
    """Minimal remote CUDA diagnostic; calling this consumes GPU quota."""
    if not torch.cuda.is_available():
        raise gr.Error("No remote CUDA device was allocated for this request.")
    device = torch.device("cuda:0")
    props = torch.cuda.get_device_properties(device)
    free_bytes, total_bytes = torch.cuda.mem_get_info(device)
    value = torch.ones((256, 256), dtype=torch.float16, device=device)
    checksum = float((value @ value)[0, 0].item())
    torch.cuda.synchronize(device)
    result = {
        "gpu_allocated": True,
        "device_name": props.name,
        "total_vram_mib": round(total_bytes / 2**20),
        "free_vram_mib": round(free_bytes / 2**20),
        "cuda_version": torch.version.cuda,
        "torch_version": torch.__version__,
        "checksum": checksum,
    }
    del value
    torch.cuda.empty_cache()
    return result


def unavailable(*_args):
    raise gr.Error(status()["reason"])


with gr.Blocks(title="LocalAiStudio Video Engine") as demo:
    gr.Markdown("# LocalAiStudio Video Engine\nRemote video generation status and supported controls.")
    with gr.Row():
        health_button = gr.Button("Health")
        status_button = gr.Button("Engine status")
        storage_button = gr.Button("Check remote storage")
        gpu_button = gr.Button("Check remote GPU")
    health_output = gr.JSON(label="Application health")
    status_output = gr.JSON(label="Engine status")
    storage_output = gr.JSON(label="Remote storage preflight")
    gpu_output = gr.JSON(label="Remote GPU diagnostic")
    health_button.click(health, outputs=health_output, api_name="health")
    status_button.click(status, outputs=status_output, api_name="engine_status")
    storage_button.click(storage_status, outputs=storage_output, api_name="storage_status")
    gpu_button.click(gpu_check, outputs=gpu_output, api_name="gpu_check")

    prompt = gr.Textbox(label="Text prompt", lines=5, placeholder="Describe the scene")
    duration = gr.Radio(["5 seconds", "8 seconds"], value="5 seconds", label="Validated duration")
    lora_scale = gr.Slider(0.3, 1.0, value=0.7, step=0.1, label="Preview style strength")
    motion_score = gr.Slider(0, 100, value=20, step=1, label="Motion score")
    seed = gr.Number(value=4, precision=0, label="Seed")
    randomize_seed = gr.Checkbox(value=False, label="Randomize seed")
    generate_button = gr.Button("Generate T2V", interactive=SANA_GENERATE is not None)
    video_output = gr.Video(label="Generated video")
    seed_output = gr.Number(label="Used seed", precision=0)
    if SANA_GENERATE is not None:
        generate_button.click(
            SANA_GENERATE,
            inputs=[prompt, duration, lora_scale, motion_score, seed, randomize_seed],
            outputs=[video_output, seed_output],
            api_name="generate",
        )
    else:
        generate_button.click(unavailable, inputs=[prompt], outputs=[video_output], api_name="generate")

    gr.Markdown(
        "SANA-Video 2.0 5B four-step preview supports T2V only: 1280×736, "
        "5 seconds at 16 FPS or 8 seconds at 24 FPS. I2V is not enabled."
    )


demo.queue(max_size=8).launch()
