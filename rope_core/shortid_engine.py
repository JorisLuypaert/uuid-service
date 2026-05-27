import secrets
import string

def rope_shortid_batch(count: int, length: int, alphabet: str | None = None) -> list[str]:
    """
    Placeholder voor Rope-kernel.
    Vandaag: base62 short IDs.
    Later: Rope-accelerated bitword mapping.
    """

    if alphabet is None or alphabet == "base62":
        alphabet = string.ascii_letters + string.digits

    return [
        "".join(secrets.choice(alphabet) for _ in range(length))
        for _ in range(count)
    ]
