import asyncio
import mmap
import random
from contextlib import suppress

from discord import AutocompleteContext, ButtonStyle, Interaction, InteractionType
from discord.commands import ApplicationContext, Option, slash_command as command
from discord.enums import IntegrationType, InteractionContextType, SeparatorSpacingSize
from discord.ext.commands import Cog
from discord.ui import (
    ActionRow,
    Button,
    Container,
    DesignerView,
    Separator,
    TextDisplay,
)

from models.interaction_raid import raidstate, raidtoken
from models.user import UserData
from utils.cache import diskstore
from utils.db import db


def _read_gif(mm: mmap.mmap, offset: int) -> str:
    mm.seek(offset)
    return mm.readline().decode().strip()


def _get_thug_gifs(count: int = 3) -> list[str]:
    f = open("gifs.txt", "rb")
    mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
    try:
        offsets = [0]
        pos = mm.find(b"\n")
        while pos != -1:
            offsets.append(pos + 1)
            pos = mm.find(b"\n", pos + 1)
        raw = [_read_gif(mm, o) for o in random.sample(offsets, count)]
        return [g for g in raw if g]
    finally:
        mm.close()
        f.close()


class _5(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.states = diskstore(filepath="raid_states.bin", limit=1000, mode="lru")
        self._stores: dict[int, diskstore] = {}
        self.farm_id = "v4:raid:farm"
        self.send_id = "v4:raid:send"

    def _get_store(self, cid: int) -> diskstore:
        if cid not in self._stores:
            self._stores[cid] = diskstore(
                filepath=f"tokens_{cid}.bin", limit=1000, mode="lru"
            )
        return self._stores[cid]

    def _get_view(self, tokens: int, sent: int) -> DesignerView:
        components = [
            Container(
                TextDisplay(
                    content=f"interaction tokens: {tokens}\nmessages sent: {sent}\n"
                ),
                Separator(
                    divider=True,
                    spacing=SeparatorSpacingSize.small,
                ),
                ActionRow(
                    Button(
                        style=ButtonStyle.primary,
                        label="farm",
                        custom_id=self.farm_id,
                    ),
                    Button(
                        style=ButtonStyle.danger,
                        label="send the messages",
                        custom_id=self.send_id,
                    ),
                ),
                colour=0xF1C40F,
            ),
        ]
        return DesignerView(*components, timeout=None)

    async def get_presets(self, ctx: AutocompleteContext):
        user = await db.get(ctx.interaction.user.id, UserData, ttl=5.0)
        options = ["thug"]
        options.extend([f"PRESET: {name}" for name in user.presets])

        val = ctx.value.lower()
        return [o for o in options if val in o.lower()][:25]

    @command(
        name="interaction-raid",
        description="raid for interaction tokens",
        contexts={
            InteractionContextType.guild,
            InteractionContextType.bot_dm,
            InteractionContextType.private_channel,
        },
        integration_types={IntegrationType.guild_install, IntegrationType.user_install},
    )
    async def raid_cmd(
        self,
        ctx: ApplicationContext,
        message: Option(
            str,
            name="message",
            description="the message to send",
            required=True,
            autocomplete=get_presets,
        ),
        cooldown: Option(
            float,
            name="cooldown",
            description="seconds to wait between each token dispatch",
            default=0.1,
        ),
        silent: Option(
            bool, name="silent", description="send as silent msg?", default=False
        ),
        bypass_automod: Option(
            bool, name="bypass_automod", description="bypass automod?", default=False
        ),
    ):
        actual_message = message
        if message.startswith("PRESET: "):
            preset_name = message.replace("PRESET: ", "", 1)
            user = await db.get(ctx.user.id, UserData)
            actual_message = user.presets.get(preset_name, message)

        state = raidstate(
            message=actual_message,
            cooldown=cooldown,
            silent=silent,
            bypass=bypass_automod,
        )
        await self.states.set(str(ctx.channel_id), state, 3600.0)

        store = self._get_store(ctx.channel_id)
        tokens = await store.get_all(raidtoken)
        await ctx.respond(view=self._get_view(len(tokens), 0), ephemeral=True)

    @Cog.listener()
    async def on_interaction(self, interaction: Interaction):
        if interaction.type != InteractionType.component:
            return

        cid = interaction.custom_id
        if cid == self.farm_id:
            await self._handle_farm(interaction)
        elif cid == self.send_id:
            await self._handle_send(interaction)

    async def _handle_farm(self, itx: Interaction):
        store = self._get_store(itx.channel_id)
        t = raidtoken(id=str(itx.application_id), token=itx.token)
        await store.set(itx.token, t, 900.0)

        state = await self.states.get(str(itx.channel_id), raidstate) or raidstate()
        tokens = await store.get_all(raidtoken)
        state.sent = len(tokens) * 5
        await self.states.set(str(itx.channel_id), state, 3600.0)

        with suppress(Exception):
            await itx.response.edit_message(
                view=self._get_view(len(tokens), state.sent)
            )

    async def _handle_send(self, itx: Interaction):
        with suppress(Exception):
            await itx.response.defer(ephemeral=True)

        store = self._get_store(itx.channel_id)
        tokens = await store.get_all(raidtoken)

        current_t = raidtoken(id=str(itx.application_id), token=itx.token)
        tokens.append(current_t)

        state = await self.states.get(str(itx.channel_id), raidstate) or raidstate()

        if not tokens:
            return

        await store.clear()
        self._stores.pop(itx.channel_id, None)

        state.sent = 0
        await self.states.set(str(itx.channel_id), state, 3600.0)

        with suppress(Exception):
            await itx.edit_original_response(view=self._get_view(0, 0))

        view_payload = None
        if state.bypass:
            view_payload = [
                Container(TextDisplay(content=state.message)).to_component_dict()
            ]

        sem = asyncio.Semaphore(3)

        is_thug = state.message.lower() == "thug"

        async def _dispatch(t: raidtoken):
            await sem.acquire()
            try:
                if is_thug:
                    gifs = _get_thug_gifs()
                    content = f"@everyone @here {self.bot.cfg.invite}\n" + "\n".join(
                        gifs
                    )
                    with suppress(Exception):
                        await self.bot.v4_webhook.send(
                            ctx=itx,
                            content=content,
                            silent=state.silent,
                            app_id=t.id,
                            token=t.token,
                        )
                else:
                    with suppress(Exception):
                        await self.bot.v4_webhook.send(
                            ctx=itx,
                            content=state.message if not state.bypass else None,
                            silent=state.silent,
                            view=view_payload,
                            is_v2=state.bypass,
                            app_id=t.id,
                            token=t.token,
                        )
            finally:
                sem.release()

        tasks = [_dispatch(t) for t in tokens for _ in range(5)]
        await asyncio.gather(*tasks)


def setup(bot):
    bot.add_cog(_5(bot))
