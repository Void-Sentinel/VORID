from __future__ import annotations
from msgspec import Struct as struct


class raidstate(
    struct,
    kw_only=True
):
    silent: bool = False
    bypass: bool = False
    message: str | None = None
