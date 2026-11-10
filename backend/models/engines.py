from typing import Literal

from pydantic import BaseModel, Field


class ComfySettings(BaseModel):
    base_url: str = Field(min_length=8, max_length=300)
    image_preset: Literal["flux-dev", "flux-schnell", "sdxl"] = "flux-dev"
    image_checkpoint: str = Field(min_length=1, max_length=300)
    video_preset: Literal["wan22", "wan21_t2v", "wan21_fun_camera", "ltxv"] = "wan21_t2v"
    video_model: str = Field(min_length=1, max_length=300)
    video_text_encoder: str = Field(min_length=1, max_length=300)
    video_vae: str = ""
    custom_image_workflow: str = Field(default="", max_length=200_000)
    custom_video_workflow: str = Field(default="", max_length=200_000)


class ComfyTest(BaseModel):
    ok: bool
    message: str
    gpu: str
    checkpoints: list[str]
    diffusion_models: list[str]
    text_encoders: list[str]


class EnginePreset(BaseModel):
    key: str
    label: str
    files: dict[str, str]


class EnginePresets(BaseModel):
    image: list[EnginePreset]
    video: list[EnginePreset]


class QueueItem(BaseModel):
    id: str
    kind: Literal["photo", "video", "site", "edit"]
    engine: str
    label: str
    ref: Literal["media", "project"]
    status: Literal["running", "waiting"]
    position: int
    elapsed_s: int
    eta_s: int
    start_in_s: int
    typical_s: int
    samples: int


class QueueState(BaseModel):
    items: list[QueueItem]
    total_eta_s: int


class DiagCheck(BaseModel):
    key: str
    label: str
    status: Literal["ok", "warn", "error", "info"]
    detail: str
    fix: str = ""
    cmd: str = ""


class Diagnostic(BaseModel):
    checks: list[DiagCheck]
    ok: int
    warn: int
    error: int
    online: bool
    checked_at: str


class KitInfo(BaseModel):
    installer_available: bool
    installer_size_mb: float
