---
title: LocalAiStudio Video Engine
emoji: 🎬
colorFrom: indigo
colorTo: purple
sdk: gradio
sdk_version: 6.25.0
python_version: "3.12"
app_file: app.py
startup_duration_timeout: 1h
license: apache-2.0
short_description: Private SANA-Video T2V Space and diagnostics.
models:
  - Efficient-Large-Model/SANA-Video_2.0_5B_720p_4step
  - Efficient-Large-Model/LTX-2.3-Diffusers
  - google/gemma-2-2b-it
---

# LocalAiStudio Video Engine

Private Hugging Face Space owned by `clocltrrh`. The selected first-generation engine is the official **SANA-Video 2.0 5B four-step preview**. The implementation is adapted from the official `Efficient-Large-Model/sana-video2-5b-720p-demo` Space and upstream NVlabs SANA code; the included upstream Apache-2.0 license and attribution are preserved.

## Current capability contract

- **T2V:** supported by the selected four-step preview after dependencies and weights load successfully.
- **I2V:** not supported by this distilled checkpoint. Do not route image-conditioned requests to it. A separate model/workflow is required and has not been loaded.
- **Validated output buckets only:** 1280×736, 5 seconds (81 frames at 16 FPS) or 8 seconds (193 frames at 24 FPS).
- **Sampler:** DMD four-stage schedule, BF16, CFG 1.0, fixed release sigmas. This is a research preview, not a guarantee of production fidelity.
- **GPU:** ZeroGPU `large` by default (48 GB). `xlarge` (96 GB) requires explicit configuration and costs 2× quota; it is not enabled.
- **Quota:** HF currently documents 5 minutes/day for authenticated Free users. Account-specific remaining quota is not exposed by this app. A generation may be rejected when quota is exhausted. No paid fallback or credits are configured.

## Credentials and remote storage (not local PC)

The Gemma text encoder is gated; current credentials have been verified to have accepted/access to `google/gemma-2-2b-it`. Do not copy the desktop login credential into the Space. The reference loader checks `HF_TOKEN`; configure a dedicated fine-grained read-only token secret scoped to the Gemma model repository. SANA weights, RL scale adapter, VAE, and Gemma together total approximately **25.2 GB** before runtime overhead. The live no-download `/storage_status` check reported about **2.0 TiB free** in the remote Space, above the 30 GiB safety threshold. The secret is still absent, so model downloads/loading remain disabled. No large model is downloaded to the user's PC.

The LTX-2.3 VAE is required by SANA's reference pipeline. Its license is separate from the SANA checkpoint; review the LTX-2 Community License before commercial deployment. Gemma use is subject to Google's Gemma Terms. Apache-2.0 on the SANA checkpoint does not override component licenses.

## API

Authenticated Gradio API endpoints:

- `/health`: application readiness and supported task names.
- `/engine_status`: model load state, selected checkpoint, output profiles, and truthful limitations.
- `/storage_status`: read-only remote disk headroom check; no GPU use or downloads.
- `/gpu_check`: small CUDA diagnostic (consumes GPU quota).
- `/generate`: T2V, unavailable until model startup completes. Inputs follow the API schema in the running Gradio app; outputs are an MP4 file and used seed.

The Space is private. API calls require a Hugging Face read token for the Space. Keep client credentials server-side; never put them in LocalAiStudio browser code.

## Components and terms

- SANA-Video 2.0 5B 4-step checkpoint: Apache-2.0; T2V-only early research preview.
- Gemma 2 2B Instruct text encoder: Google's Gemma Terms and gated access.
- LTX-2.3 Diffusers VAE: separately licensed complementary model component; commercial rights are conditional under the LTX-2 Community License.
- Upstream SANA source: Apache-2.0; see `LICENSE`.

No model artifacts are committed to this Space repository, and none are downloaded to the local PC. GPU inference is intended to use the official Hugging Face Spaces allocation; only free account quota is authorized.
