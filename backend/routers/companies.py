from fastapi import APIRouter, HTTPException, Query

from lib import companies as C
from lib import local_engine, webcheck
from models.companies import (
    CompanyDetail, CompanyOverview, CompanyPoint, CompanySiteRequest, GeoResult, LocalEngine, LocalEngineTest, Sector,
    WebCheckRequest, WebStatus,
)
from models.schemas import ProjectCreate, ProjectSummary
from routers.projects import start_project

router = APIRouter()


async def _safe(coro):
    try:
        return await coro
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(502, f"Service officiel des entreprises indisponible : {str(exc)[:160]}")


@router.get("/companies/sectors", response_model=list[Sector])
async def sectors():
    return [{"code": k, "label": v} for k, v in C.SECTIONS.items()]


@router.get("/companies/overview", response_model=CompanyOverview)
async def overview():
    return await C.overview()


@router.get("/companies/near", response_model=list[CompanyPoint])
async def near(
    lat: float = Query(ge=41, le=51.5), lng: float = Query(ge=-5.5, le=10), radius: float = Query(default=2, ge=0.1, le=50),
    section: str = Query(default="", pattern="^[A-U]?$"), pages: int = Query(default=4, ge=1, le=8),
):
    return await _safe(C.near(lat, lng, radius, section, pages))


@router.get("/companies/geocode", response_model=list[GeoResult])
async def geocode(q: str = Query(min_length=3, max_length=120)):
    return await _safe(C.geocode(q))


@router.post("/companies/web-status", response_model=list[WebStatus])
async def web_status(body: WebCheckRequest):
    return await webcheck.statuses([i.model_dump() for i in body.items])


@router.get("/companies/{siren}", response_model=CompanyDetail)
async def detail(siren: str):
    if not (siren.isdigit() and len(siren) == 9):
        raise HTTPException(422, "SIREN invalide (9 chiffres)")
    c = await _safe(C.detail(siren))
    if not c:
        raise HTTPException(404, "Entreprise introuvable")
    return c


@router.post("/companies/{siren}/site", response_model=ProjectSummary)
async def create_site(siren: str, body: CompanySiteRequest):
    c = await detail(siren)
    if not c["active"]:
        raise HTTPException(409, "Cette entreprise est fermée")
    return await start_project(
        ProjectCreate(prompt=C.site_prompt(c), name=c["name"], mode=body.mode, llm=body.llm),
        extra={"company": {"siren": c["siren"], "name": c["name"], "city": c["city"]}},
    )


@router.get("/settings/local-engine", response_model=LocalEngine)
async def get_local_engine():
    return await local_engine.get_settings()


@router.put("/settings/local-engine", response_model=LocalEngine)
async def put_local_engine(body: LocalEngine):
    return await local_engine.save_settings(body.model_dump())


@router.post("/settings/local-engine/test", response_model=LocalEngineTest)
async def test_local_engine(body: LocalEngine):
    return await local_engine.test({**body.model_dump(), "base_url": body.base_url.rstrip("/")})
