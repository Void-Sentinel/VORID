from __future__ import annotations

import logging
from pathlib import Path
import time
from typing import Any

from lmdb import Environment
from lmdb import open as lmdb_open

from utils.encoders import decode, encode


class _LMDBStore:
    __slots__ = ("env", "db")

    def __init__(self, env: Environment, db_name: bytes):
        self.env = env
        self.db = env.open_db(db_name)

    def _make_key(self, key: str) -> bytes:
        return key.encode("utf-8")

    async def set(self, key: str, value: Any, ttl: float | None = None) -> None:
        self._set(key, value, ttl)

    def _set(self, key: str, value: Any, ttl: float | None = None) -> None:
        data = encode(value)
        expire = time.time() + ttl if ttl else 0.0
        payload = int(expire).to_bytes(8, "little") + data
        with self.env.begin(write=True, db=self.db) as txn:
            txn.put(self._make_key(key), payload)

    async def get(self, key: str, type_ref: Any = None) -> Any:
        return self._get(key, type_ref)

    def _get(self, key: str, type_ref: Any = None) -> Any:
        with self.env.begin(db=self.db) as txn:
            raw = txn.get(self._make_key(key))
        if raw is None:
            return None
        expire = int.from_bytes(raw[:8], "little")
        if expire != 0 and time.time() > expire:
            with self.env.begin(write=True, db=self.db) as txn:
                txn.delete(self._make_key(key))
            return None
        data = raw[8:]
        return decode(data, type=type_ref) if type_ref else decode(data)

    async def get_all(self, type_ref: Any = None) -> list[Any]:
        return self._get_all(type_ref)

    def _get_all(self, type_ref: Any = None) -> list[Any]:
        results = []
        now = time.time()
        with self.env.begin(db=self.db) as txn:
            cursor = txn.cursor()
            for _, raw in cursor:
                if len(raw) < 8:
                    continue
                expire = int.from_bytes(raw[:8], "little")
                if expire != 0 and now > expire:
                    continue
                data = raw[8:]
                try:
                    results.append(
                        decode(data, type=type_ref) if type_ref else decode(data)
                    )
                except Exception:
                    pass
        return results

    async def delete(self, key: str) -> None:
        self._delete(key)

    def _delete(self, key: str) -> None:
        with self.env.begin(write=True, db=self.db) as txn:
            txn.delete(self._make_key(key))

    async def clear(self) -> None:
        self._clear()

    def _clear(self) -> None:
        with self.env.begin(write=True, db=self.db) as txn:
            txn.drop(self.db, delete=False)


class db:
    __slots__ = ()
    cache = None
    history_store = None
    persistence = None
    _env = None

    @classmethod
    async def setup(cls):
        Path("data/lmdb").mkdir(parents=True, exist_ok=True)
        cls._env = lmdb_open(
            "data/lmdb/store.lmdb",
            map_size=104857600,
            subdir=True,
            sync=False,
            metasync=False,
            max_dbs=10,
        )
        cls.cache = _LMDBStore(cls._env, b"cache")
        cls.history_store = _LMDBStore(cls._env, b"history")
        cls.persistence = _LMDBStore(cls._env, b"persistence")
        logging.info("db: lmdb initialized")

    @classmethod
    async def close(cls):
        if cls._env:
            cls._env.sync()
            cls._env.close()

    @classmethod
    async def track_message(
        cls, msg_id: str, app_id: str, token: str, channel_id: int, user_id: int
    ):
        if not cls.history_store:
            return
        exp = time.time() + 900.0
        payload = {
            "id": msg_id,
            "app_id": app_id,
            "token": token,
            "channel_id": channel_id,
            "user_id": user_id,
            "expires": exp,
        }
        await cls.history_store.set(msg_id, payload, 900.0)

    @classmethod
    async def get_webhook_history(cls, channel_id: int, user_id: int) -> list[dict]:
        if not cls.history_store:
            return []
        now = time.time()
        return [
            m
            for m in await cls.history_store.get_all(dict)
            if m["channel_id"] == channel_id
            and m["user_id"] == user_id
            and m["expires"] > now
        ]

    @classmethod
    async def clear_webhook_history(cls, msg_ids: list[str]):
        if not cls.history_store:
            return
        for mid in msg_ids:
            await cls.history_store.delete(mid)

    @classmethod
    async def get(
        cls, user_id: int, type_ref: Any = dict, ttl: float | None = 60.0
    ) -> Any:
        if not cls.persistence:
            return type_ref() if callable(type_ref) else {}

        cache_key = f"u:{user_id}"
        if ttl is not None:
            cached = await cls.cache.get(cache_key, type_ref)
            if cached is not None:
                return cached

        data = await cls.persistence.get(str(user_id), type_ref)
        if data is None:
            return type_ref() if callable(type_ref) else {}

        if ttl is not None:
            await cls.cache.set(cache_key, data, ttl)
        return data

    @classmethod
    async def set(cls, user_id: int, data: Any):
        if not cls.persistence:
            return
        await cls.cache.set(f"u:{user_id}", data, 60.0)
        await cls.persistence.set(str(user_id), data, 86400.0 * 365)

    @classmethod
    async def delete(cls, user_id: int):
        if not cls.persistence:
            return
        await cls.cache.delete(f"u:{user_id}")
        await cls.persistence.delete(str(user_id))
