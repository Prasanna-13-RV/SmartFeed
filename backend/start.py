from __future__ import annotations

import os
import sys

import uvicorn

from app.config import settings
from app.utils.db import is_mongo_reachable


def main() -> None:
    if not is_mongo_reachable():
        print(
            "[notice] MongoDB is not reachable at "
            f"{settings.mongo_uri}. Backend can start, but DB endpoints will fail until MongoDB is up."
        )
        print("[notice] Quick start Mongo with Docker: docker compose up -d mongo")

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    reload_enabled = os.getenv("RELOAD", "1") == "1"

    uvicorn.run("app.main:app", host=host, port=port, reload=reload_enabled)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
