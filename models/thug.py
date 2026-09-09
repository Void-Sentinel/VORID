from __future__ import annotations
from msgspec import Struct as struct


class thugstate(
    struct,
    kw_only=True
):
    silent: bool = False
    bypass: bool = False
