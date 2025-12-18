from __future__ import annotations

import app.services.redis_client as redis_client
from app.services.idempotency_service import try_acquire_idempotency_key
from tests.util_fake_redis import FakeRedis


def test_idempotency_key_acquire_is_strict(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(redis_client, "_redis_str", fake)

    res1 = try_acquire_idempotency_key(idempotency_key="k1", event_id="e1")
    assert res1.acquired is True

    res2 = try_acquire_idempotency_key(idempotency_key="k1", event_id="e2")
    assert res2.acquired is False
    assert res2.existing_event_id == "e1"



