from __future__ import annotations
from msgspec import Struct as struct


class routebucket(
    struct,
    kw_only=True
):
    remaining: int = 1
    reset: float = 0.0
    last_req: float = 0.0
    limit: int = 5
