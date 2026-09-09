import asyncio
from discord.ext.commands import Cog
from discord.commands import (
    slash_command as command,
    Option,
    ApplicationContext,
    AutocompleteContext
)
from discord.ui import (
    DesignerView,
    TextDisplay,
    Container,
    Separator,
    ActionRow,
    Button
)
from discord import (
    InteractionContextType,
    IntegrationType,
    Interaction,
    InteractionType,
    ButtonStyle,
    SeparatorSpacingSize
)
from utils.cache import diskstore
from models.raid import raidstate
from utils.db import db
from models.user import UserData

async def preset_autocomplete(ctx: AutocompleteContext):
    user = await db.get(ctx.interaction.user.id, UserData)
    if not user or not user.presets:
        return []
    val = ctx.value.lower()
    return [name for name in user.presets if val in name.lower()][:25]

class customraidview(DesignerView):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot
        self.btn5 = "v4:customraid:5x"
        self.btn6 = "v4:customraid:6x"

    def _get_payload(self, state: raidstate):
        msg = state.message
        if not state.bypass:
            return {
                "content": msg,
                "is_v2": False
            }
        return {
            "view": [
                TextDisplay(content=msg).to_component_dict()
            ],
            "is_v2": True
        }

    async def dispatch(self, itx: Interaction, count: int, respond: bool, state: raidstate):
        if respond and state.bypass:
            await itx.response.defer(ephemeral=True)
        elif respond:
            p = self._get_payload(state)
            await itx.response.send_message(content=p["content"])
            count -= 1
            msg = await itx.original_response()
            asyncio.create_task(
                self.bot.db.track_message(
                    str(msg.id),
                    str(itx.application_id),
                    itx.token,
                    itx.channel_id,
                    itx.user.id
                )
            )
        else:
            await itx.response.defer(ephemeral=True)
            
        tasks = []
        for _ in range(count):
            p = self._get_payload(state)
            tasks.append(
                self.bot.v4_webhook.send(
                    ctx=itx,
                    silent=state.silent,
                    **p
                )
            )
        await asyncio.gather(*tasks)

class _2(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.states = diskstore(
            filepath="customraid_cmd_states.bin",
            limit=1000,
            mode="lru"
        )

    @Cog.listener()
    async def on_ready(self):
        self.bot.add_view(customraidview(self.bot))

    @command(
        name="custom-raid",
        description="raid using one of your custom presets",
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
    async def customraid_cmd(
        self,
        ctx: ApplicationContext,
        preset: Option(
            str,
            name="preset",
            description="choose your preset",
            autocomplete=preset_autocomplete,
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
            description="bypass automod?",
            default=False
        )
    ):
        user_data = await db.get(ctx.user.id, UserData)
        if not user_data or not user_data.presets:
            return await ctx.error("you have no presets.", ephemeral=True)
            
        message = user_data.presets.get(preset)
        if not message:
            return await ctx.warn("preset not found.", ephemeral=True)
            
        state = raidstate(
            silent=silent,
            bypass=bypass_automod,
            message=message
        )
        await self.states.set(
            f"{ctx.channel_id}:{ctx.user.id}",
            state,
            3600.0
        )
        
        components = [
            Container(
                TextDisplay(content=f"spamming preset: {preset[:50]}"),
                Separator(
                    divider=True,
                    spacing=SeparatorSpacingSize.small,
                ),
                ActionRow(
                    Button(
                        style=ButtonStyle.primary,
                        label="raid 5x",
                        custom_id="v4:customraid:5x",
                    ),
                    Button(
                        style=ButtonStyle.danger,
                        label="raid 6x",
                        custom_id="v4:customraid:6x",
                    ),
                ),
            ),
        ]
        
        await ctx.respond(
            view=DesignerView(
                *components,
                timeout=None
            ),
            ephemeral=True
        )

    @Cog.listener()
    async def on_interaction(self, itx: Interaction):
        if itx.type != InteractionType.component:
            return
            
        cid = itx.custom_id
        view = customraidview(self.bot)
        if cid not in (view.btn5, view.btn6):
            return
            
        key = f"{itx.channel_id}:{itx.user.id}"
        state = await self.states.get(key, raidstate)
        
        if not state or not state.message:
            return
            
        if cid == view.btn5:
            await view.dispatch(itx, 5, False, state)
        elif cid == view.btn6:
            await view.dispatch(itx, 6, True, state)

def setup(bot):
    bot.add_cog(_2(bot))
