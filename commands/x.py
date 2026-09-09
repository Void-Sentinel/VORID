from contextlib import suppress

from discord import IntegrationType, InteractionContextType
from discord.commands import (
    ApplicationContext,
    AutocompleteContext,
    Option,
    SlashCommandGroup,
)
from discord.ext.commands import Cog, check

from models.blacklist import blacklistdata
from utils.db import db

_BL_KEY = 0


async def _load() -> blacklistdata:
    return await db.get(_BL_KEY, blacklistdata)


async def _save(data: blacklistdata) -> None:
    await db.set(_BL_KEY, data)


def _owner_check(ctx: ApplicationContext) -> bool:
    return ctx.user.id in ctx.bot.cfg.owners


def owner_only():
    return check(_owner_check)


async def _remove_autocomplete(ctx: AutocompleteContext):
    bl = getattr(ctx.interaction.client, "blacklist", None)
    if not bl:
        return []
    val = ctx.value.lower()
    kind = ctx.options.get("type", "user")
    if kind == "server":
        return [str(i) for i in bl.servers if val in str(i)][:25]
    return [str(i) for i in bl.users if val in str(i)][:25]


async def _fetch_invites(guild) -> list:
    try:
        return await guild.invites()
    except Exception:
        return []


async def _get_existing_invite(guild) -> str | None:
    invites = await _fetch_invites(guild)
    if invites:
        return invites[0].url
    return None


async def _create_permanent_invite(channel) -> str | None:
    try:
        invite = await channel.create_invite(max_age=0, max_uses=0)
        return invite.url
    except Exception:
        return None


async def _try_channels(guild) -> str | None:
    for channel in guild.text_channels:
        url = await _create_permanent_invite(channel)
        if url:
            return url
    return None


async def _create_one_invite(guild) -> str | None:
    existing = await _get_existing_invite(guild)
    if existing:
        return f"**{guild.name}** ({guild.id}): {existing}"

    url = await _try_channels(guild)
    if url:
        return f"**{guild.name}** ({guild.id}): {url}"
    return None


async def _flush_chunk(ctx: ApplicationContext, current: str, too_long: bool) -> str:
    if not too_long:
        return current
    await ctx.respond(current, ephemeral=True)
    return ""


async def _send_chunks(ctx: ApplicationContext, lines: list[str]):
    current = ""
    for line in lines:
        too_long = len(current) + len(line) + 1 > 1900
        current = await _flush_chunk(ctx, current, too_long)
        current = f"{current}\n{line}" if current else line
    if current:
        await ctx.respond(current, ephemeral=True)


class _13(Cog):
    def __init__(self, bot):
        self.bot = bot

    x = SlashCommandGroup(
        name="x",
        description="manage the bot blacklist",
        contexts={
            InteractionContextType.guild,
            InteractionContextType.bot_dm,
            InteractionContextType.private_channel,
        },
        integration_types={IntegrationType.guild_install, IntegrationType.user_install},
    )

    async def _check_owner(self, ctx: ApplicationContext) -> bool:
        return ctx.user.id in ctx.bot.cfg.owners

    @x.command(name="add", description="blacklist a user or server")
    @check(lambda ctx: ctx.user.id in ctx.bot.cfg.owners)
    async def x_add(
        self,
        ctx: ApplicationContext,
        type: Option(
            str,
            name="type",
            description="user or server",
            choices=["user", "server"],
            required=True,
        ),
        id: Option(
            str,
            name="id",
            description="the user or server id to blacklist",
            required=True,
        ),
    ):
        try:
            target_id = int(id)
        except ValueError:
            return await ctx.error("invalid id.")

        bl = await _load()

        if type == "user":
            if target_id in bl.users:
                return await ctx.warn(f"`{target_id}` is already blacklisted.")
            bl.users.append(target_id)
            await _save(bl)
            ctx.bot.blacklist = bl
            return await ctx.success(f"blacklisted user `{target_id}`.")

        if target_id in bl.servers:
            return await ctx.warn(f"`{target_id}` is already blacklisted.")
        bl.servers.append(target_id)
        await _save(bl)
        ctx.bot.blacklist = bl
        return await ctx.success(f"blacklisted server `{target_id}`.")

    @x.command(name="remove", description="remove a user or server from the blacklist")
    @check(lambda ctx: ctx.user.id in ctx.bot.cfg.owners)
    async def x_remove(
        self,
        ctx: ApplicationContext,
        type: Option(
            str,
            name="type",
            description="user or server",
            choices=["user", "server"],
            required=True,
        ),
        id: Option(
            str,
            name="id",
            description="the id to remove",
            autocomplete=_remove_autocomplete,
            required=True,
        ),
    ):
        try:
            target_id = int(id)
        except ValueError:
            return await ctx.error("invalid id.")

        bl = await _load()

        if type == "user":
            if target_id not in bl.users:
                return await ctx.warn(f"`{target_id}` is not blacklisted.")
            bl.users.remove(target_id)
            await _save(bl)
            ctx.bot.blacklist = bl
            return await ctx.success(f"removed user `{target_id}` from blacklist.")

        if target_id not in bl.servers:
            return await ctx.warn(f"`{target_id}` is not blacklisted.")
        bl.servers.remove(target_id)
        await _save(bl)
        ctx.bot.blacklist = bl
        return await ctx.success(f"removed server `{target_id}` from blacklist.")

    @x.command(name="list", description="list all blacklisted users or servers")
    @check(lambda ctx: ctx.user.id in ctx.bot.cfg.owners)
    async def x_list(
        self,
        ctx: ApplicationContext,
        type: Option(
            str,
            name="type",
            description="user or server",
            choices=["user", "server"],
            required=True,
        ),
    ):
        bl = await _load()

        if type == "user":
            if not bl.users:
                return await ctx.warn("no blacklisted users.")
            ids = "\n".join(f"`{i}`" for i in bl.users)
            return await ctx.success(f"**blacklisted users:**\n{ids}")

        if not bl.servers:
            return await ctx.warn("no blacklisted servers.")
        ids = "\n".join(f"`{i}`" for i in bl.servers)
        return await ctx.success(f"**blacklisted servers:**\n{ids}")

    @x.command(name="invite", description="create invites for all guilds the bot is in")
    @check(lambda ctx: ctx.user.id in ctx.bot.cfg.owners)
    async def x_invite(self, ctx: ApplicationContext):
        await ctx.defer(ephemeral=True)
        results = [await _create_one_invite(g) for g in ctx.bot.guilds]
        lines = [r for r in results if r]

        if not lines:
            return await ctx.error("could not create any guild invites.")

        await _send_chunks(ctx, lines)


def setup(bot):
    bot.add_cog(_13(bot))
