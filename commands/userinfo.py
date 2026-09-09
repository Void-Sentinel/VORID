from discord.ext.commands import Cog
from discord.commands import (
    slash_command as command,
    Option,
    ApplicationContext
)
from discord.ui import (
    DesignerView,
    TextDisplay,
    Container,
    MediaGallery,
    Section,
    Thumbnail
)
from discord import InteractionContextType, IntegrationType, User
class _12(Cog):
    def __init__(self, bot):
        self.bot = bot

    @command(
        name="userinfo",
        description="show info about a user?. avatars & server tag included",
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
    async def userinfo_cmd(
        self,
        ctx: ApplicationContext,
        target: Option(
            User,
            name="user",
            description="the user to inspect",
            required=False
        ),
        ephemeral: Option(
            bool,
            name="ephemeral",
            description="hide the message?",
            default=True
        )
    ):
        user = target or ctx.user
        
        flags = [f.name for f in user.public_flags.all()] if hasattr(user, "public_flags") else []
        flag_str = ", ".join(flags) if flags else "none"
        
        member = ctx.guild.get_member(user.id) if ctx.guild else None
        
        role_tag = "n/a"
        if hasattr(user, "primary_guild") and user.primary_guild:
            role_tag = user.primary_guild.tag
            
        created = f"<t:{int(user.created_at.timestamp())}:R>"
        joined = f"<t:{int(member.joined_at.timestamp())}:R>" if member and member.joined_at else "n/a"
        
        stats = (
            f"**user:** {user.name}\n"
            f"**id:** {user.id}\n"
            f"**created:** {created}\n"
            f"**joined:** {joined}\n"
            f"**server tag:** {role_tag}\n"
            f"**flags:** {flag_str}"
        )
        
        gal = MediaGallery()
        if user.display_avatar:
            gal.add_item(user.display_avatar.url, description="avatar")
            
        if member and getattr(member, "guild_avatar", None):
            gal.add_item(member.guild_avatar.url, description="guild avatar")
            
        if getattr(user, "avatar_decoration", None):
            gal.add_item(user.avatar_decoration.url, description="avatar decoration")
            
        container_items = [TextDisplay(content=stats), gal]
        
        if hasattr(user, "primary_guild") and user.primary_guild and user.primary_guild.badge:
            container_items.append(
                Section(
                    TextDisplay(content="server tag / clan badge"),
                    accessory=Thumbnail(url=user.primary_guild.badge.url)
                )
            )
            
        components = [
            Container(*container_items)
        ]
        
        await ctx.respond(
            view=DesignerView(
                *components,
                timeout=None
            ),
            ephemeral=ephemeral
        )

def setup(bot):
    bot.add_cog(_12(bot))
