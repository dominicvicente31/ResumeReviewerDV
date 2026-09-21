from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()  # must run before any module reads os.environ

from fastapi import FastAPI

from backend.auth.router import router as auth_router
from backend.database import Base, engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(title="ResumeReviewerDV", lifespan=lifespan)
app.include_router(auth_router)
