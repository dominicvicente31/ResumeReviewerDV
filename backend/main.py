from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()  # must run before any module reads os.environ

from fastapi import FastAPI

from backend.auth.router import router as auth_router
from backend.database import Base, engine
from backend.profiles.router import router as profiles_router
from backend.submissions.router import router as submissions_router

# Import all models so Base.metadata is fully populated before create_all
import backend.auth.models  # noqa: F401
import backend.profiles.models  # noqa: F401
import backend.submissions.models  # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(title="ResumeReviewerDV", lifespan=lifespan)
app.include_router(auth_router)
app.include_router(profiles_router)
app.include_router(submissions_router)
