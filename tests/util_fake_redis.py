from __future__ import annotations

from typing import Any, Optional


class FakeRedis:
    def __init__(self) -> None:
        self._kv: dict[str, str] = {}
        self._hash: dict[str, dict[str, str]] = {}

    def set(self, key: str, value: str, nx: bool = False) -> bool:
        if nx and key in self._kv:
            return False
        self._kv[key] = str(value)
        return True

    def get(self, key: str) -> Optional[str]:
        return self._kv.get(key)

    def delete(self, key: str) -> int:
        n = 0
        if key in self._kv:
            del self._kv[key]
            n += 1
        if key in self._hash:
            del self._hash[key]
            n += 1
        return n

    def exists(self, key: str) -> int:
        return 1 if (key in self._kv or key in self._hash) else 0

    def hset(self, key: str, mapping: dict[str, Any]) -> None:
        h = self._hash.setdefault(key, {})
        for k, v in mapping.items():
            h[str(k)] = str(v)

    def hgetall(self, key: str) -> dict[str, str]:
        return dict(self._hash.get(key, {}))

    def hincrby(self, key: str, field: str, amount: int) -> int:
        h = self._hash.setdefault(key, {})
        cur = int(h.get(field, "0") or "0")
        cur += int(amount)
        h[field] = str(cur)
        return cur





