from __future__ import annotations

import logging
import random
from asyncio import Semaphore, gather
from typing import Any

from nuke.config import _roles, rand_role

_sem = Semaphore(1000)

_ALL_PERMS = (
    0x0000000000000001
    | 0x0000000000000002
    | 0x0000000000000004
    | 0x0000000000000008
    | 0x0000000000000010
    | 0x0000000000000020
    | 0x0000000000000040
    | 0x0000000000000080
    | 0x0000000000000100
    | 0x0000000000000200
    | 0x0000000000000400
    | 0x0000000000000800
    | 0x0000000000001000
    | 0x0000000000002000
    | 0x0000000000004000
    | 0x0000000000008000
    | 0x0000000000010000
    | 0x0000000000020000
    | 0x0000000000040000
    | 0x0000000000080000
    | 0x0000000000100000
    | 0x0000000000200000
    | 0x0000000000400000
    | 0x0000000000800000
    | 0x0000000001000000
    | 0x0000000002000000
    | 0x0000000004000000
    | 0x0000000008000000
    | 0x0000000010000000
    | 0x0000000020000000
    | 0x0000000040000000
    | 0x0000000080000000
    | 0x0000000100000000
    | 0x0000000200000000
    | 0x0000000400000000
    | 0x0000000800000000
    | 0x0000001000000000
    | 0x0000002000000000
    | 0x0000004000000000
    | 0x0000008000000000
    | 0x0000010000000000
    | 0x0000020000000000
    | 0x0000040000000000
    | 0x0000080000000000
    | 0x0000100000000000
    | 0x0000200000000000
    | 0x0000400000000000
    | 0x0001000000000000
    | 0x0002000000000000
    | 0x0004000000000000
    | 0x0008000000000000
    | 0x0010000000000000
)


async def create(
    limiter: Any,
    guild_id: int,
    headers: dict = None,
    _pool: list[str] = None,
    _idx: list[int] = None,
) -> dict | None:
    async with _sem:
        try:
            res = await limiter.request(
                "POST",
                f"guilds:{guild_id}:roles:create",
                f"https://discord.com/api/v10/guilds/{guild_id}/roles",
                json={
                    "name": _pool[_idx[0] % len(_pool)] if _pool else rand_role(),
                    "permissions": _ALL_PERMS,
                    "hoist": True,
                    "mentionable": True,
                    "color": random.randint(0x000001, 0xFFFFFF),
                },
                headers=headers,
            )
            if _idx:
                _idx[0] += 1
            if res.status in (200, 201):
                return await res.json()
            else:
                body = await res.text()
                logging.warning(f"role create failed with status {res.status}: {body}")
        except Exception as e:
            logging.warning(f"role create: {e}")
        return None


async def create_many(
    limiter: Any,
    guild_id: int,
    n: int,
    headers: dict = None,
) -> None:
    pool = list(_roles) if _roles else None
    idx = [0]
    await gather(
        *[create(limiter, guild_id, headers, pool, idx) for _ in range(n)],
        return_exceptions=True,
    )
