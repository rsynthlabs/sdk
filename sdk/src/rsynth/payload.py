"""Payload model and canonicalization. See SCHEMA.md."""

import enum

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


def canonical_bytes(payload: Payload) -> bytes:
    # TODO: implement per SCHEMA.md §2
    raise NotImplementedError


def payload_hash(payload: Payload) -> bytes:
    # TODO: implement per SCHEMA.md §2
    raise NotImplementedError
