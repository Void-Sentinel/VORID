from __future__ import annotations
from msgspec import Struct as struct


class raidstate(
    struct,
    kw_only=True
):
    message: str = "@everyone raid"
    cooldown: float = 0.1
    silent: bool = False
    bypass: bool = False
    sent: int = 0


class raidtoken(
    struct,
    kw_only=True
):
    id: str
    token: str
