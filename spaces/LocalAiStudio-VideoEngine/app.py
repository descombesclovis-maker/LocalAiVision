"""Private LocalAiStudio remote GPU diagnostic Space.

Import `spaces` before torch/CUDA-touching libraries as required by ZeroGPU.
This diagnostic deliberately loads no video model and performs no inference.
"""
from __future__ import annotations

import spaces  # Must be imported before torch.
import gradio as gr
import torch

from engine_registry import engine_status, gpu_size_from_env


GPU_SIZE = gpu_size_from_env()


@spaces.GPU(duration=15, size=GPU_SIZE)
@torch.inference_mode()
def gpu_check() -> dict[str, object]:
    """Request the Space GPU and run a tiny allocation/kernel/sync check."""
    if not torch.cuda.is_available():
        raise gr.Error("No remote CUDA device was allocated for this request.")

    device = torch.device("cuda:0")
    props = torch.cuda.get_device_properties(device)
    free_bytes, total_bytes = torch.cuda.mem_get_info(device)
    x = torch.ones((256, 256), dtype=torch.float16, device=device)
    y = x @ x
    checksum = float(y[0, 0].item())
    torch.cuda.synchronize(device)
    allocated_bytes = torch.cuda.memory_allocated(device)
    del x, y
    torch.cuda.empty_cache()

    return {
        "gpu_allocated": True,
        "device_name": props.name,
        "compute_capability": f"{props.major}.{props.minor}",
        "total_vram_mib": round(total_bytes / 2**20),
        "free_vram_mib_during_check": round(free_bytes / 2**20),
        "torch_allocated_mib_during_check": round(allocated_bytes / 2**20),
        "cuda_version": torch.version.cuda,
        "torch_version": torch.__version__,
        "cuda_kernel_checksum": checksum,
        "generation_ready": False,
        "note": "GPU diagnostic only; no video model is loaded or inferred.",
    }


def health() -> dict[str, object]:
    return {
        "space": "clocltrrh/LocalAiStudio-VideoEngine",
        "app_ready": True,
        "generation_ready": False,
        "gpu_check_endpoint": "/gpu_check",
        "engine_status_endpoint": "/engine_status",
    }


with gr.Blocks(title="LocalAiStudio Video Engine") as demo:
    gr.Markdown(
        "# LocalAiStudio Video Engine\n"
        "Remote compute status and diagnostics. Video generation is not enabled until a model and all required dependencies are verified."
    )
    with gr.Row():
        gpu_button = gr.Button("Check remote GPU")
        status_button = gr.Button("Check engine readiness")
    gpu_result = gr.JSON(label="Remote GPU diagnostic")
    status_result = gr.JSON(label="Engine readiness")
    gpu_button.click(gpu_check, outputs=gpu_result, api_name="gpu_check")
    status_button.click(engine_status, outputs=status_result, api_name="engine_status")

demo.queue(max_size=8).launch()
