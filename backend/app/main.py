import os
import shutil

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import Base, engine
from . import models  # noqa: F401
from .routers.assistant import router as assistant_router
from .routers.meetings import router as meetings_router
from .routers.telegram import router as telegram_router

app = FastAPI(title="Helper API", version="0.1.0")

# Build the list of allowed CORS origins.
# CORS_ORIGINS env var accepts a comma-separated list of URLs.
# Always include the Railway frontend domain and localhost for development.
_default_origins = [
    "https://helper-production-f608.up.railway.app",
    "http://localhost:3000",
    "http://localhost:8080",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8080",
]
_extra = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]
_allowed_origins = list(dict.fromkeys(_default_origins + _extra))

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_origin_regex=r"https://.*\.up\.railway\.app",  # all Railway subdomains
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(meetings_router, prefix="/meetings", tags=["meetings"])
app.include_router(assistant_router, prefix="/assistant", tags=["assistant"])
app.include_router(telegram_router, prefix="/telegram", tags=["telegram"])


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/stt")
async def health_stt() -> dict:
    """Check configured STT mode and local Whisper prerequisites."""
    provider = os.getenv("STT_PROVIDER", "openai_whisper_local")
    if provider == "openai_whisper_local":
        ffmpeg_ok = shutil.which("ffmpeg") is not None
        return {
            "provider": provider,
            "model": os.getenv("WHISPER_MODEL", "small"),
            "ffmpeg_installed": ffmpeg_ok,
            "reachable": ffmpeg_ok,
            "note": "Local openai/whisper model is used in backend process.",
        }
    if provider == "openai_whisper_api":
        return {
            "provider": provider,
            "reachable": bool(os.getenv("OPENAI_API_KEY", "").strip()),
            "note": "Cloud Whisper via OpenAI API.",
        }
    return {
        "provider": provider,
        "reachable": False,
        "note": "Unknown STT provider.",
    }
