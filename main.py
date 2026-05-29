from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from rope_core.uuid_engine import rope_uuid_batch
from rope_core.shortid_engine import rope_shortid_batch
from datetime import datetime, timezone
import time

app = FastAPI(title="UUID & Short-ID API", version="1.2.0")

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
        "version": "1.2.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime_seconds": uptime_seconds
    }


# -----------------------------
# Request Models (with validation)
# -----------------------------

class UUIDRequest(BaseModel):
    count: int = Field(
        default=1,
        ge=1,
        le=10_000,
        description="Number of UUIDs to generate (1–10,000)"
    )


class ShortIDRequest(BaseModel):
    count: int = Field(
        default=1,
        ge=1,
        le=10_000,
        description="Number of short IDs to generate (1–10,000)"
    )
    length: int = Field(
        default=10,
        ge=4,
        le=64,
        description="Length of each short ID (4–64)"
    )
    alphabet: str | None = Field(
        default=None,
        description="Optional custom alphabet"
    )


# -----------------------------
# Endpoints
# -----------------------------

@app.post("/v1/uuid")
def generate_uuid(req: UUIDRequest):
    # Validatie gebeurt nu volledig in Pydantic
    ids = rope_uuid_batch(req.count)

    return {
        "type": "uuid_v4",
        "count": len(ids),
        "ids": ids
    }


@app.post("/v1/short-id")
def generate_short_id(req: ShortIDRequest):
    # Validatie gebeurt nu volledig in Pydantic
    ids = rope_shortid_batch(req.count, req.length, req.alphabet)

    return {
        "type": "short_id",
        "count": len(ids),
        "length": req.length,
        "ids": ids
    }


