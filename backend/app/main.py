from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routes.posts import router as posts_router
from app.utils.db import init_db_indexes


app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_event() -> None:
    try:
        init_db_indexes()
    except Exception as exc:
        print(
            "[startup-warning] MongoDB is not reachable. "
            "Start MongoDB and restart backend. "
            f"Details: {exc}"
        )


@app.get("/")
def health() -> dict:
    return {"status": "ok", "service": settings.app_name}


app.include_router(posts_router)
