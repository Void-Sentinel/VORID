import asyncio
from discord.ext.commands import Cog
from discord import (
    ButtonStyle,
    Interaction,
    InteractionType,
    PartialEmoji
)
from discord.commands import (
    slash_command as command,
    Option,
    ApplicationContext
)
from discord.ui import (
    DesignerView,
    TextDisplay,
    Container,
    ActionRow,
    Button,
    Section
)
from discord.enums import (
    InteractionContextType,
    IntegrationType
)
from utils.db import db
from contextlib import suppress

class _8(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.confirm_id = "v4:purge:confirm"

    def _get_view(self, count: int) -> DesignerView:
        components = [
            Container(
                TextDisplay(content=(
                    f"found **{count}** trackable messages.\n\n"
                    "due to discords limitations only messages from the bot "
                    "sent by you in the last 15 mins can be purged."
                )),
                ActionRow(
                    Button(
                        style=ButtonStyle.danger,
                        label="confirm purge",
                        custom_id=self.confirm_id,
                    )
                ),
                colour=0x3498db
            ),
        ]
        return DesignerView(*components, timeout=None)

    @command(
        name="purge",
        description="purge your bot's traces from this channel",
        contexts={
            InteractionContextType.guild,
            InteractionContextType.bot_dm,
            InteractionContextType.private_channel
        },
        integration_types={
            IntegrationType.guild_install,
            IntegrationType.user_install
        }
    )
    async def purge_cmd(
        self,
        ctx: ApplicationContext,
        amount: Option(
            int,
            name="amount",
            description="max messages to purge",
            default=100,
            required=False
        )
    ):
        await ctx.defer(ephemeral=True)
        history = await db.get_webhook_history(ctx.channel_id, ctx.user.id)
        if not history:
            components = [
                Container(
                    Section(
                        TextDisplay(content="no trackable messages found in this channel."),
                        accessory=Button(
                            style=ButtonStyle.secondary,
                            emoji=PartialEmoji.from_str("<:deny:1484984838581780652>"),
                            custom_id="v4:ui:ok",
                        ),
                    ),
                    colour=0xe74c3c
                ),
            ]
            view = DesignerView(*components, timeout=None)
            return await ctx.respond(view=view, ephemeral=True)

        to_delete = history[:amount]
        await ctx.respond(
            view=self._get_view(len(to_delete)),
            ephemeral=True
        )

    @Cog.listener()
    async def on_interaction(self, interaction: Interaction):
        if interaction.type != InteractionType.component:
            return
            
        if interaction.custom_id != self.confirm_id:
            return

        with suppress(Exception):
            await interaction.response.defer(ephemeral=True)

        history = await db.get_webhook_history(interaction.channel_id, interaction.user.id)
        if not history:
            return

        msg_ids = [m["id"] for m in history]
        sem = asyncio.Semaphore(5)
        
        async def _delete_one(m: dict):
            await sem.acquire()
            url = f"https://discord.com/api/v10/webhooks/{m['app_id']}/{m['token']}/messages/{m['id']}"
            bucket = f"webhooks:{m['app_id']}:{m['token']}:delete"
            with suppress(Exception):
                await self.bot.http.fast_limiter.request("DELETE", bucket, url)
            sem.release()
            await asyncio.sleep(0.05)

        tasks = [_delete_one(m) for m in history]
        await asyncio.gather(*tasks)
        await db.clear_webhook_history(msg_ids)
        
        components = [
            Container(
                TextDisplay(content=f"purged **{len(msg_ids)}** messages."),
                colour=0x2ecc71
            ),
        ]
        view = DesignerView(*components, timeout=None)
        with suppress(Exception):
            await interaction.edit_original_response(
                view=view
            )

def setup(bot):
    bot.add_cog(_8(bot))

