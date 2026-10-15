"""FastAPI application.

    uvicorn app.main:app --reload
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .api.routes import router as job_router
from .api.auth_routes import router as auth_router
from .config import production_problems, settings

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
    yield


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
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/", include_in_schema=False)
def index():
    return FileResponse("app/static/index.html")
