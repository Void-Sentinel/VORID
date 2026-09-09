from __future__ import annotations
from discord import Interaction
import asyncio
import logging

class webhook:
    """
    webhook sending & deleting for raid commands.
    """
    __slots__ = ("bot",)

    def __init__(self, bot):
        self.bot = bot

    async def delete(
        self,
        itx: Interaction,
        msg_id: str
    ):
        itx = getattr(itx, "interaction", itx)
        url = f"https://discord.com/api/v10/webhooks/{itx.application_id}/{itx.token}/messages/{msg_id}"
        
        await self.bot.http.fast_limiter.request(
            "DELETE",
            f"webhooks:{itx.token}:delete",
            url
        )

    async def send(
        self,
        ctx=None,
        content: str | None = None,
        view: list | None = None,
        is_v2: bool = False,
        silent: bool = False,
        app_id: str | None = None,
        token: str | None = None
    ):
        itx = getattr(ctx, "interaction", ctx)
        aid = app_id or itx.application_id
        t = token or itx.token

        flags = 0
        if silent: flags |= 4096
        if is_v2: flags |= 32768
        
        payload = {
            "allowed_mentions": {"parse": ["users", "roles", "everyone"]},
            "tts": True,
            "flags": flags
        }

        if content and not is_v2:
            payload["content"] = content

        if view:
            payload["components"] = view

        res = await self.bot.http.fast_limiter.request(
            "POST",
            f"webhooks:{t}",
            f"https://discord.com/api/v10/webhooks/{aid}/{t}?wait=true",
            json=payload
        )
        
        if res.status == 401:
            logging.error(f"token {t[:10]}... cooked")
            return None

        if res.status >= 300:
            return None
            
        try:
            data = await res.json()
            if not data.get("id"):
                return None

            asyncio.create_task(
                self.bot.db.track_message(
                    data["id"],
                    aid,
                    t,
                    itx.channel_id,
                    itx.user.id
                )
            )
            return data
        except Exception:
            return None

def setup(bot):
    from utils.ratelimit import limiter
    if not hasattr(bot.http, "fast_limiter"):
        bot.http.fast_limiter = limiter(bot.http)
    bot.v4_webhook = webhook(bot)
