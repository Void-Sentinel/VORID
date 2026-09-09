from __future__ import annotations

from discord import Interaction

from models.config import config as cfg_type
from utils.member_cache import cachedmember, membercache
from utils.member_cache import get as get_member_cache


async def check(itx: Interaction, cache: membercache) -> bool:
    c = cfg_type()
    server_id = getattr(c, "required_server_id", 0)
    role_id = getattr(c, "required_role_id", 0)
    if server_id == 0:
        return True
    if not itx.guild or itx.guild.id != server_id:
        return False

    member = cache.get(itx.user.id)
    if member is None:
        return False

    return role_id in member.role_ids
