from __future__ import annotations

import logging

from discord import Interaction

from models.config import config as cfg_type
from utils.cache import diskstore
from utils.member_cache import get as get_member_cache
from utils.perm import check as core_check

_temp_bl = diskstore(filepath="temp_blacklist.bin", limit=100000, mode="lru")


async def _temp_blacklist(user_id: int, guild_id: int) -> None:
    await _temp_bl.set(f"{user_id}:{guild_id}", True, 45.0)


async def _is_temp_blacklisted(user_id: int, guild_id: int) -> float:
    val = await _temp_bl.get(f"{user_id}:{guild_id}", bool)
    if val is True:
        key = f"{user_id}:{guild_id}"
        from time import time

        now = time()
        async with _temp_bl.lock:
            entry = _temp_bl.cache.get(key)
            if entry:
                expires, _ = entry
                return max(0.0, expires - now)
    return 0.0


async def check(itx: Interaction) -> bool:
    return await core_check(itx, get_member_cache())


async def deny(itx: Interaction) -> bool:
    if await check(itx):
        return False
    c = cfg_type()
    server_id = getattr(c, "required_server_id", 0)
    role_id = getattr(c, "required_role_id", 0)
    invite = getattr(c, "invite", "")
    if server_id == 0 or role_id == 0:
        return False
    if itx.guild and itx.guild.id == server_id:
        await _temp_blacklist(itx.user.id, itx.guild.id)
        return await itx.error(
            "no raid commands allowed in the required server. you've been temp blacklisted for 45s."
        )
    if not itx.guild or itx.guild.id != server_id:
        msg = (
            f"you need to be in the server to use the bot {invite}"
            if invite
            else "join the server!"
        )
        return await itx.error(msg)
    member = itx.guild.get_member(itx.user.id)
    if member is None:
        msg = (
            f"you need to be in the server to use the bot {invite}"
            if invite
            else "join the server!"
        )
        return await itx.error(msg)
    role = itx.guild.get_role(role_id)
    role_name = role.name if role else "required"
    return await itx.error(f"you need the {role_name} role to use this bot lol")
