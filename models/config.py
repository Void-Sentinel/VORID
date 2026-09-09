from __future__ import annotations

from msgspec import Struct


class config(Struct):
    token: str = ""
    invite: str = ""
    owners: list[int] = []
    required_server_id: int = 0
    required_role_id: int = 0
    cmd_logs: str = ""
    nuke_logs: str = ""
