import uuid

def rope_uuid_batch(n: int) -> list[str]:
    """
    Placeholder voor Rope-kernel.
    Vandaag: gewone UUIDs.
    Later: Rope-accelerated batch generation.
    """
    return [str(uuid.uuid4()) for _ in range(n)]
