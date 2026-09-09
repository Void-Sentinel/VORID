from __future__ import annotations

import logging

from discord.http import Route


async def update_bio(bot):
    payload = {
        "description": "Raid bot source code https://github.com/fuhnut/777-raid-bot/tree/main"
    }
    try:
        await bot.http.request(Route("PATCH", "/applications/@me"), json=payload)
        logging.info("application bio updated successfully")
    except Exception as error:
        logging.error(f"failed to update bio: {error} :c")
