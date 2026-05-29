import os
import json
import time
import uuid
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime, timezone
from typing import Dict, Tuple

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field

from rope_core.uuid_engine import rope_uuid_batch
from rope_core.shortid_engine import rope_shortid_batch


# -----------------------------
# Config via environment
# -----------------------------

SERVICE_NAME = os.getenv("SERVICE_NAME", "uuid-service")
SERVICE_VERSION = os.getenv("SERVICE_VERSION", "1.7.0")

LOG_FILE = os.getenv("LOG_FILE", "service.log")
LOG_MAX_BYTES = int(os.getenv("LOG_MAX_BYTES", "5000000"))
LOG_BACKUPS = int(os.getenv("LOG_BACKUPS", "5"))

RATE_WINDOW_SECONDS = int(os.getenv("RATE_WINDOW_SECONDS", "60"))
RATE_MAX_REQUESTS = int(os.getenv("RATE_MAX_REQUESTS", "100"))

METRICS_ENABLED = os.getenv("METRICS_ENABLED", "true").lower() == "true"


# -----------------------------
# Logging setup (JSON + rotating)
# -----------------------------

class JsonFormatter(logging.Formatter):
    def format(self, record):
        base = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
        }
        msg = record.getMessage()
        try:
            # als message al JSON is
            parsed = json.loads(msg)
            base.update(parsed)
        except Exception:
            base["message"] = msg
        return json.dumps(base)


file_handler = RotatingFileHandler(
    LOG_FILE,
    maxBytes=LOG_MAX_BYTES,
    backupCount=LOG_BACKUPS
)
file_handler.setFormatter(JsonFormatter())
file_handler.setLevel(logging.INFO)

console_handler = logging.StreamHandler()
console_handler.setFormatter(JsonFormatter())
console_handler.setLevel(logging.INFO)

logger = logging.getLogger(SERVICE_NAME)
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)
logger.addHandler(console_handler)


# -----------------------------
# Metrics (simpel in-memory)
# -----------------------------

start_time = time.time()

metrics_counters = {
    "uuid_requests_total": 0,
    "shortid_requests_total": 0,
    "errors_total": 0,
}

metrics_durations_ms = {
    "uuid_requests_duration_ms_total": 0,
    "shortid_requests_duration_ms_total": 0,
}


def record_metric(endpoint: str, duration_ms: int):
    if endpoint == "/v1/uuid":
        metrics_counters["uuid_requests_total"] += 1
        metrics_durations_ms["uuid_requests_duration_ms_total"] += duration_ms
    elif endpoint == "/v1/short-id":
        metrics_counters["shortid_requests_total"] += 1
        metrics_durations_ms["shortid_requests_duration_ms_total"] += duration_ms


# -----------------------------
# Rate limiting (simpel per IP)
# -----------------------------

rate_state: Dict[str, Tuple[float, int]] = {}  # ip -> (window_start, count)


def check_rate_limit(request: Request):
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()

    window_start, count = rate_state.get(client_ip, (now, 0))

    if now - window_start > RATE_WINDOW_SECONDS:
        # nieuw venster
        window_start = now
        count = 0

    count += 1
    rate_state[client_ip] = (window_start, count)

    if count > RATE_MAX_REQUESTS:
        logger.warning(json.dumps({
            "event": "rate_limit_exceeded",
            "ip": client_ip,
            "count": count,
            "window_seconds": RATE_WINDOW_SECONDS
        }))
        raise HTTPException(
            status_code=429,
            detail="ROPE-429: Rate limit exceeded"
        )


# -----------------------------
# FastAPI app
# -----------------------------

app = FastAPI(title="UUID & Short-ID API", version=SERVICE_VERSION)


# -----------------------------
# Helper: uniforme response
# -----------------------------

def make_response(data: dict, endpoint: str | None = None):
    start = time.time()

    request_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()

    response = {
        "request_id": request_id,
        "timestamp": timestamp,
        "service_version": SERVICE_VERSION,
        "data": data
    }

    duration_ms = int((time.time() - start) * 1000)
    response["duration_ms"] = duration_ms

    record_metric(endpoint or "unknown", duration_ms)

    logger.info(json.dumps({
        "event": "api_response",
        "endpoint": endpoint,
        "request_id": request_id,
        "duration_ms": duration_ms,
        "data_keys": list(data.keys())
    }))

    return response


# -----------------------------
# Models
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
# Exception handlers
# -----------------------------

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    metrics_counters["errors_total"] += 1

    logger.error(json.dumps({
        "event": "http_error",
        "status_code": exc.status_code,
        "detail": exc.detail,
        "path": request.url.path
    }))

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.status_code,
                "message": exc.detail,
                "path": request.url.path
            }
        }
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    metrics_counters["errors_total"] += 1

    logger.exception(json.dumps({
        "event": "unhandled_error",
        "path": request.url.path,
        "error": str(exc)
    }))

    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": 500,
                "message": "ROPE-500: Internal server error",
                "path": request.url.path
            }
        }
    )


# -----------------------------
# System endpoints
# -----------------------------

@app.get("/")
def root():
    return {
        "service": SERVICE_NAME,
        "status": "ok",
        "docs": "/docs",
        "uuid_endpoint": "/v1/uuid",
        "shortid_endpoint": "/v1/short-id",
        "health": "/health",
        "status_endpoint": "/status",
        "metrics": "/metrics",
        "logs": "/logs"
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/status")
def status():
    uptime_seconds = int(time.time() - start_time)
    return {
        "service": SERVICE_NAME,
        "version": SERVICE_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime_seconds": uptime_seconds
    }


@app.get("/metrics")
def metrics():
    if not METRICS_ENABLED:
        raise HTTPException(status_code=404, detail="ROPE-404: Metrics disabled")

    lines = []
    lines.append(f'uuid_requests_total {metrics_counters["uuid_requests_total"]}')
    lines.append(f'shortid_requests_total {metrics_counters["shortid_requests_total"]}')
    lines.append(f'errors_total {metrics_counters["errors_total"]}')
    lines.append(
        f'uuid_requests_duration_ms_total {metrics_durations_ms["uuid_requests_duration_ms_total"]}'
    )
    lines.append(
        f'shortid_requests_duration_ms_total {metrics_durations_ms["shortid_requests_duration_ms_total"]}'
    )

    return PlainTextResponse("\n".join(lines))


@app.get("/logs")
def get_logs(lines: int = 200):
    try:
        with open(LOG_FILE, "r") as f:
            content = f.readlines()
        return {"lines": content[-lines:]}
    except FileNotFoundError:
        return {"error": "Log file not found"}


# -----------------------------
# Business endpoints
# -----------------------------

@app.post("/v1/uuid")
def generate_uuid(req: UUIDRequest, _: None = Depends(check_rate_limit)):
    ids = rope_uuid_batch(req.count)

    return make_response({
        "type": "uuid_v4",
        "count": len(ids),
        "ids": ids
    }, endpoint="/v1/uuid")


@app.post("/v1/short-id")
def generate_short_id(req: ShortIDRequest, _: None = Depends(check_rate_limit)):
    ids = rope_shortid_batch(req.count, req.length, req.alphabet)

    return make_response({
        "type": "short_id",
        "count": len(ids),
        "length": req.length,
        "alphabet_provided": req.alphabet is not None,
        "ids": ids
    }, endpoint="/v1/short-id")
