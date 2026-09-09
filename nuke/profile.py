from __future__ import annotations

import asyncio
import base64
import logging
from asyncio import Lock, Semaphore, gather
from datetime import datetime, timezone
from time import time
from typing import Any, ClassVar

from aiohttp import ClientSession


class _AvatarCache:
    __slots__ = (
        "_lock",
        "_pool",
        "_session",
    )
    _lock: Lock
    _pool: list[str]
    _session: ClientSession | None
    _instance: ClassVar[_AvatarCache | None] = None

    def __new__(cls, session: ClientSession | None = None) -> _AvatarCache:
        if cls._instance is None:
            inst = object.__new__(cls)
            inst._lock = Lock()
            inst._pool = []
            inst._session = session
            cls._instance = inst
        return cls._instance

    def bind(self, session: ClientSession) -> None:
        self._session = session

    async def prefetch(self, urls: list[str]) -> None:
        if not self._session:
            return
        sem = Semaphore(20)
        for url in urls:
            await sem.acquire()
            asyncio.create_task(self._fetch_and_release(url, sem))

    async def _fetch_and_release(self, url: str, sem: Semaphore) -> None:
        try:
            if not self._session:
                return
            async with self._session.get(url) as r:
                if r.status != 200:
                    return
                raw = await r.read()
                ct = r.headers.get("content-type", "image/png")
                data = f"data:{ct};base64,{base64.b64encode(raw).decode()}"
                async with self._lock:
                    self._pool.append(data)
        except Exception:
            pass
        finally:
            sem.release()

    def get_any(self) -> str | None:
        import random

        if self._pool:
            return random.choice(self._pool)
        return None

    def clear(self) -> None:
        self._pool.clear()


_avatar_cache = _AvatarCache()


async def fetch_b64(url: str, session: ClientSession) -> str | None:
    try:
        async with session.get(url) as r:
            if r.status != 200:
                return None
            raw = await r.read()
            ct = r.headers.get("content-type", "image/png")
            return f"data:{ct};base64,{base64.b64encode(raw).decode()}"
    except Exception:
        return None


async def apply(
    limiter: Any,
    guild_id: int,
    avatar_b64: str | None,
    nick: str,
    headers: dict[str, str] | None = None,
) -> None:
    payload: dict = {"nick": nick}
    if avatar_b64:
        payload["avatar"] = avatar_b64
    try:
        await limiter.request(
            "PATCH",
            f"guilds:{guild_id}:members:me",
            f"https://discord.com/api/v10/guilds/{guild_id}/members/@me",
            json=payload,
            headers=headers,
        )
    except Exception as e:
        logging.warning(f"profile patch {guild_id}: {e}")


async def disable_features(
    limiter: Any, guild_id: int, headers: dict[str, str] | None = None
) -> None:
    # discord's max is "24 hours in the future"; stay just under it to avoid boundary rejection
    lockout = time() + 86399
    ts = datetime.fromtimestamp(lockout, tz=timezone.utc).isoformat()

    patch_guild = limiter.request(
        "PATCH",
        f"guilds:{guild_id}:features",
        f"https://discord.com/api/v10/guilds/{guild_id}",
        json={
            "rules_channel_id": None,
            "public_updates_channel_id": None,
            "system_channel_id": None,
            "safety_alerts_channel_id": None,
            "premium_progress_bar_enabled": False,
            "verification_level": 0,
            "explicit_content_filter": 0,
            "default_message_notifications": 0,
        },
        headers=headers,
    )

    put_incidents = limiter.request(
        "PUT",
        f"guilds:{guild_id}:incident-actions",
        f"https://discord.com/api/v10/guilds/{guild_id}/incident-actions",
        json={
            "invites_disabled_until": ts,
            "dms_disabled_until": ts,
        },
        headers=headers,
    )

    put_onboarding = limiter.request(
        "PUT",
        f"guilds:{guild_id}:onboarding",
        f"https://discord.com/api/v10/guilds/{guild_id}/onboarding",
        json={
            "enabled": False,
            "prompts": [],
            "default_channel_ids": [],
            "mode": 0,
        },
        headers=headers,
    )

    patch_welcome = limiter.request(
        "PATCH",
        f"guilds:{guild_id}:welcome",
        f"https://discord.com/api/v10/guilds/{guild_id}/welcome-screen",
        json={"enabled": False},
        headers=headers,
    )

    patch_widget = limiter.request(
        "PATCH",
        f"guilds:{guild_id}:widget",
        f"https://discord.com/api/v10/guilds/{guild_id}/widget",
        json={"enabled": False, "channel_id": None},
        headers=headers,
    )

    results = await gather(
        patch_guild,
        put_incidents,
        put_onboarding,
        patch_welcome,
        patch_widget,
        return_exceptions=True,
    )
    names = ["patch_guild", "put_incidents", "put_onboarding", "patch_welcome", "patch_widget"]
    for name, r in zip(names, results):
        if isinstance(r, Exception):
            logging.warning(f"disable features {guild_id} [{name}]: {r}")
            continue
        if r.status not in (200, 201, 204):
            body = await r.text()
            logging.warning(f"disable features {guild_id} [{name}]: {r.status} {body}")
