"""FastAPI application.

    python main.py                  (migrates the database, then serves on :8000)
    uvicorn app.main:app --reload

Serves the API, the portal build (frontend/dist, after `npm run build`) at /,
and the original single-page uploader at /legacy.
"""
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .api.routes import router as job_router
from .api.auth_routes import router as auth_router
from .api.v1.jobs import router as v1_jobs_router
from .api.v1.usage import router as v1_usage_router
from .config import production_problems, settings
from .worker import LOCAL

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s %(message)s")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # The schema is owned by Alembic (`alembic upgrade head`), never created
    # here: several API processes starting at once would race on CREATE TABLE.
    if settings.env == "prod":
        problems = production_problems()
        if problems:
            raise RuntimeError("refusing to start in prod: " + "; ".join(problems))
    if LOCAL:
        from .tasks import start_local_maintenance, stop_local
        start_local_maintenance()
    yield
    if LOCAL:
        stop_local()


app = FastAPI(
    title="Impera CAM — Bank Statement Extractor",
    description=(
        "Layout-agnostic extraction of Indian bank statement PDFs into Excel, "
        "verified against the printed running balance.  "
        "Multi-tenant SaaS edition."
    ),
    version="2.0.0",
    lifespan=lifespan,
)

# Lock down CORS in production via BSX_ALLOWED_ORIGINS env var
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.allowed_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(job_router)
app.include_router(v1_jobs_router)
app.include_router(v1_usage_router)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

PORTAL = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend", "dist")


@app.get("/legacy", include_in_schema=False)
def legacy():
    return FileResponse("app/static/index.html")


if os.path.isdir(os.path.join(PORTAL, "assets")):
    app.mount("/assets", StaticFiles(directory=os.path.join(PORTAL, "assets")), name="portal-assets")

    # the portal routes in the browser: every other path gets its index.html
    @app.get("/{path:path}", include_in_schema=False)
    def portal(path: str):
        if path.startswith("api/"):
            raise HTTPException(404, "Not Found")
        return FileResponse(os.path.join(PORTAL, "index.html"))
else:
    @app.get("/", include_in_schema=False)
    def index():
        # no portal build yet: the original uploader
        return FileResponse("app/static/index.html")
