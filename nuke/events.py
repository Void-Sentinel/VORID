from __future__ import annotations

import logging
from datetime import datetime, timezone
from time import time
from typing import Any

from nuke.config import get as cfg


async def create(limiter: Any, guild_id: int, headers: dict | None = None) -> None:
    c = cfg()
    now = time()
    # start basically now, end 4 years out (max Discord allows is 5 years)
    start_ts = datetime.fromtimestamp(now + 60, tz=timezone.utc).isoformat()
    end_ts = datetime.fromtimestamp(
        now + (365 * 24 * 60 * 60 * 4), tz=timezone.utc
    ).isoformat()
    payload = {
        "name": c.event_name,
        "description": c.event_description,
        "privacy_level": 2,
        "scheduled_start_time": start_ts,
        "scheduled_end_time": end_ts,
        "entity_type": 3,
        "entity_metadata": {"location": c.event_location},
        "channel_id": None,
    }
    try:
        res = await limiter.request(
            "POST",
            f"guilds:{guild_id}:events:create",
            f"https://discord.com/api/v10/guilds/{guild_id}/scheduled-events",
            json=payload,
            headers=headers,
        )
        if res.status not in (200, 201):
            body = await res.text()
            logging.warning(f"event create {guild_id}: {res.status} {body}")
    except Exception as e:
        logging.warning(f"event create {guild_id}: {e}")
