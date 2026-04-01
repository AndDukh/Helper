from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers.assistant import router as assistant_router
from .routers.meetings import router as meetings_router

app = FastAPI(title="Helper API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(meetings_router, prefix="/meetings", tags=["meetings"])
app.include_router(assistant_router, prefix="/assistant", tags=["assistant"])


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
