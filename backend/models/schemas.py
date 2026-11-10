from typing import Literal, Optional

from pydantic import BaseModel, Field


class Step(BaseModel):
    key: str
    label: str
    status: Literal["pending", "running", "done", "error", "waiting"] = "pending"
    detail: str = ""


class PageInfo(BaseModel):
    file: str
    title: str


class FileItem(BaseModel):
    path: str
    content: str


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str
    created_at: str


class StyleOptions(BaseModel):
    mood: str = ""
    colors: str = ""
    fonts: str = ""
    references: str = ""


class ProjectCreate(BaseModel):
    prompt: str = Field(min_length=8, max_length=4000)
    name: str = ""
    mode: Literal["libre", "pro"] = "libre"
    llm: Literal["local", "claude", "gpt", "gemini"] = "local"
    engine: Literal["premium", "code"] = "premium"
    hero_video: bool = False
    brand_id: Optional[str] = None
    style: Optional[StyleOptions] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    brand_id: Optional[str] = None


class ProjectSummary(BaseModel):
    id: str
    name: str
    prompt: str
    mode: str
    llm: str
    engine: str = "code"
    hero_video: bool = False
    brand_id: Optional[str] = None
    status: str
    site_type: str = ""
    thumbnail_url: Optional[str] = None
    version: int = 0
    created_at: str
    updated_at: str


class Project(ProjectSummary):
    style: Optional[StyleOptions] = None
    steps: list[Step] = []
    question: Optional[str] = None
    pages: list[PageInfo] = []
    files: list[FileItem] = []
    messages: list[ChatMessage] = []
    asset_ids: list[str] = []
    error: Optional[str] = None
    qa_report: list[str] = []


class Selection(BaseModel):
    page: str = ""
    selector: str = ""
    html: str = Field(default="", max_length=4000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    page: str = ""
    selection: Optional[Selection] = None
    media_ids: list[str] = []


class FileUpdate(BaseModel):
    path: str
    content: str


class Version(BaseModel):
    id: str
    project_id: str
    number: int
    label: str
    created_at: str


class Brand(BaseModel):
    id: str
    name: str
    slogan: str = ""
    colors: list[str] = []
    logo_media_id: Optional[str] = None
    created_at: str


class BrandCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    slogan: str = ""
    colors: list[str] = []
    logo_media_id: Optional[str] = None


class Media(BaseModel):
    id: str
    kind: Literal["image", "video"]
    source: str
    prompt: str
    model: str
    status: Literal["pending", "running", "done", "error", "cancelled"]
    progress_label: str = ""
    url: Optional[str] = None
    mime: Optional[str] = None
    aspect_ratio: Optional[str] = None
    duration: Optional[str] = None
    project_id: Optional[str] = None
    error: Optional[str] = None
    created_at: str
    updated_at: str
    generation_metrics: Optional[dict] = None


class ImageRequest(BaseModel):
    prompt: str = Field(min_length=3, max_length=3000)
    model: Literal["comfy", "nano-banana", "nano-banana-pro"] = "comfy"
    aspect_ratio: Literal["1:1", "16:9", "9:16", "4:5"] = "1:1"
    ref_media_id: Optional[str] = None
    comfy_preset: Optional[Literal["flux-dev", "flux-schnell", "sdxl"]] = None


class VideoRequest(BaseModel):
    prompt: str = Field(min_length=3, max_length=2500)
    model: Literal["comfy", "veo", "kling", "minimax"] = "comfy"
    mode: Literal["text", "image"] = "text"
    duration: str = ""
    aspect_ratio: str = "16:9"
    ref_media_id: Optional[str] = None
    camera_pose: Literal["Static", "Pan Up", "Pan Down", "Pan Left", "Pan Right", "Zoom In", "Zoom Out", "Anti Clockwise (ACW)", "ClockWise (CW)"] = "Static"
    comfy_preset: Optional[Literal["wan22", "wan21_fun_camera", "ltxv"]] = None


class SmartMotionRequest(BaseModel):
    prompt: str = Field(min_length=3, max_length=2000)
    ref_media_id: str = Field(min_length=1, max_length=80)
    seconds: int = Field(default=5, ge=5, le=30)
    fps: Literal[24] = 24
    output_size: Literal["source", "1280x720", "1920x1080"] = "source"
    motion: Literal["push_in", "pan_left", "pan_right", "tilt_up", "tilt_down", "orbit_subtle", "static"] = "push_in"


class UploadRequest(BaseModel):
    data_url: str
    source: Literal["upload", "ad", "logo"] = "upload"
    prompt: str = ""


class VideoModel(BaseModel):
    key: str
    label: str
    tagline: str
    durations: list[str]
    aspects: list[str]
    audio: bool


class ActivityItem(BaseModel):
    id: str
    kind: Literal["site", "image", "video"]
    name: str
    status: str
    label: str


class Activity(BaseModel):
    count: int
    items: list[ActivityItem]
