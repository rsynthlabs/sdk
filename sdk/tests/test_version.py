"""Tests for v0.2 version/policy dispatch. See docs/v0.2/SCHEMA-DIFF.md §1."""

import pytest

from rsynth.fetch import VersionError, validate_version
from rsynth.payload import Payload, payload_hash

from .test_payload import SCHEMA_EXAMPLE, SCHEMA_EXAMPLE_HASH
from .test_policy import POLICY, V02_EXAMPLE


# --- happy paths: return the validated version, never raise ---


def test_validate_version_v01_happy():
    assert validate_version(Payload.model_validate(SCHEMA_EXAMPLE)) == "0.1.0"


def test_validate_version_v02_happy():
    assert validate_version(Payload.model_validate(V02_EXAMPLE)) == "0.2.0"


# --- version/policy mismatches ---


def test_validate_version_v01_with_policy_forbidden():
    p = Payload.model_validate({**SCHEMA_EXAMPLE, "policy": POLICY})
    with pytest.raises(VersionError) as exc:
        validate_version(p)
    assert exc.value.reason == "policy_forbidden"


def test_validate_version_v02_without_policy_required():
    p = Payload.model_validate({**V02_EXAMPLE, "policy": None})
    with pytest.raises(VersionError) as exc:
        validate_version(p)
    assert exc.value.reason == "policy_required"


def test_validate_version_unknown_rejected():
    p = Payload.model_validate({**SCHEMA_EXAMPLE, "version": "0.3.0"})
    with pytest.raises(VersionError) as exc:
        validate_version(p)
    assert exc.value.reason == "unknown_version"


def test_validate_version_unknown_empty():
    p = Payload.model_validate({**SCHEMA_EXAMPLE, "version": ""})
    with pytest.raises(VersionError) as exc:
        validate_version(p)
    assert exc.value.reason == "unknown_version"


def test_validate_version_unknown_wins_over_policy():
    # version is the source of truth: an unknown version is rejected regardless
    # of whether a policy block is present (dispatch on the string, not the key).
    p = Payload.model_validate({**V02_EXAMPLE, "version": "9.9.9"})
    with pytest.raises(VersionError) as exc:
        validate_version(p)
    assert exc.value.reason == "unknown_version"


# --- backward compat: v0.1 passes the validator AND the locked hash is unmoved ---


def test_v01_passes_validator_and_hash_unchanged():
    p = Payload.model_validate(SCHEMA_EXAMPLE)
    assert validate_version(p) == "0.1.0"
    assert payload_hash(p).hex() == SCHEMA_EXAMPLE_HASH
