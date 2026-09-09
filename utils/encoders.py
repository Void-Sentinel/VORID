from __future__ import annotations

from msgspec.json import decode as _json_decode
from msgspec.msgpack import decode as _mp_decode
from msgspec.msgpack import encode as _mp_encode

_encoder = _mp_encode


def encode(obj: object) -> bytes:
    return _encoder(obj)


def decode(data: bytes, type: type | None = None) -> object:
    if type is None:
        return _mp_decode(data)
    return _mp_decode(data, type=type)


def decode_json(data: str | bytes, type: type | None = None) -> object:
    if type is None:
        return _json_decode(data)
    return _json_decode(data, type=type)
