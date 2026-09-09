from __future__ import annotations

from typing import Any

from utils.db import db


class diskstore:
    """
    lmdb-backed cache store
    """

    __slots__ = ("_backend",)

    def __init__(self, filepath: str = "", limit: int = 0, mode: str = "lru"):
        self._backend = db.cache

    async def set(self, key: str, value: Any, ttl: float) -> None:
        await self._backend.set(key, value, ttl)

    async def get(self, key: str, type_ref: Any) -> Any:
        return await self._backend.get(key, type_ref)

    async def get_all(self, type_ref: Any) -> list[Any]:
        return await self._backend.get_all(type_ref)

    async def delete(self, key: str) -> None:
        await self._backend.delete(key)

    async def clear(self) -> None:
        await self._backend.clear()

    @property
    def lock(self):
        class _Lock:
            async def __aenter__(self):
                pass

            async def __aexit__(self, *args):
                pass

        return _Lock()
