"""SANA-Video 2.0 5B 720p — four-step text-to-video preview.

The DMD sampler, prompt construction, latent layout and VAE post-processing
mirror the authors' verified four-step inference command. The original
50-step T2V + TI2V release remains available from the linked base model.
"""

from __future__ import annotations

import os

os.environ.setdefault("DISABLE_XFORMERS", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

# isort: off
import spaces  # noqa: E402  (must precede torch / CUDA-touching imports)
from preview_controls import (  # noqa: E402
    DEFAULT_MOTION_SCORE,
    DEFAULT_RL_LORA_SCALE,
    DEFAULT_VIDEO_DURATION,
    MAX_MOTION_SCORE,
    MAX_RL_LORA_SCALE,
    MIN_MOTION_SCORE,
    MIN_RL_LORA_SCALE,
    REFERENCE_RL_LORA_SCALE,
    RL_LORA_SCALE_STEP,
    VIDEO_PROFILES,
    get_video_profile,
    lora_adjustment_coefficient,
    motion_suffix,
    normalize_base_prompt,
    normalize_lora_scale,
    normalize_motion_score,
)

# isort: on

import gc  # noqa: E402
import random  # noqa: E402
import tempfile  # noqa: E402
import threading  # noqa: E402
import time  # noqa: E402

import gradio as gr  # noqa: E402
import imageio  # noqa: E402
import pyrallis  # noqa: E402
import torch  # noqa: E402
from accelerate import init_empty_weights  # noqa: E402
from huggingface_hub import hf_hub_download, snapshot_download  # noqa: E402

from diffusion import FastVideoDMD4Step  # noqa: E402
from diffusion.model.builder import (  # noqa: E402
    build_model,
    get_tokenizer_and_text_encoder,
    get_vae,
    vae_decode,
)
from diffusion.model.utils import get_weight_dtype  # noqa: E402
from diffusion.utils.config import SanaVideoConfig, model_video_init_config  # noqa: E402

# --------------------------------------------------------------------------------------
# Constants taken from the released config / the authors' verified commands
# --------------------------------------------------------------------------------------
MODEL_ID = "Efficient-Large-Model/SANA-Video_2.0_5B_720p_4step"
CKPT_FILE = "checkpoints/SANA_Video_2.0_5B_720p_4step.pth"
RL_LORA_FILE = "adapters/SANA_Video_2.0_5B_720p_RL500_LoRA_rank128.pt"
VAE_ID = "Efficient-Large-Model/LTX-2.3-Diffusers"
CONFIG_PATH = "configs/sana_video2/SanaVideo2_5B_720p.yaml"

# The only inference bucket the reference exposes for 720p:
# ASPECT_RATIO_VIDEO_720_TEST_DIV32 == {"0.57": (736.0, 1280.0)}
VIDEO_HEIGHT, VIDEO_WIDTH = 736, 1280
MODEL_CONSTRUCTION_IMAGE_SIZE = 480

# Authors' verified DMD preview settings. The schedule is fixed by training.
DEFAULT_STEPS = 4
DEFAULT_CFG = 1.0
GENERATOR_SIGMA_PROFILE = "sana_shift6_dpm"
MAX_SEED = 2**31 - 1
DEFAULT_SEED = 4

EXPECTED_LORA_FORMAT = "sana_video20_refl_lora_v1"
EXPECTED_LORA_GLOBAL_STEP = 500
EXPECTED_LORA_RANK = 128
EXPECTED_LORA_ALPHA = 256.0
EXPECTED_LORA_MODULES = 256
EXPECTED_LORA_TARGET_ELEMENTS = 4_194_304_000
EXPECTED_PUBLIC_LORA_BYTES = 587_418_315

torch.set_grad_enabled(False)


class RLLoRAScaleController:
    """Reconstruct the latest DMD model at a requested RL LoRA multiplier.

    The latest full checkpoint is the scale=1 reference. For every scale change
    we start from immutable CPU BF16 copies of the 256 target weights and apply
    ``(scale - 1) * (alpha / rank) * (B @ A)``. This keeps repeated requests
    deterministic and prevents cumulative BF16 drift.
    """

    def __init__(self, path: str) -> None:
        if os.path.getsize(path) != EXPECTED_PUBLIC_LORA_BYTES:
            raise RuntimeError("Public RL LoRA file size does not match the validated release artifact.")

        payload = torch.load(path, map_location="cpu", mmap=True, weights_only=True)
        if not isinstance(payload, dict):
            raise TypeError("RL LoRA checkpoint must be a mapping.")
        if payload.get("format") != EXPECTED_LORA_FORMAT or payload.get("global_step") != EXPECTED_LORA_GLOBAL_STEP:
            raise RuntimeError("RL LoRA checkpoint identity does not match the release contract.")

        config = payload.get("lora_config")
        state = payload.get("lora_state_dict")
        release_metadata = payload.get("release_metadata")
        if not isinstance(config, dict) or not isinstance(state, dict):
            raise TypeError("RL LoRA checkpoint is missing its config or tensor mapping.")
        if not isinstance(release_metadata, dict):
            raise TypeError("RL LoRA checkpoint is missing public release metadata.")
        if (
            release_metadata.get("intended_model") != MODEL_ID
            or float(release_metadata.get("full_model_reference_scale", -1)) != REFERENCE_RL_LORA_SCALE
            or float(release_metadata.get("space_default_scale", -1)) != DEFAULT_RL_LORA_SCALE
            or release_metadata.get("space_supported_scale_range") != [MIN_RL_LORA_SCALE, MAX_RL_LORA_SCALE]
        ):
            raise RuntimeError("RL LoRA release metadata does not target this preview model.")

        module_names = config.get("matched_module_names")
        rank = int(config.get("rank", -1))
        alpha = float(config.get("alpha", float("nan")))
        if (
            not isinstance(module_names, list)
            or len(module_names) != EXPECTED_LORA_MODULES
            or len(set(module_names)) != EXPECTED_LORA_MODULES
            or rank != EXPECTED_LORA_RANK
            or alpha != EXPECTED_LORA_ALPHA
        ):
            raise RuntimeError("RL LoRA rank, alpha, or module coverage has drifted.")

        expected_keys = {f"{name}.{suffix}" for name in module_names for suffix in ("lora_A", "lora_B")}
        if set(state) != expected_keys or any(not torch.is_tensor(value) for value in state.values()):
            raise RuntimeError("RL LoRA tensor coverage does not match the release contract.")

        self.module_names = tuple(module_names)
        self.rank = rank
        self.alpha = alpha
        self.intrinsic_scaling = alpha / rank
        self.state = state
        self.payload = payload  # Keep mmap-backed adapter tensors alive.
        self.reference: dict[str, torch.Tensor] | None = None
        self.parameters: dict[str, torch.nn.Parameter] = {}
        self.current_scale = REFERENCE_RL_LORA_SCALE

    def capture_reference(self, state_dict: dict[str, torch.Tensor]) -> dict[str, torch.Tensor]:
        """Capture immutable scale=1 target weights before model assignment."""
        references: dict[str, torch.Tensor] = {}
        target_elements = 0
        for name in self.module_names:
            key = f"{name}.weight"
            if key not in state_dict:
                raise KeyError(f"Full checkpoint is missing RL LoRA target {key}.")
            weight = state_dict[key]
            lora_a = self.state[f"{name}.lora_A"]
            lora_b = self.state[f"{name}.lora_B"]
            if tuple(lora_a.shape) != (self.rank, weight.shape[1]) or tuple(lora_b.shape) != (
                weight.shape[0],
                self.rank,
            ):
                raise RuntimeError(f"RL LoRA shape mismatch for {name}.")
            references[key] = weight.detach().to(device="cpu", dtype=torch.bfloat16).clone()
            target_elements += weight.numel()
        if target_elements != EXPECTED_LORA_TARGET_ELEMENTS:
            raise RuntimeError("RL LoRA target parameter coverage does not match the release contract.")
        return references

    def register_model(
        self,
        model: torch.nn.Module,
        reference: dict[str, torch.Tensor],
    ) -> None:
        """Bind validated target parameters after the full model reaches CUDA."""
        named_parameters = dict(model.named_parameters())
        selected: dict[str, torch.nn.Parameter] = {}
        for name in self.module_names:
            key = f"{name}.weight"
            parameter = named_parameters.get(key)
            if parameter is None or tuple(parameter.shape) != tuple(reference[key].shape):
                raise RuntimeError(f"Loaded model does not expose RL LoRA target {key}.")
            if parameter.device.type != "cuda":
                raise RuntimeError(f"RL LoRA target is not on CUDA: {key}.")
            selected[key] = parameter
        self.reference = reference
        self.parameters = selected

    @torch.inference_mode()
    def apply_scale(self, requested_scale: int | float) -> float:
        """Reconstruct weights from the immutable scale=1 reference."""
        scale = normalize_lora_scale(requested_scale)
        if scale == self.current_scale:
            return 0.0
        if self.reference is None or len(self.parameters) != len(self.module_names):
            raise RuntimeError("RL LoRA controller is not bound to the model.")

        coefficient = lora_adjustment_coefficient(scale, self.intrinsic_scaling)
        started = time.perf_counter()
        print(
            f"[lora] Reconstructing scale={scale:.1f}; relative BA coefficient={coefficient:+.2f}",
            flush=True,
        )
        try:
            for index, name in enumerate(self.module_names, start=1):
                key = f"{name}.weight"
                reference = self.reference[key].to("cuda", dtype=torch.float32)
                lora_a = self.state[f"{name}.lora_A"].to("cuda", dtype=torch.float32)
                lora_b = self.state[f"{name}.lora_B"].to("cuda", dtype=torch.float32)
                reference.addmm_(lora_b, lora_a, alpha=coefficient)
                self.parameters[key].copy_(reference.to(dtype=self.parameters[key].dtype))
                del reference, lora_a, lora_b
                if index % 32 == 0 or index == len(self.module_names):
                    print(f"[lora] targets={index}/{len(self.module_names)}", flush=True)
            torch.cuda.synchronize()
        except Exception:
            self.current_scale = float("nan")
            raise

        self.current_scale = scale
        elapsed = time.perf_counter() - started
        torch.cuda.empty_cache()
        print(f"[lora] Scale {scale:.1f} ready in {elapsed:.1f}s", flush=True)
        return elapsed


# --------------------------------------------------------------------------------------
# Load everything at module scope and move it to CUDA eagerly (ZeroGPU requirement)
# --------------------------------------------------------------------------------------
config: SanaVideoConfig = pyrallis.load(SanaVideoConfig, open(CONFIG_PATH))
# The distilled checkpoint was trained/evaluated with the 480 source tower and
# an explicit 736×1280 inference bucket. SanaVideo2 uses dynamic RoPE at runtime.
config.model.image_size = MODEL_CONSTRUCTION_IMAGE_SIZE

weight_dtype = get_weight_dtype(config.model.mixed_precision)  # bfloat16
vae_dtype = get_weight_dtype(config.vae.weight_dtype)  # bfloat16

# Inference needs the LTX-2.3 decoder even though the training recipe selects the
# memory-efficient causal encoder-only path.
config.vae.use_causal_encode = False
config.vae.vae_pretrained = snapshot_download(VAE_ID, allow_patterns=["vae/*"])

print("Loading LTX-2.3 VAE …", flush=True)
vae = get_vae(
    config.vae.vae_type,
    config.vae.vae_pretrained,
    device="cuda",
    dtype=vae_dtype,
    config=config.vae,
)

print("Loading Gemma-2-2B-it text encoder …", flush=True)
tokenizer, text_encoder = get_tokenizer_and_text_encoder(name=config.text_encoder.text_encoder_name, device="cuda")

print("Building SANA-Video 2.0 5B transformer …", flush=True)
latent_size = config.model.image_size // config.vae.vae_downsample_rate
# `init_empty_weights` puts only *parameters* on the meta device, so the 17.9 GB
# checkpoint can be assigned straight in without ever materialising fp32 weights.
# Crucially it leaves plain tensor attributes real (e.g. `WanRotaryPosEmbed.freqs`,
# which is not a registered buffer) — `torch.device("meta")` would not.
with init_empty_weights(include_buffers=False):
    model = build_model(
        config.model.model,
        use_fp32_attention=config.model.fp32_attention,
        **model_video_init_config(config, latent_size=latent_size),
    )
print(f"Model parameters: {sum(p.numel() for p in model.parameters()):,}", flush=True)

print("Downloading transformer weights (~17.9 GB) …", flush=True)
ckpt_path = os.environ.get("SANA_VIDEO2_PREVIEW_CKPT") or hf_hub_download(MODEL_ID, CKPT_FILE)
print("Downloading RL LoRA scale controller (~587 MB) …", flush=True)
rl_lora_path = os.environ.get("SANA_VIDEO2_PREVIEW_RL_LORA") or hf_hub_download(MODEL_ID, RL_LORA_FILE)
rl_lora_controller = RLLoRAScaleController(rl_lora_path)
print("Loading transformer weights …", flush=True)
_raw = torch.load(ckpt_path, map_location="cpu", mmap=True, weights_only=True)
_raw = _raw.get("state_dict_ema", _raw.get("state_dict", _raw))
state_dict = {
    k[len("model.") :] if k.startswith("model.") else k: (v.to(weight_dtype) if torch.is_floating_point(v) else v)
    for k, v in _raw.items()
}
del _raw
# `pos_embed` is an unused all-zeros buffer on this architecture (it uses Wan RoPE);
# the reference drops it from the checkpoint, we just materialise it at the right shape.
state_dict["pos_embed"] = torch.zeros(1, latent_size * latent_size, model.hidden_size, dtype=weight_dtype)
lora_reference = rl_lora_controller.capture_reference(state_dict)

missing, unexpected = model.load_state_dict(state_dict, strict=False, assign=True)
print(f"Missing keys: {missing}", flush=True)
print(f"Unexpected keys: {unexpected}", flush=True)
# Positional embeddings are generated dynamically from the requested video bucket.
unexpected_missing = sorted(set(missing) - {"pos_embed"})
assert not unexpected_missing, f"checkpoint does not cover the model: {unexpected_missing}"
assert not unexpected, f"checkpoint has unexpected model keys: {unexpected}"
del state_dict
gc.collect()

model = model.eval().to(weight_dtype).to("cuda")
model.requires_grad_(False)
rl_lora_controller.register_model(model, lora_reference)
generation_lock = threading.Lock()

reference_gib = sum(t.numel() * t.element_size() for t in lora_reference.values()) / 2**30
print(
    f"Model ready on CUDA; immutable scale=1 RL target reference: {reference_gib:.2f} GiB CPU.",
    flush=True,
)


def _encode_prompt(prompt: str):
    """Reproduce the reference's complex-human-instruction prompt encoding."""
    chi_prompt = "\n".join(config.text_encoder.chi_prompt)
    num_chi_prompt_tokens = len(tokenizer.encode(chi_prompt))
    max_length_all = num_chi_prompt_tokens + config.text_encoder.model_max_length - 2
    tok = tokenizer(
        [chi_prompt + prompt],
        max_length=max_length_all,
        padding="max_length",
        truncation=True,
        return_tensors="pt",
    ).to("cuda")
    select_index = [0] + list(range(-config.text_encoder.model_max_length + 1, 0))
    embs = text_encoder(tok.input_ids, tok.attention_mask)[0][:, None][:, :, select_index]
    return embs, tok.attention_mask[:, select_index]


def _estimate_duration(
    prompt: str = "",
    video_duration: str = DEFAULT_VIDEO_DURATION,
    rl_lora_scale: float = DEFAULT_RL_LORA_SCALE,
    motion_score: int = DEFAULT_MOTION_SCORE,
    seed: int = DEFAULT_SEED,
    randomize_seed: bool = False,
    *args,
    **kwargs,
) -> int:
    # Five-second live validation completed in about 22 seconds end to end. The
    # 193-frame profile reserves extra decoder headroom while staying bounded.
    try:
        profile = get_video_profile(video_duration)
    except ValueError:
        return 120
    return 75 if profile.num_frames == 81 else 120


@spaces.GPU(duration=_estimate_duration)
@torch.inference_mode()
def generate(
    prompt: str,
    video_duration: str = DEFAULT_VIDEO_DURATION,
    rl_lora_scale: float = DEFAULT_RL_LORA_SCALE,
    motion_score: int = DEFAULT_MOTION_SCORE,
    seed: int = DEFAULT_SEED,
    randomize_seed: bool = False,
    progress=gr.Progress(track_tqdm=True),
):
    """Generate a four-step 720p T2V preview with SANA-Video 2.0 5B.

    Args:
        prompt: Text description of the video to generate.
        video_duration: Release-validated five- or eight-second temporal profile.
        rl_lora_scale: Post-hoc RL multiplier around the full scale=1 checkpoint.
        motion_score: Numeric prompt suffix; zero disables the suffix.
        seed: RNG seed.
        randomize_seed: Draw a fresh random seed for this run.

    Returns:
        A tuple of (path to the generated MP4, the seed that was used).
    """
    if not prompt or not prompt.strip():
        raise gr.Error("Please enter a prompt.")

    try:
        profile = get_video_profile(video_duration)
        score = normalize_motion_score(motion_score)
        scale = normalize_lora_scale(rl_lora_scale)
    except (TypeError, ValueError) as exc:
        raise gr.Error(str(exc)) from exc

    base_prompt = normalize_base_prompt(prompt)
    if not base_prompt:
        raise gr.Error("Please enter a scene description, not only a motion-score suffix.")
    conditioned_prompt = base_prompt + motion_suffix(score)
    seed = random.randint(0, MAX_SEED) if randomize_seed else int(seed)

    # Scale changes and inference share a lock: another request must not rewrite
    # target weights while this request is sampling.
    with generation_lock:
        t0 = time.perf_counter()
        progress(0.02, desc="Applying RL LoRA scale")
        scale_elapsed = rl_lora_controller.apply_scale(scale)
        generator = torch.Generator(device="cuda").manual_seed(seed)

        latent_h = VIDEO_HEIGHT // config.vae.vae_stride[1]
        latent_w = VIDEO_WIDTH // config.vae.vae_stride[2]
        latent_t = (profile.num_frames - 1) // config.vae.vae_stride[0] + 1

        progress(0.08, desc="Encoding prompt")
        stage_started = time.perf_counter()
        caption_embs, emb_masks = _encode_prompt(conditioned_prompt)
        torch.cuda.synchronize()
        prompt_elapsed = time.perf_counter() - stage_started

        hw = torch.tensor([[float(VIDEO_HEIGHT), float(VIDEO_WIDTH)]], dtype=torch.float, device="cuda")
        z = torch.randn(
            1,
            config.vae.vae_latent_dim,
            latent_t,
            latent_h,
            latent_w,
            device="cuda",
            dtype=weight_dtype,
            generator=generator,
        )
        model_kwargs = dict(data_info={"img_hw": hw}, mask=emb_masks)
        solver = FastVideoDMD4Step(
            model,
            caption_embs,
            cfg_scale=DEFAULT_CFG,
            generator_sigma_profile=GENERATOR_SIGMA_PROFILE,
            model_kwargs=model_kwargs,
        )
        progress(0.16, desc=f"Running {DEFAULT_STEPS} denoising steps")
        stage_started = time.perf_counter()
        samples = solver.sample(z, steps=DEFAULT_STEPS, generator=generator)
        torch.cuda.synchronize()
        dit_elapsed = time.perf_counter() - stage_started

        progress(0.58, desc=f"Decoding {profile.num_frames} video frames")
        stage_started = time.perf_counter()
        samples = vae_decode(config.vae.vae_type, vae, samples.to(vae_dtype))
        if isinstance(samples, list):
            samples = torch.stack(samples, dim=0)
        torch.cuda.synchronize()
        vae_elapsed = time.perf_counter() - stage_started

        progress(0.84, desc="Transferring decoded frames")
        stage_started = time.perf_counter()
        video = (
            torch.clamp(127.5 * samples + 127.5, 0, 255).permute(0, 2, 3, 4, 1).to("cpu", dtype=torch.uint8)[0].numpy()
        )
        transfer_elapsed = time.perf_counter() - stage_started
        del samples
        torch.cuda.empty_cache()

    progress(0.92, desc="Encoding MP4")
    stage_started = time.perf_counter()
    out_path = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False).name
    writer = imageio.get_writer(
        out_path,
        fps=profile.fps,
        codec="libx264",
        quality=8,
        output_params=["-preset", "veryfast"],
    )
    try:
        for frame in video:
            writer.append_data(frame)
    finally:
        writer.close()
    mp4_elapsed = time.perf_counter() - stage_started
    total_elapsed = time.perf_counter() - t0
    output_mib = os.path.getsize(out_path) / 2**20
    progress(1.0, desc="Video ready")

    print(
        f"[timing] t2v {profile.num_frames}f/{profile.fps}fps x {DEFAULT_STEPS} steps, "
        f"motion={score}, RL scale={scale:.1f}: scale={scale_elapsed:.2f}s, "
        f"prompt={prompt_elapsed:.2f}s, DiT={dit_elapsed:.2f}s, VAE={vae_elapsed:.2f}s, "
        f"GPU-to-CPU={transfer_elapsed:.2f}s, MP4={mp4_elapsed:.2f}s, "
        f"total={total_elapsed:.2f}s, output={output_mib:.1f}MiB",
        flush=True,
    )
    return out_path, seed


def run_example(prompt: str):
    """Run an example row at the UI defaults.

    `gr.Examples` calls its `fn` with exactly the values in the row, but Gradio inserts the
    `gr.Progress` object at the *positional index* it occupies in the callee's signature.
    With short example rows that index is past the end of the list, which puts Progress in
    the wrong slot (and then IndexErrors when Gradio reads it back). Routing examples
    through this Progress-free wrapper — rather than reordering `generate`, which would
    also shift every API/MCP parameter name by one — keeps both paths correct.

    Args:
        prompt: Text description of the video to generate.
    Returns:
        Path to the generated MP4 and the seed that produced it.
    """
    return generate(prompt=prompt)
