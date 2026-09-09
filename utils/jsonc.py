from __future__ import annotations

import re
from pathlib import Path

from msgspec.json import decode as _decode

_trailing_comma_re = re.compile(r",(\s*[}\]])")


def load[T](path: str | Path, type_ref: type[T] = dict) -> T:
    raw = Path(path).read_text(encoding="utf-8")
    lines = []
    for line in raw.splitlines():
        stripped = line.strip()
        if stripped.startswith("//"):
            continue
        lines.append(line)
    cleaned = "\n".join(lines)
    cleaned = _trailing_comma_re.sub(r"\1", cleaned)
    return _decode(cleaned.encode(), type=type_ref)
