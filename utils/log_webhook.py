from __future__ import annotations
import logging
import random
from aiohttp import ClientSession


def _rand_color() -> int:
    return random.randint(0, 0xFFFFFF)


async def send(url: str, payload: dict | list) -> None:
    if not url:
        return
    if isinstance(payload, list):
        payload = {"flags": 32768, "components": payload}
    elif "components" in payload and "flags" not in payload:
        payload["flags"] = 32768
    has_components = "components" in payload
    url = f"{url}?with_components=true" if has_components else url
    payload.setdefault("allowed_mentions", {"parse": []})
    try:
        async with ClientSession() as s:
            async with s.post(url, json=payload, timeout=10) as r:
                if r.status >= 300:
                    body = await r.text()
                    logging.warning(f"webhook {r.status}: {body[:200]}")
    except Exception as e:
        logging.warning(f"webhook send error: {e}")
