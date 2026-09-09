from msgspec import Struct


class UserData(Struct):
    presets: dict[str, str] = {}
