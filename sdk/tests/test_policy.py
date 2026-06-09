"""Tests for the v0.2 additive policy lineage field. See docs/v0.2/POLICY-LINEAGE.md."""

import pytest
from pydantic import ValidationError

from rsynth.fetch import LineageError, _validate_lineage
from rsynth.payload import Payload, PolicyMeta, canonical_bytes, payload_hash

from .test_payload import SCHEMA_EXAMPLE, SCHEMA_EXAMPLE_HASH


ID = "0x" + "11" * 32
PARENT = "0x" + "22" * 32

POLICY = {
    "id": ID,
    "parent_id": PARENT,
    "source_uri": "hf://lerobot/smolvla-base@a1b2c3d",
    "lineage_chain": [PARENT],
}

V02_EXAMPLE = {**SCHEMA_EXAMPLE, "version": "0.2.0", "policy": POLICY}


# --- backward-compat guards: v0.1 payloads hash/serialize byte-identically ---


def test_v01_model_hash_unchanged():
    # The optional policy field + the canonical_bytes guard must not move the
    # locked v0.1 hash on the model path (policy=None must be dropped, not
    # serialized as "policy":null).
    assert payload_hash(Payload.model_validate(SCHEMA_EXAMPLE)).hex() == SCHEMA_EXAMPLE_HASH


def test_v01_model_canonical_equals_dict():
    # No "policy":null may leak into the model-path canonical bytes.
    model = Payload.model_validate(SCHEMA_EXAMPLE)
    assert canonical_bytes(model) == canonical_bytes(SCHEMA_EXAMPLE)


def test_absent_policy_omitted():
    assert b'"policy"' not in canonical_bytes(Payload.model_validate(SCHEMA_EXAMPLE))


# --- v0.2 policy block ---


def test_policy_roundtrips():
    payload = Payload.model_validate(V02_EXAMPLE)
    dumped = payload.model_dump(mode="json")
    assert dumped["policy"] == POLICY
    assert Payload.model_validate(dumped) == payload


def test_policy_in_hash():
    a = Payload.model_validate(V02_EXAMPLE)
    b = Payload.model_validate({**V02_EXAMPLE, "policy": {**POLICY, "id": "0x" + "33" * 32}})
    assert b'"policy"' in canonical_bytes(a)
    assert payload_hash(a) != payload_hash(b)


def test_root_parent_id_encoded_as_null():
    # M1: a root policy keeps parent_id in the preimage, encoded as JSON null.
    payload = Payload.model_validate({**V02_EXAMPLE, "policy": {**POLICY, "parent_id": None}})
    assert b'"parent_id":null' in canonical_bytes(payload)


def test_lineage_chain_max_16():
    chain = ["0x" + f"{i:064x}" for i in range(16)]
    PolicyMeta(id=ID, source_uri=POLICY["source_uri"], lineage_chain=chain)
    with pytest.raises(ValidationError):
        PolicyMeta(id=ID, source_uri=POLICY["source_uri"], lineage_chain=chain + [PARENT])


# --- v0.2 self-attested lineage validation (fetch._validate_lineage) ---


def test_validate_lineage_happy():
    assert _validate_lineage(Payload.model_validate(V02_EXAMPLE)) == [PARENT]


def test_validate_lineage_no_policy_empty():
    # v0.1 / no-policy payload: empty chain, never raises.
    assert _validate_lineage(Payload.model_validate(SCHEMA_EXAMPLE)) == []


def test_validate_lineage_root_empty_chain():
    none = Payload.model_validate(
        {**V02_EXAMPLE, "policy": {**POLICY, "parent_id": None, "lineage_chain": None}}
    )
    empty = Payload.model_validate(
        {**V02_EXAMPLE, "policy": {**POLICY, "parent_id": None, "lineage_chain": []}}
    )
    assert _validate_lineage(none) == []
    assert _validate_lineage(empty) == []


def test_validate_lineage_broken_parent():
    p = Payload.model_validate(
        {**V02_EXAMPLE, "policy": {**POLICY, "lineage_chain": ["0x" + "99" * 32]}}
    )
    with pytest.raises(LineageError) as exc:
        _validate_lineage(p)
    assert exc.value.reason == "broken_parent"


def test_validate_lineage_chain_without_parent():
    p = Payload.model_validate(
        {**V02_EXAMPLE, "policy": {**POLICY, "parent_id": None, "lineage_chain": [PARENT]}}
    )
    with pytest.raises(LineageError) as exc:
        _validate_lineage(p)
    assert exc.value.reason == "broken_parent"


def test_validate_lineage_depth_overflow():
    # Bypass the Pydantic max_length=16 cap to exercise the verify-side re-check.
    p = Payload.model_validate(V02_EXAMPLE)
    p.policy.lineage_chain = ["0x" + f"{i:064x}" for i in range(16)] + [PARENT]
    with pytest.raises(LineageError) as exc:
        _validate_lineage(p)
    assert exc.value.reason == "depth_overflow"


def test_validate_lineage_malformed_source_uri():
    p = Payload.model_validate({**V02_EXAMPLE, "policy": {**POLICY, "source_uri": ""}})
    with pytest.raises(LineageError) as exc:
        _validate_lineage(p)
    assert exc.value.reason == "malformed"


def test_validate_lineage_malformed_empty_id():
    p = Payload.model_validate({**V02_EXAMPLE, "policy": {**POLICY, "id": ""}})
    with pytest.raises(LineageError) as exc:
        _validate_lineage(p)
    assert exc.value.reason == "malformed"


def test_validate_lineage_malformed_empty_link():
    p = Payload.model_validate(
        {**V02_EXAMPLE, "policy": {**POLICY, "lineage_chain": ["", PARENT]}}
    )
    with pytest.raises(LineageError) as exc:
        _validate_lineage(p)
    assert exc.value.reason == "malformed"
