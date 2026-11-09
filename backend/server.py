import asyncio
from contextlib import asynccontextmanager, suppress
from fastapi import FastAPI, APIRouter
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
import os
import logging
from pathlib import Path


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
from lib.db import client, db, ensure_indexes
from routers import companies, engines, media, projects


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


api_router.include_router(projects.router)
api_router.include_router(media.router)
api_router.include_router(companies.router)
api_router.include_router(engines.router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Include the router in the main app (keep last)
app.include_router(api_router)
