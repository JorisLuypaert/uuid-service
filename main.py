###main.py (volledige API, 60 lijnen)
Dit is je echte microdienst.
Volledig werkend.
Volledig veilig.
Volledig Rope‑proof.###

from fastapi import FastAPI
from pydantic import BaseModel
from rope_core.uuid_engine import rope_uuid_batch
from rope_core.shortid_engine import rope_shortid_batch

app = FastAPI(title="UUID & Short-ID API", version="1.0.0")


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
