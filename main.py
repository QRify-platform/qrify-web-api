from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import router as api_router
from db.connection import close_db, init_db
from instrumentation.prometheus import instrument_app


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Startup: pool + CREATE TABLE IF NOT EXISTS
    init_db()
    yield
    close_db()


app = FastAPI(
    title="QRify Web API",
    description="QR codes: S3 for images, Postgres for id ↔ s3_key metadata.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

instrument_app(app)
app.include_router(api_router)
