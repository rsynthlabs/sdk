"""Payload model and canonicalization. See SCHEMA.md."""

from __future__ import annotations

import enum
import json
from typing import Any

from eth_utils import keccak
from pydantic import BaseModel, Field


class Outcome(enum.Enum):
    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    FAIL = "FAIL"


class Metrics(BaseModel):
    rmse: float
    jerk: float
    end_variance: float


class Payload(BaseModel):
    version: str
    agent_id: int
    robot_id: str
    episode_id: str
    task: str
    started_at: str
    ended_at: str
    duration_seconds: float
    frames: int
    metrics: Metrics
    score: float = Field(ge=0, le=1)
    outcome: Outcome


def canonical_bytes(payload: Payload | dict[str, Any]) -> bytes:
    """Canonical byte sequence for hashing/signing. See SCHEMA.md §2.

    Sorted keys at every depth, no whitespace between tokens, UTF-8 encoded,
    no trailing newline. Accepts a Payload model or a JSON-serializable dict.
    """
    data = payload.model_dump(mode="json") if isinstance(payload, BaseModel) else payload
    return json.dumps(
        data,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def payload_hash(payload: Payload | dict[str, Any]) -> bytes:
    """keccak256 of canonical_bytes(payload). 32 bytes. See SCHEMA.md §2."""
    return keccak(canonical_bytes(payload))
