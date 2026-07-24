from contextlib import asynccontextmanager
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import router as api_router
from db.connection import close_db, init_db
from instrumentation.prometheus import instrument_app

# Browser origins that may call this API (credentials not used; CORS is still scoped).
_DEFAULT_ORIGINS = [
    "http://localhost:3000",
    "https://dev.qrify-web.com",
    "https://qrify-web.com",
]


def _cors_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS", "").strip()
    if raw:
        return [o.strip() for o in raw.split(",") if o.strip()]
    return _DEFAULT_ORIGINS


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield
    close_db()


app = FastAPI(
    title="QRify Web API",
    description=(
        "QR codes: preview as data-URL, optional save to S3 + Postgres, "
        "Cognito JWT for owned codes."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

instrument_app(app)
app.include_router(api_router)
