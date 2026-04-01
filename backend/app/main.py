from fastapi import FastAPI

from .routers.meetings import router as meetings_router

app = FastAPI(title="Helper API", version="0.1.0")
app.include_router(meetings_router, prefix="/meetings", tags=["meetings"])


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
