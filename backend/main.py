import logging
from contextlib import asynccontextmanager
from pathlib import Path

from arq import create_pool
from arq.connections import RedisSettings
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text

from backend.config import settings
from backend.admin.router import router as admin_router
from backend.auth.router import router as auth_router
from backend.database import Base, engine
from backend.limiter import limiter
from backend.profiles.router import router as profiles_router
from backend.submissions.router import UPLOAD_DIR, router as submissions_router

# Import all models so Base.metadata is fully populated before create_all
import backend.auth.models  # noqa: F401
import backend.profiles.models  # noqa: F401
import backend.submissions.models  # noqa: F401

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Path(UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    app.state.arq = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    logger.info("Application startup complete — env=%s", settings.env)

    yield

    await app.state.arq.aclose()
    logger.info("Application shutdown")


app = FastAPI(title="ResumeReviewerDV", lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next) -> Response:
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = "default-src 'none'"
    if settings.env == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Please try again later."},
    )


@app.get("/health", tags=["system"])
async def health():
    from backend.database import AsyncSessionLocal
    from sqlalchemy.exc import SQLAlchemyError
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        db_status = "connected"
    except SQLAlchemyError:
        db_status = "disconnected"
    status_str = "ok" if db_status == "connected" else "degraded"
    return {"status": status_str, "database": db_status, "env": settings.env}


app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(profiles_router)
app.include_router(submissions_router)
