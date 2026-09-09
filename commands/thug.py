import mmap
import random
import asyncio
from discord.ext.commands import Cog
from discord import (
    ButtonStyle,
    SeparatorSpacingSize,
    InteractionType,
    MediaGalleryItem,
    Interaction,
    ui
)
from discord.enums import (
    InteractionContextType,
    IntegrationType
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
    Separator,
    ActionRow,
    Button,
    MediaGallery
)
from utils.cache import diskstore
from models.thug import thugstate
from contextlib import suppress

def _read_gif(mm: mmap.mmap, offset: int) -> str:
    mm.seek(offset)
    return mm.readline().decode().strip()

class thugview(DesignerView):
    offsets: list[int] | None = None

    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot
        self.btn5 = "v4:thug:5x"
        self.btn6 = "v4:thug:6x"
        self._index()

    def _index(self):
        if thugview.offsets is not None:
            return
        f = open("gifs.txt", "rb")
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        thugview.offsets = [0]
        pos = mm.find(b"\n")
        while pos != -1:
            thugview.offsets.append(pos + 1)
            pos = mm.find(b"\n", pos + 1)
        mm.close()
        f.close()

    def _get_payload(self, state: thugstate):
        f = open("gifs.txt", "rb")
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        try:
            raw = [_read_gif(mm, o) for o in random.sample(thugview.offsets, 3)]
            gifs = [g for g in raw if g]
        finally:
            mm.close()
            f.close()

        if not state.bypass:
            content = f"@everyone @here {self.bot.cfg.invite}\n" + "\n".join(gifs)
            return {"content": content, "is_v2": False}

        items = [MediaGalleryItem(url=g) for g in gifs]
        layout = Container(
            MediaGallery(*items),
            Separator(
                divider=True,
                spacing=SeparatorSpacingSize.small
            ),
            TextDisplay(content=f"@everyone @here {self.bot.cfg.invite}")
        )
        return {
            "view": [layout.to_component_dict()],
            "is_v2": True
        }

    async def dispatch(
        self,
        itx: Interaction,
        count: int,
        respond: bool,
        state: thugstate
    ):
        p = self._get_payload(state)
        view_dict = p.pop("view", None)
        is_v2 = p.pop("is_v2", False)
        
        if respond and view_dict:
            p["view"] = ui.View.from_dict(view_dict[0])

        if respond and not itx.response.is_done():
            await itx.response.send_message(**p)
        elif respond:
            await itx.edit_original_response(**p)
        elif not itx.response.is_done():
            await itx.response.defer(ephemeral=True)

        if respond:
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
            p["is_v2"] = is_v2
            if view_dict: p["view"] = view_dict
        else:
            await self.bot.v4_webhook.send(ctx=itx, silent=state.silent, **p)

        tasks = []
        for _ in range(count - 1):
            tasks.append(
                self.bot.v4_webhook.send(
                    ctx=itx,
                    silent=state.silent,
                    **self._get_payload(state)
                )
            )
        
        if tasks:
            await asyncio.gather(*tasks)

class _11(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.states = diskstore(
            filepath="thug_states.bin",
            limit=1000,
            mode="lru"
        )

    @Cog.listener()
    async def on_ready(self):
        self.bot.add_view(thugview(self.bot))

    @command(
        name="thug",
        description="thug the server",
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
    async def thug_cmd(
        self,
        ctx: ApplicationContext,
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
        state = thugstate(
            silent=silent,
            bypass=bypass_automod
        )
        await self.states.set(f"{ctx.channel_id}:{ctx.user.id}", state, 3600.0)

        components = [
            Container(
                TextDisplay(content="thug"),
                Separator(
                    divider=True,
                    spacing=SeparatorSpacingSize.small,
                ),
                ActionRow(
                    Button(
                        style=ButtonStyle.primary,
                        label="thug 5x",
                        custom_id="v4:thug:5x",
                    ),
                    Button(
                        style=ButtonStyle.danger,
                        label="thug 6x",
                        custom_id="v4:thug:6x",
                    ),
                ),
            ),
        ]
        await ctx.respond(
            view=DesignerView(*components, timeout=None),
            ephemeral=True
        )

    @Cog.listener()
    async def on_interaction(self, itx: Interaction):
        if itx.type != InteractionType.component:
            return
            
        cid = itx.custom_id
        view = thugview(self.bot)
        
        if cid not in (view.btn5, view.btn6):
            return

        key = f"{itx.channel_id}:{itx.user.id}"
        state = await self.states.get(key, thugstate) or thugstate()
        
        if cid == view.btn5:
            await view.dispatch(itx, 5, False, state)
        elif cid == view.btn6:
            await view.dispatch(itx, 6, True, state)

def setup(bot):
    bot.add_cog(_11(bot))
