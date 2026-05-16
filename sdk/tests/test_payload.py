"""Tests for payload canonicalization. See SCHEMA.md §2."""

import json

from rsynth.payload import canonical_bytes, payload_hash


SCHEMA_EXAMPLE = {
    "version": "0.1.0",
    "agent_id": 10311,
    "robot_id": "roarm-m3-01",
    "episode_id": "ep_2026-05-14_18-22-31_004a",
    "task": "pick and place the cube",
    "started_at": "2026-05-14T18:22:31Z",
    "ended_at": "2026-05-14T18:22:53Z",
    "duration_seconds": 22.6,
    "frames": 678,
    "metrics": {
        "rmse": 4.583,
        "jerk": 2434753.0,
        "end_variance": 0.0,
    },
    "score": 0.90,
    "outcome": "SUCCESS",
}

SCHEMA_EXAMPLE_HASH = "26444c4ba73c1f692533ddcf1827e56f5cefe27cbbd169c87ff11c443e99aa8d"


def test_top_level_order_independence():
    a = {"version": "0.1.0", "agent_id": 1, "score": 0.5}
    b = {"score": 0.5, "agent_id": 1, "version": "0.1.0"}
    assert canonical_bytes(a) == canonical_bytes(b)


def test_nested_order_independence():
    a = {"metrics": {"rmse": 1.0, "jerk": 2.0, "end_variance": 3.0}, "agent_id": 1}
    b = {"agent_id": 1, "metrics": {"end_variance": 3.0, "jerk": 2.0, "rmse": 1.0}}
    assert canonical_bytes(a) == canonical_bytes(b)


def test_exact_no_whitespace():
    assert canonical_bytes({"b": 2, "a": 1}) == b'{"a":1,"b":2}'


def test_no_trailing_newline():
    assert not canonical_bytes({"a": 1}).endswith(b"\n")
    assert not canonical_bytes(SCHEMA_EXAMPLE).endswith(b"\n")


def test_utf8_preserved():
    payload = {"name": "机器人", "place": "résumé"}
    out = canonical_bytes(payload)
    assert "机器人".encode("utf-8") in out
    assert "résumé".encode("utf-8") in out
    assert json.loads(out.decode("utf-8")) == payload


def test_hash_is_32_bytes():
    h = payload_hash({"a": 1})
    assert isinstance(h, bytes)
    assert len(h) == 32


def test_hash_order_independent():
    a = {"version": "0.1.0", "agent_id": 1, "score": 0.5}
    b = {"score": 0.5, "agent_id": 1, "version": "0.1.0"}
    assert payload_hash(a) == payload_hash(b)


def test_schema_example_regression():
    assert payload_hash(SCHEMA_EXAMPLE).hex() == SCHEMA_EXAMPLE_HASH
