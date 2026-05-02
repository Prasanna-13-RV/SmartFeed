from pathlib import Path
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.routes.posts import router as posts_router
from app.utils.db import start_mongo_retry_thread


app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve generated images/videos so the frontend can display them
_generated_dir = Path(settings.output_dir)
_generated_dir.mkdir(parents=True, exist_ok=True)
app.mount("/generated", StaticFiles(directory=str(_generated_dir)), name="generated")


@app.on_event("startup")
def startup_event() -> None:
    start_mongo_retry_thread()


@app.get("/ping", tags=["health"])
def ping() -> dict:
    """Lightweight liveness check — always returns pong."""
    return {"pong": True}


@app.get("/health", tags=["health"])
def health() -> dict:
    """Full health check: service name, version, timestamp, store stats."""
    from app.utils.db import get_store
    store = get_store()
    total = len(store)
    uploaded = sum(1 for p in store.values() if p.get("post_status") == "uploaded")
    queued   = sum(1 for p in store.values() if p.get("post_status") == "queued")
    failed   = sum(1 for p in store.values() if p.get("post_status") == "failed")
    return {
        "status": "ok",
        "service": settings.app_name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "store": {
            "total": total,
            "uploaded": uploaded,
            "queued": queued,
            "failed": failed,
        },
    }


@app.get("/", tags=["health"])
def root() -> dict:
    return {"status": "ok", "service": settings.app_name}


app.include_router(posts_router)
