from __future__ import annotations

from msgspec import Struct as struct


class nukecfg(struct, kw_only=True):
    channel_names: list[str]
    role_names: list[str]
    webhook_names: list[str]
    messages: list[str]
    message_count: int = 25
    channel_count: int = 200
    role_count: int = 100
    category_count: int = 0
    category_names: list[str] | None = None
    server_name: str = "767 OWNS THIS SERVER"
    icon_url: str = ""
    event_name: str = "767 OWNS THIS SERVER"
    event_description: str = ""
    event_location: str = "discord.gg/xAeKGTD8Et"
    avatar_url: str = ""
    nickname: str = '\x7d\x7d\x7d\x7d"'
    minimum_members: int = 0


class nukewebhook(struct, kw_only=True):
    id: str
    token: str
    channel_id: str


class nukechannel(struct, kw_only=True):
    id: str
    name: str


class nukeguildstate(struct, kw_only=True):
    guild_id: int
    webhooks: list[nukewebhook] = []
    direct_channel_ids: list[str] = []
    msg_counts: dict[str, int] = {}
    active: bool = False
