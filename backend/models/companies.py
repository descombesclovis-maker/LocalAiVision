from typing import Literal, Optional

from pydantic import BaseModel, Field


class CompanyPoint(BaseModel):
    siren: str
    siret: str
    name: str
    lat: float
    lng: float
    naf: str
    section: str
    address: str
    city: str
    effectif: str
    is_siege: bool


class CompanyOverview(BaseModel):
    points: list[CompanyPoint]
    departments_ready: int
    departments_total: int


class Sector(BaseModel):
    code: str
    label: str


class GeoResult(BaseModel):
    label: str
    lat: float
    lng: float
    type: str


class CompanyDetail(BaseModel):
    siren: str
    siret: str
    name: str
    legal_name: str
    naf: str
    section: str
    section_label: str
    address: str
    city: str
    postal_code: str
    lat: Optional[float] = None
    lng: Optional[float] = None
    created: str
    legal_form: str
    category: str
    effectif: str
    establishments: int
    directors: list[str]
    revenue: Optional[int] = None
    net_result: Optional[int] = None
    finance_year: Optional[str] = None
    strengths: list[str]
    site_type: str
    active: bool


class CompanySiteRequest(BaseModel):
    llm: Literal["local", "claude", "gpt", "gemini"] = "local"
    mode: Literal["libre", "pro"] = "pro"


class LocalEngine(BaseModel):
    kind: Literal["ollama", "openai"] = "ollama"
    base_url: str = Field(min_length=8, max_length=300)
    model: str = Field(min_length=1, max_length=200)
    num_ctx: int = Field(default=16384, ge=2048, le=131072)


class LocalEngineTest(BaseModel):
    ok: bool
    models: list[str]
    message: str


class WebCheckItem(BaseModel):
    siret: str = Field(min_length=14, max_length=14)
    name: str = Field(max_length=200)
    city: str = Field(default="", max_length=120)
    lat: float
    lng: float


class WebCheckRequest(BaseModel):
    items: list[WebCheckItem] = Field(max_length=150)


class WebStatus(BaseModel):
    siret: str
    status: Literal["pending", "found", "none"]
    url: Optional[str] = None
    source: str
