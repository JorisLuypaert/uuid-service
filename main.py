from fastapi import FastAPI
from pydantic import BaseModel
from rope_core.uuid_engine import rope_uuid_batch
from rope_core.shortid_engine import rope_shortid_batch
from datetime import datetime, timezone
import time

app = FastAPI(title="UUID & Short-ID API", version="1.1.0")

start_time = time.time()


# -----------------------------
# Root Endpoint
# -----------------------------

@app.get("/")
def root():
    return {
        "service": "uuid-service",
        "status": "ok",
        "docs": "/docs",
        "uuid_endpoint": "/v1/uuid",
        "shortid_endpoint": "/v1/short-id",
        "health": "/health",
        "status_endpoint": "/status"
    }


# -----------------------------
# System Endpoints
# -----------------------------

@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/status")
def status():
    uptime_seconds = int(time.time() - start_time)
    return {
        "service": "uuid-service",
        "version": "1.1.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime_seconds": uptime_seconds
    }


# -----------------------------
# Request Models
# -----------------------------

class UUIDRequest(BaseModel):
    count: int = 1


class ShortIDRequest(BaseModel):
    count: int = 1
    length: int = 10
    alphabet: str | None = None


# -----------------------------
# Endpoints
# -----------------------------

@app.post("/v1/uuid")
def generate_uuid(req: UUIDRequest):
    count = max(1, min(req.count, 10_000))
    ids = rope_uuid_batch(count)
    return {
        "type": "uuid_v4",
        "count": len(ids),
        "ids": ids
    }


@app.post("/v1/short-id")
def generate_short_id(req: ShortIDRequest):
    count = max(1, min(req.count, 10_000))
    length = max(4, min(req.length, 64))

    ids = rope_shortid_batch(count, length, req.alphabet)

    return {
        "type": "short_id",
        "count": len(ids),
        "length": length,
        "ids": ids
    }


