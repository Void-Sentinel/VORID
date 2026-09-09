from __future__ import annotations

import random

from models.nuke import nukecfg
from utils.jsonc import load as _jload

_cfg: nukecfg | None = None

_emoji_codes = [
    format(ord(e), "x")
    for e in [
        "\U0001f595",
        "\U0001f64f",
        "\U0001f970",
        "\U0001f973",
        "\U0001f974",
        "\U0001f975",
        "\U0001f976",
        "\U0001f97a",
        "\U0001f9d0",
        "\U0001f9d1",
        "\U0001f9d2",
        "\U0001f9d3",
        "\U0001f9d4",
        "\U0001f9d5",
        "\U0001f9d6",
        "\U0001f9d7",
        "\U0001f9d8",
        "\U0001f9d9",
        "\U0001f9da",
        "\U0001f9db",
        "\U0001f9dc",
        "\U0001f9dd",
        "\U0001f9de",
        "\U0001f9df",
        "\U0001f9e0",
        "\U0001f9e1",
        "\U0001f9e2",
        "\U0001f9e3",
        "\U0001f9e4",
        "\U0001f9e5",
        "\U0001f9e6",
        "\U0001f9e7",
        "\U0001f9e8",
        "\U0001f9e9",
        "\U0001f9ea",
        "\U0001f9eb",
        "\U0001f9ec",
        "\U0001f9ed",
        "\U0001f9ee",
        "\U0001f9ef",
        "\U0001f9f0",
        "\U0001f9f1",
        "\U0001f9f2",
        "\U0001f9f3",
        "\U0001f9f4",
        "\U0001f9f5",
        "\U0001f9f6",
        "\U0001f9f7",
        "\U0001f9f8",
        "\U0001f9f9",
        "\U0001f9fa",
        "\U0001f9fb",
        "\U0001f9fc",
        "\U0001f9fd",
        "\U0001f9fe",
        "\U0001f9ff",
        "\U0001fa00",
        "\U0001fa01",
        "\U0001fa02",
        "\U0001fa03",
        "\U0001fa04",
        "\U0001fa05",
        "\U0001fa06",
        "\U0001fa07",
        "\U0001fa08",
        "\U0001fa09",
        "\U0001fa0a",
        "\U0001fa0b",
        "\U0001fa0c",
        "\U0001fa0d",
        "\U0001fa0e",
        "\U0001fa0f",
        "\U0001fa10",
        "\U0001fa11",
        "\U0001fa12",
        "\U0001fa13",
        "\U0001fa14",
        "\U0001fa15",
        "\U0001fa16",
        "\U0001fa17",
        "\U0001fa18",
        "\U0001fa19",
        "\U0001fa1a",
        "\U0001fa1b",
        "\U0001fa1c",
        "\U0001fa1d",
        "\U0001fa1e",
        "\U0001fa1f",
        "\U0001fa20",
        "\U0001fa21",
        "\U0001fa22",
        "\U0001fa23",
        "\U0001fa24",
        "\U0001fa25",
        "\U0001fa26",
        "\U0001fa27",
        "\U0001fa28",
        "\U0001fa29",
        "\U0001fa2a",
        "\U0001fa2b",
        "\U0001fa2c",
        "\U0001fa2d",
        "\U0001fa2e",
        "\U0001fa2f",
        "\U0001fa30",
        "\U0001fa31",
        "\U0001fa32",
        "\U0001fa33",
        "\U0001fa34",
        "\U0001fa35",
        "\U0001fa36",
        "\U0001fa37",
        "\U0001fa38",
        "\U0001fa39",
        "\U0001fa3a",
        "\U0001fa3b",
        "\U0001fa3c",
        "\U0001fa3d",
        "\U0001fa3e",
        "\U0001fa3f",
        "\U0001fa40",
        "\U0001fa41",
        "\U0001fa42",
        "\U0001fa43",
        "\U0001fa44",
        "\U0001fa45",
        "\U0001fa46",
        "\U0001fa47",
        "\U0001fa48",
        "\U0001fa49",
        "\U0001fa4a",
        "\U0001fa4b",
        "\U0001fa4c",
        "\U0001fa4d",
        "\U0001fa4e",
        "\U0001fa4f",
        "\U0001fa50",
        "\U0001fa51",
        "\U0001fa52",
        "\U0001fa53",
        "\U0001fa54",
        "\U0001fa55",
        "\U0001fa56",
        "\U0001fa57",
        "\U0001fa58",
        "\U0001fa59",
        "\U0001fa5a",
        "\U0001fa5b",
        "\U0001fa5c",
        "\U0001fa5d",
        "\U0001fa5e",
        "\U0001fa5f",
        "\U0001fa60",
        "\U0001fa61",
        "\U0001fa62",
        "\U0001fa63",
        "\U0001fa64",
        "\U0001fa65",
        "\U0001fa66",
        "\U0001fa67",
        "\U0001fa68",
        "\U0001fa69",
        "\U0001fa6a",
        "\U0001fa6b",
        "\U0001fa6c",
        "\U0001fa6d",
        "\U0001fa6e",
        "\U0001fa6f",
    ]
]

_avatar_pool = [
    f"https://images.emojiterra.com/twitter/v14.0/128px/{code}.png"
    for code in _emoji_codes
]

_msgs: list[str] | None = None
_names: list[str] | None = None
_roles: list[str] | None = None
_channels: list[str] | None = None
_categories: list[str] | None = None


def get() -> nukecfg:
    global _cfg
    if _cfg is None:
        _cfg = _jload("nuke.jsonc", nukecfg)
    return _cfg


def rand_channel() -> str:
    global _channels
    if _channels is None:
        _channels = get().channel_names
    return random.choice(_channels)


def rand_category() -> str:
    global _categories
    if _categories is None:
        cfg = get()
        _categories = cfg.category_names if cfg.category_names else cfg.channel_names
    return random.choice(_categories)


def rand_role() -> str:
    global _roles
    if _roles is None:
        _roles = get().role_names
    return random.choice(_roles)


def rand_webhook_name() -> str:
    global _names
    if _names is None:
        _names = get().webhook_names
    return random.choice(_names)


def rand_msg() -> str:
    global _msgs
    if _msgs is None:
        _msgs = get().messages
    return random.choice(_msgs)


def rand_avatar_url() -> str:
    return random.choice(_avatar_pool)
