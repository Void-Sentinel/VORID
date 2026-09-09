from discord import (
    Interaction,
    ApplicationContext,
    InteractionType
)
from discord.ext.commands import Cog
from discord.commands import slash_command as command
from discord.ui import (
    DesignerView,
    Container,
    Section,
    TextDisplay,
    Button,
    Modal,
    InputText,
    Select,
    DesignerModal,
    Label
)
from discord import (
    ButtonStyle,
    IntegrationType,
    InteractionContextType,
    InputTextStyle,
    SelectOption
)
from utils.db import db
from models.user import UserData

class add_modal(Modal):
    def __init__(self):
        super().__init__(
            title="add custom preset",
            custom_id="preset_add_modal"
        )
        self.name = InputText(
            label="preset name",
            placeholder="e.g. '67'",
            max_length=100,
            custom_id="preset_name_input"
        )
        self.message = InputText(
            label="raid message",
            placeholder="enter your raid message here",
            style=InputTextStyle.long,
            max_length=2000,
            custom_id="preset_message_input"
        )
        self.add_item(self.name)
        self.add_item(self.message)

    async def callback(self, itx: Interaction):
        user = await db.get(itx.user.id, UserData)
        
        if len(user.presets) >= 10 and self.name.value not in user.presets:
            return await itx.error("you have reached the limit of 10 presets pls remove one :c")
            
        user.presets[self.name.value] = self.message.value
        
        await db.set(itx.user.id, user)
        await itx.success(f"preset '**{self.name.value}**' added successfully.")

class remove_modal(DesignerModal):
    def __init__(
        self,
        presets_data: dict[str, str],
        user_id: int
    ):
        super().__init__(
            title="remove preset",
            custom_id="preset_remove_modal"
        )
        self.user_id = user_id
        self.presets_data = presets_data
        
        options = [
            SelectOption(
                label=name,
                value=name
            ) for name in presets_data
        ][:25]
        
        self.select = Select(
            placeholder="select a preset to remove",
            options=options,
            custom_id="preset_remove_select"
        )
        self.add_item(
            Label(
                label="choose preset",
                item=self.select
            )
        )

    async def callback(self, itx: Interaction):
        if not self.select.values:
            return await itx.warn("no selection made")
            
        name = self.select.values[0]
        self.presets_data.pop(name, None)
        
        user = await db.get(self.user_id, UserData)
        user.presets = self.presets_data
        
        if user.presets:
            await db.set(self.user_id, user)
        else:
            await db.delete(self.user_id)
            
        await itx.success(f"preset '**{name}**' removed.")

class _7(Cog):
    def __init__(self, bot):
        self.bot = bot

    @command(
        name="setpresetmessage",
        description="manage your custom raid messages",
        integration_types={
            IntegrationType.guild_install,
            IntegrationType.user_install
        },
        contexts={
            InteractionContextType.guild,
            InteractionContextType.bot_dm,
            InteractionContextType.private_channel
        }
    )
    async def setpresetmessage(self, ctx: ApplicationContext):
        components = [
            Container(
                Section(
                    TextDisplay(content="add custom message"),
                    accessory=Button(
                        style=ButtonStyle.success,
                        label="add",
                        custom_id="preset_add",
                    ),
                ),
                Section(
                    TextDisplay(content="remove message"),
                    accessory=Button(
                        style=ButtonStyle.danger,
                        label="remove",
                        custom_id="preset_remove",
                    ),
                ),
                Section(
                    TextDisplay(content="list all your message"),
                    accessory=Button(
                        style=ButtonStyle.primary,
                        label="list",
                        custom_id="preset_list",
                    ),
                ),
                colour=0x3498db
            ),
        ]
        
        view = DesignerView(
            *components,
            timeout=None
        )
        
        await ctx.respond(
            view=view,
            ephemeral=True
        )

    @Cog.listener()
    async def on_interaction(self, itx: Interaction):
        if itx.type != InteractionType.component:
            return
            
        cid = itx.custom_id
        if cid == "preset_add":
            await itx.response.send_modal(add_modal())
            
        elif cid == "preset_list":
            user = await db.get(itx.user.id, UserData)
            
            if not user.presets:
                return await itx.error("you have no preset messages.")
            
            sections = [
                Section(
                    TextDisplay(content=name),
                    accessory=Button(
                        style=ButtonStyle.secondary,
                        label="view message",
                        custom_id=f"preset:view:{name}",
                    ),
                ) for name in user.presets
            ]
            
            view = DesignerView(
                Container(
                    *sections,
                    colour=0x3498db
                ),
                timeout=None
            )
            
            await itx.response.send_message(
                view=view,
                ephemeral=True
            )
            
        elif cid.startswith("preset:view:"):
            name = cid.split(":", 2)[2]
            user = await db.get(itx.user.id, UserData)
            msg = user.presets.get(name)
            
            if not msg:
                return await itx.error("preset not found.")
            
            await itx.response.send_message(
                content=f"{msg}",
                ephemeral=True
            )
            
        elif cid == "preset_remove":
            user = await db.get(itx.user.id, UserData)
            
            if not user.presets:
                return await itx.error("nothing to remove")
            
            await itx.response.send_modal(
                remove_modal(user.presets, itx.user.id)
            )

def setup(bot):
    bot.add_cog(_7(bot))
