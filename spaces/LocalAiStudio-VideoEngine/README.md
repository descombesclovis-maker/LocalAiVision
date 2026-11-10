---
title: LocalAiStudio Video Engine
emoji: 🎬
colorFrom: indigo
colorTo: purple
sdk: gradio
sdk_version: 6.25.0
python_version: "3.12"
app_file: app.py
license: apache-2.0
short_description: Private LocalAiStudio remote GPU diagnostics.
---

# LocalAiStudio Video Engine

Private Hugging Face Space owned by `clocltrrh`. This Space currently exposes a real remote-GPU diagnostic endpoint. Video generation is deliberately reported as unavailable until its model and every dependency have verified access and licensing.

## Current capability status

- Remote GPU allocation: tested through the `/gpu_check` Gradio API.
- T2V: not enabled. The preferred candidate is SANA-Video 2.0 5B 4-step (T2V-only, Apache-2.0 checkpoint), but its reference pipeline uses the gated `google/gemma-2-2b-it` text encoder. The owner has not accepted/accessed that gated model, so no weights are loaded and no T2V endpoint is advertised as ready.
- I2V: not enabled. The distilled 4-step checkpoint is explicitly T2V-only. The non-distilled SANA 5B checkpoint advertises T2V/TI2V but uses the same gated text encoder and a 50-step inference recipe; it has not been tested here.
- No paid hardware, model download, or external inference call is configured.

The ZeroGPU runtime defaults to the documented `large` allocation (48 GB VRAM). The same GPU wrapper supports explicit `xlarge` (96 GB) via Space variable `LAS_GPU_SIZE=xlarge`; this would consume twice the daily quota and is deliberately not enabled. Hugging Face may change runtime availability and quotas.

## Candidate comparison (not inference-tested here)

- **SANA-Video 2.0 5B 4-step**: preferred T2V candidate by open commercial license and low step count; 4.47B parameters, 720p output; Apache-2.0 checkpoint. The official inference app requires gated `google/gemma-2-2b-it`; that account currently gets HTTP 403, so deployment is blocked pending the model's access/terms acceptance. This distilled checkpoint is T2V only, not I2V.
- **SANA-Video 2.0 5B base**: model card advertises T2V/TI2V and Apache-2.0, but uses the same gated encoder and a 50-step recipe. No latency or quality test on this Space.
- **Wan2.2 TI2V 5B**: official model card declares Apache-2.0, T2V+I2V at 720p/24fps, and says the full 5B pipeline requires at least 24 GB VRAM with CPU offload. It is a plausible 48 GB candidate, but no ZeroGPU compatibility, duration, download, or generation has been tested.
- **Wan2.1 T2V 1.3B**: Apache-2.0; official card reports 8.19 GB VRAM and recommends 480p; lower quality/resolution ceiling than the 5B candidate. No ZeroGPU test here.
- **LTX-2.3**: 19B parameters in the Diffusers listing. It offers stronger prior visual results, but is covered by the LTX-2 Community License (not Apache/MIT); commercial rights are conditional, including a revenue threshold and other restrictions. Fit/speed on the 48 GB slice has not been established; not selected.

Only one GPU workload/model may be active in a future generation process; the current app loads no model weights.

## Remaining prerequisite for generation

The account owner must review and accept the gated Gemma model terms/access at https://huggingface.co/google/gemma-2-2b-it. The current credential's access check returned HTTP 403. Do not copy a token into Space secrets or widen its permission for this: hosted model download could use an appropriately scoped read token only after the owner accepts those model terms. Once unblocked, add a read-only repository-scoped/fine-grained permission for the approved model if required, then separately test memory/latency before exposing generation endpoints.

The current API is private and uses the normal Hugging Face bearer-authenticated Gradio API. It does not expose a public unauthenticated video-generation endpoint.

## API

The authenticated Gradio API endpoint `/gpu_check` briefly requests the remote GPU and returns its device, total/free VRAM, CUDA/PyTorch versions, and a small CUDA operation result. `/engine_status` reports the honest model readiness state without allocating a GPU.

This Space is private. Use an authorized Hugging Face token with read access to call its API. Never place a token in this repository or in client-side UI code.

## Terms and attribution

The diagnostic application files are licensed under Apache-2.0. This does not grant rights to external model components. Before enabling SANA, review and accept the Gemma terms for the associated account and review the full dependency licenses. The SANA 4-step checkpoint itself declares Apache-2.0 and is T2V-only.

ZeroGPU allocation is quota-limited and does not imply unlimited or guaranteed capacity. No paid fallback is configured.
