import asyncio
from pathlib import Path

from discord import (
    ButtonStyle,
    Interaction,
    InteractionType,
    SeparatorSpacingSize,
    ui,
)
from discord.commands import ApplicationContext, Option
from discord.commands import slash_command as command
from discord.enums import IntegrationType, InteractionContextType
from discord.ext.commands import Cog
from discord.ui import (
    ActionRow,
    Button,
    Container,
    DesignerView,
    Separator,
    TextDisplay,
)

from models.raid import raidstate
from utils.cache import diskstore


class floodview(DesignerView):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot
        self.btn5 = "v4:floodcmd:5x"
        self.btn6 = "v4:floodcmd:6x"

    def _get_payload(self, state: raidstate):
        msg = state.message
        if not state.bypass:
            return {"content": msg, "is_v2": False}
        return {"view": [TextDisplay(content=msg).to_component_dict()], "is_v2": True}

    async def dispatch(
        self, itx: Interaction, count: int, respond: bool, state: raidstate
    ):
        p = self._get_payload(state)
        if respond:
            is_v2 = p.pop("is_v2", False)
            view_dict = p.pop("view", None)
            if view_dict:
                p["view"] = ui.View.from_dict(view_dict[0])
            if not itx.response.is_done():
                await itx.response.send_message(**p)
            else:
                await itx.edit_original_response(**p)

            msg = await itx.original_response()
            asyncio.create_task(
                self.bot.db.track_message(
                    str(msg.id),
                    str(itx.application_id),
                    itx.token,
                    itx.channel_id,
                    itx.user.id,
                )
            )
            p["is_v2"] = is_v2
            if view_dict:
                p["view"] = view_dict
        else:
            if not itx.response.is_done():
                await itx.response.defer(ephemeral=True)
            await self.bot.v4_webhook.send(ctx=itx, silent=state.silent, **p)

        tasks = []
        for _ in range(count - 1):
            tasks.append(
                self.bot.v4_webhook.send(
                    ctx=itx, silent=state.silent, **self._get_payload(state)
                )
            )
        if tasks:
            await asyncio.gather(*tasks)


class _3(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.states = diskstore(filepath="flood_cmd_states.bin", limit=1000, mode="lru")

    @Cog.listener()
    async def on_ready(self):
        self.bot.add_view(floodview(self.bot))

    @command(
        name="flood",
        description="flood the channel",
        contexts={
            InteractionContextType.guild,
            InteractionContextType.bot_dm,
            InteractionContextType.private_channel,
        },
        integration_types={IntegrationType.guild_install, IntegrationType.user_install},
    )
    async def flood_cmd(
        self,
        ctx: ApplicationContext,
        message: Option(
            str, name="message", description="message to flood", required=True
        ),
        silent: Option(
            bool, name="silent", description="send as silent msg?", default=False
        ),
        bypass_automod: Option(
            bool, name="bypass_automod", description="bypass automod?", default=False
        ),
    ):
        state = raidstate(message=message, silent=silent, bypass=bypass_automod)
        await self.states.set(f"{ctx.channel_id}:{ctx.user.id}", state, 3600.0)

        components = [
            Container(
                TextDisplay(content="flood"),
                Separator(
                    divider=True,
                    spacing=SeparatorSpacingSize.small,
                ),
                ActionRow(
                    Button(
                        style=ButtonStyle.primary,
                        label="flood 5x",
                        custom_id="v4:floodcmd:5x",
                    ),
                    Button(
                        style=ButtonStyle.danger,
                        label="flood 6x",
                        custom_id="v4:floodcmd:6x",
                    ),
                ),
            ),
        ]
        await ctx.respond(view=DesignerView(*components, timeout=None), ephemeral=True)

    @Cog.listener()
    async def on_interaction(self, itx: Interaction):
        if itx.type != InteractionType.component:
            return

        cid = itx.custom_id
        view = floodview(self.bot)

        if cid not in (view.btn5, view.btn6):
            return

        key = f"{itx.channel_id}:{itx.user.id}"
        state = await self.states.get(key, raidstate) or raidstate()

        if cid == view.btn5:
            await view.dispatch(itx, 5, False, state)
        elif cid == view.btn6:
            await view.dispatch(itx, 6, True, state)


def setup(bot):
    bot.add_cog(_3(bot))
