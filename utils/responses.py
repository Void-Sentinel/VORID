from discord import (
    Interaction,
    ApplicationContext,
    PartialEmoji,
    ButtonStyle
)
from discord.ui import (
    DesignerView,
    Container,
    Section,
    TextDisplay,
    Button
)

async def _respond_custom(
    ctx: ApplicationContext | Interaction,
    content: str,
    emoji: str,
    color: int,
    ephemeral: bool = True
):
    components = [
        Container(
            Section(
                TextDisplay(content=content),
                accessory=Button(
                    style=ButtonStyle.secondary,
                    emoji=PartialEmoji.from_str(emoji),
                    custom_id="v4:ui:ok",
                ),
            ),
            colour=color
        ),
    ]
    
    view = DesignerView(*components, timeout=None)
    
    msg = None
    if isinstance(ctx, Interaction):
        if ctx.response.is_done():
            msg = await ctx.followup.send(view=view, ephemeral=ephemeral)
        else:
            await ctx.response.send_message(view=view, ephemeral=ephemeral)
            msg = await ctx.original_response()
    else:
        if ctx.response.is_done():
            msg = await ctx.followup.send(view=view, ephemeral=ephemeral)
        else:
            res = await ctx.respond(view=view, ephemeral=ephemeral)
            msg = await res.original_response()

    if msg and hasattr(ctx, "bot") and hasattr(ctx.bot, "db"):
        import asyncio
        itx = getattr(ctx, "interaction", ctx)
        asyncio.create_task(
            ctx.bot.db.track_message(
                str(msg.id),
                str(itx.application_id),
                itx.token,
                itx.channel_id,
                itx.user.id
            )
        )

async def success(self, content: str, ephemeral: bool = True):
    await _respond_custom(
        self,
        content,
        "<:approve:1484984864825409557>",
        0x2ecc71,
        ephemeral
    )

async def warn(self, content: str, ephemeral: bool = True):
    await _respond_custom(
        self,
        content,
        "<:warning:1484984862489313367>",
        0xf1c40f,
        ephemeral
    )

async def error(self, content: str, ephemeral: bool = True):
    await _respond_custom(
        self,
        content,
        "<:deny:1484984838581780652>",
        0xe74c3c,
        ephemeral
    )

def setup():
    ApplicationContext.success = success
    ApplicationContext.warn = warn
    ApplicationContext.error = error
    Interaction.success = success
    Interaction.warn = warn
    Interaction.error = error
