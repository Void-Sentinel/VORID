from discord.commands import (
    slash_command as command,
    Option,
    ApplicationContext
)
from discord.enums import (
    InteractionContextType,
    IntegrationType
)
from discord.ui import (
    DesignerView,
    TextDisplay
)
from discord.ext.commands import Cog

class _10(Cog):
    def __init__(self, bot):
        self.bot = bot

    @command(
        name="say",
        description="send a message through the bot",
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
    async def say(
        self,
        ctx: ApplicationContext,
        message: Option(
            str,
            name="message",
            description="the message to send",
            required=True
        ),
        silent: Option(
            bool,
            name="silent",
            description="send as silent msg?",
            default=False
        ),
        bypass_automod: Option(
            bool,
            name="bypass_automod",
            description="bypass discords automod; BEWARE that invites will NOT show up but they are clickable.",
            default=False
        )
    ):
        from contextlib import suppress
        with suppress(Exception):
            await ctx.respond(
                f"JOIN THE SERVER >>>> {self.bot.cfg.invite}",
                ephemeral=True
            )
        if bypass_automod:
            v4_view = DesignerView(TextDisplay(content=message))
            await self.bot.v4_webhook.send(
                ctx=ctx,
                view=v4_view.to_components(),
                is_v2=True,
                silent=silent
            )
            return
        await self.bot.v4_webhook.send(
            ctx=ctx,
            content=message,
            silent=silent
        )

def setup(bot):
    bot.add_cog(_10(bot))
