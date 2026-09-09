import asyncio
from discord.ext.commands import Cog
from discord import (
    ButtonStyle,
    Interaction,
    InteractionType,
    User
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
    Button
)
from contextlib import suppress
from discord.enums import (
    InteractionContextType,
    IntegrationType
)
from utils.cache import diskstore

class _4(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.states = diskstore(
            filepath="ghostping_states.bin",
            limit=1000,
            mode="lru"
        )
        self.ping_id = "v4:ghostping:fire"

    def _get_view(self, target: str) -> DesignerView:
        components = [
            Container(
                TextDisplay(content=f"ghostping target: {target}"),
                ActionRow(
                    Button(
                        style=ButtonStyle.danger,
                        label="ghostping",
                        custom_id=self.ping_id,
                    )
                ),
                colour=0xe74c3c
            ),
        ]
        return DesignerView(*components, timeout=None)

    @command(
        name="ghostping",
        description="ghostping someone or @everyone",
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
    async def ghostping_cmd(
        self,
        ctx: ApplicationContext,
        user: Option(
            User,
            name="user",
            description="the user to ghostping (defaults to @everyone)",
            default=None,
            required=False
        )
    ):
        content = user.mention if user else "@everyone"
        res = await ctx.respond(
            view=self._get_view(content),
            ephemeral=True
        )
        msg = await res.original_response()
        await self.states.set(str(msg.id), content, 3600.0)

    @Cog.listener()
    async def on_interaction(self, interaction: Interaction):
        if interaction.type != InteractionType.component:
            return
            
        if interaction.custom_id != self.ping_id:
            return

        target = await self.states.get(str(interaction.message.id), str) or "@everyone"

        async def _ping_once(respond=False):
            if respond:
                with suppress(Exception):
                    await interaction.response.send_message(target)
                    await asyncio.sleep(0.1)
                    await interaction.delete_original_response()
                return

            res = await self.bot.v4_webhook.send(
                ctx=interaction,
                content=target
            )
            if res and "id" in res:
                await asyncio.sleep(0.1)
                await self.bot.v4_webhook.delete(
                    itx=interaction,
                    msg_id=res["id"]
                )

        tasks = [_ping_once(True)]
        tasks.extend([_ping_once() for _ in range(4)])
        await asyncio.gather(*tasks)

def setup(bot):
    bot.add_cog(_4(bot))
