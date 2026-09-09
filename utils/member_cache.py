from __future__ import annotations
from asyncio import Lock
from typing import Any
from weakref import WeakValueDictionary

from models.member import cachedmember


class membercache:
    __slots__ = (
        "_mem",
        "_lock",
        "_store",
    )

    def __init__(self):
        self._mem: WeakValueDictionary[int, cachedmember] = WeakValueDictionary()
        self._lock = Lock()
        self._store = None

    def bind_store(self, store: Any) -> None:
        self._store = store

    def get(self, user_id: int) -> cachedmember | None:
        return self._mem.get(user_id)

    def add(self, m: cachedmember) -> None:
        self._mem[m.user_id] = m

    def remove(self, user_id: int) -> None:
        self._mem.pop(user_id, None)

    async def load(self, guild_id: int) -> list[cachedmember]:
        members: list[cachedmember] = []
        if self._store is None:
            return members
        all_members = await self._store.get_all(cachedmember)
        for m in all_members:
            members.append(m)
            self._mem[m.user_id] = m
        return members

    async def save(self, m: cachedmember) -> None:
        if self._store is None:
            return
        await self._store.set(str(m.user_id), m, 86400.0 * 7)

    async def remove_user(self, user_id: int) -> None:
        if self._store is None:
            return
        await self._store.delete(str(user_id))
        self._mem.pop(user_id, None)


_cache: membercache | None = None


def get() -> membercache:
    global _cache
    if _cache is None:
        _cache = membercache()
    return _cache
