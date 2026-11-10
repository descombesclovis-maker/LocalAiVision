import asyncio
from contextlib import asynccontextmanager, suppress
from fastapi import FastAPI, APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
import os
import logging
from pathlib import Path


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
from lib.db import client, db, ensure_indexes
from lib.auth import AuthMiddleware, boot, API_KEY, COOKIE_NAME, tokens_equal
from routers import companies, engines, media, projects

# Restrictive CORS: only loopback origins by default.  The frontend (Vite dev server on
# :3000 or :5173) and the backend itself (:8001) are the only legitimate callers.  If the
# operator sets CORS_ORIGINS in .env we honour it, but never fall back to '*' — a wildcard
# with allow_credentials=True is a security misconfiguration rejected by browsers anyway.
_LOOPBACK_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:8001",
    "http://127.0.0.1:8001",
]


def _cors_origins() -> list[str]:
    raw = os.environ.get("CORS_ORIGINS", "")
    if raw:
        origins = [o.strip() for o in raw.split(",") if o.strip()]
        # Filter out '*' — never serve credentials to every origin.
        origins = [o for o in origins if o != "*"]
        return origins or _LOOPBACK_ORIGINS
    return _LOOPBACK_ORIGINS


async def _recover_interrupted() -> None:
    """Tasks die with the process: flag in-flight jobs so the user can resume them."""
    await db.projects.update_many(
        {"status": {"$in": ["queued", "generating"]}},
        {"$set": {"status": "error", "error": "Génération interrompue par un redémarrage du serveur. Cliquez sur « Reprendre »."}},
    )
    await db.projects.update_many({"status": "editing"}, {"$set": {"status": "ready"}})
    await db.media.update_many(
        {"status": {"$in": ["pending", "running"]}},
        {"$set": {"status": "error", "error": "Interrompue par un redémarrage du serveur", "progress_label": "Échec"}},
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.index_task = asyncio.create_task(ensure_indexes())
    with suppress(Exception):
        await _recover_interrupted()
    yield
    app.state.index_task.cancel()
    with suppress(asyncio.CancelledError):
        await app.state.index_task
    client.close()


app = FastAPI(lifespan=lifespan)
api_router = APIRouter(prefix="/api")


@api_router.get("/")
async def root():
    return {"message": "LocalAiStudio API"}


@api_router.post("/auth/init")
async def init_session(request: Request):
    """One-time session initialisation.

    The Windows launcher generates a random bootstrap token (``LAS_BOOT_TOKEN``) and passes
    it to both the backend and the Vite proxy.  The frontend calls this endpoint; the Vite
    proxy injects the token as ``X-Boot-Token``.  The backend validates it, issues an httpOnly
    ``SameSite=Strict`` session cookie, and invalidates the token (one-time use).

    CSRF protection: ``SameSite=Strict`` prevents the cookie from being sent on cross-site
    requests.  No double-submit token is needed for a local app with ``SameSite=Strict``.
    """
    # CORS alone does not stop a cross-site form POST: reject it before consuming the
    # one-time boot token, even when the proxy has injected a valid token.
    origin = request.headers.get("origin")
    if (origin and origin not in _cors_origins()) or request.headers.get("sec-fetch-site") == "cross-site":
        raise HTTPException(403, "Origine non autorisée pour l'ouverture de session")
    existing = request.cookies.get(COOKIE_NAME, "")
    if existing and tokens_equal(existing, API_KEY):
        # Page refresh or new tab with a valid session: idempotent, the consumed boot token is not needed.
        response = JSONResponse({"ok": True, "session": "existing"})
        response.set_cookie(COOKIE_NAME, API_KEY, httponly=True, samesite="strict", path="/api")
        return response
    token = request.headers.get("x-boot-token", "")
    if not boot.consume(token):
        raise HTTPException(401, "Jeton d'initialisation invalide ou déjà utilisé")
    response = JSONResponse({"ok": True})
    response.set_cookie(
        COOKIE_NAME,
        API_KEY,
        httponly=True,
        samesite="strict",
        path="/api",
    )
    return response


api_router.include_router(projects.router)
api_router.include_router(media.router)
api_router.include_router(companies.router)
api_router.include_router(engines.router)

app.add_middleware(AuthMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=_cors_origins(),
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-API-Key"],
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Include the router in the main app (keep last)
app.include_router(api_router)
