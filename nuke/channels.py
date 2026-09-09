from __future__ import annotations

import logging
from asyncio import Semaphore, gather
from typing import Any

from nuke.config import rand_category, rand_channel

sem = Semaphore(1000)


async def delete(
    limiter: Any, guild_id: int, channel_id: int, headers: dict[str, str] | None = None
) -> None:
    async with sem:
        try:
            await limiter.request(
                "DELETE",
                f"guilds:{guild_id}:ch:del",
                f"https://discord.com/api/v10/channels/{channel_id}",
                headers=headers,
            )
        except Exception as e:
            logging.warning(f"ch del {channel_id}: {e}")


async def create(
    limiter: Any,
    guild_id: int,
    headers: dict[str, str] | None = None,
    channel_type: int = 0,
    parent_id: str | None = None,
) -> str | None:
    async with sem:
        try:
            payload: dict = {"name": rand_channel(), "type": channel_type}
            if parent_id:
                payload["parent_id"] = parent_id
            res = await limiter.request(
                "POST",
                f"guilds:{guild_id}:ch:create",
                f"https://discord.com/api/v10/guilds/{guild_id}/channels",
                json=payload,
                headers=headers,
            )
            if res.status in (200, 201):
                data = await res.json()
                return str(data.get("id"))
            else:
                body = await res.text()
                logging.warning(f"ch create failed {res.status}: {body[:200]}")
        except Exception as e:
            logging.warning(f"ch create exception: {e}")
        return None


async def create_category(
    limiter: Any,
    guild_id: int,
    headers: dict[str, str] | None = None,
) -> str | None:
    async with sem:
        try:
            res = await limiter.request(
                "POST",
                f"guilds:{guild_id}:ch:category:create",
                f"https://discord.com/api/v10/guilds/{guild_id}/channels",
                json={"name": rand_category(), "type": 4},
                headers=headers,
            )
            if res.status in (200, 201):
                data = await res.json()
                return str(data.get("id"))
            else:
                body = await res.text()
                logging.warning(f"category create failed {res.status}: {body[:200]}")
        except Exception as e:
            logging.warning(f"category create exception: {e}")
        return None


async def create_categories(
    limiter: Any,
    guild_id: int,
    n: int,
    headers: dict[str, str] | None = None,
) -> list[str]:
    results = await gather(
        *[create_category(limiter, guild_id, headers) for _ in range(n)],
        return_exceptions=True,
    )
    return [r for r in results if isinstance(r, str)]


async def delete_all(
    limiter: Any,
    guild_id: int,
    existing: list,
    headers: dict[str, str] | None = None,
) -> None:
    channel_ids = [int(c["id"]) if isinstance(c, dict) else int(c) for c in existing]
    await gather(
        *[delete(limiter, guild_id, ch_id, headers) for ch_id in channel_ids],
        return_exceptions=True,
    )


async def create_many(
    limiter: Any,
    guild_id: int,
    n: int,
    headers: dict[str, str] | None = None,
    ready=None,
    on_create=None,
    on_threshold=None,
    category_ids: list[str] | None = None,
) -> list[str]:
    if ready is None:
        from asyncio import Event

        ready = Event()
    done = 0
    results: list[str] = []
    cat_count = len(category_ids) if category_ids else 0
    for i in range(0, n, 100):
        batch_size = min(100, n - i)
        batch = await gather(
            *[
                create(
                    limiter,
                    guild_id,
                    headers,
                    channel_type=0 if (i + j) % 2 == 0 else 2,
                    parent_id=category_ids[(i + j) % cat_count] if category_ids else None,
                )
                for j in range(batch_size)
            ],
            return_exceptions=True,
        )
        for ch_id in batch:
            if isinstance(ch_id, str):
                results.append(ch_id)
                done += 1
                if on_create:
                    on_create(ch_id)
                if on_threshold and done >= 50 and not ready.is_set():
                    on_threshold()
        if done >= n and not ready.is_set():
            ready.set()

    if not ready.is_set():
        ready.set()

    return results
