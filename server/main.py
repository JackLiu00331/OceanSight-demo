import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import config
from errors import register_handlers
from routers import buoys, sensor_data

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("oceansight_server")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if not config.DB_PATH.exists():
        raise RuntimeError(f"database not found: {config.DB_PATH} (create it with: python database/init_db.py)")
    logger.info("using database %s", config.DB_PATH)
    yield


app = FastAPI(title="OceanSight Server", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)
register_handlers(app)
app.include_router(sensor_data.router)
app.include_router(buoys.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
