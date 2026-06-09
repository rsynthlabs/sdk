"""Tests for on-chain anchor verification. See SCHEMA.md §4."""

import pytest

from rsynth.anchor import _anchor
from rsynth.fetch import (
    AnchorMismatchError,
    AnchorNotFoundError,
    LineageError,
    _verify,
    _verify_with_lineage,
)
from rsynth.payload import Payload, payload_hash
from rsynth.sign import sign

from .test_payload import SCHEMA_EXAMPLE
from .test_policy import PARENT, POLICY, V02_EXAMPLE
from .test_sign import HARDHAT_ADDR_0, HARDHAT_KEY_0


def _payload() -> Payload:
    return Payload.model_validate(SCHEMA_EXAMPLE)


def test_verify_returns_signer_and_hash(deployed):
    w3, addr, _abi = deployed
    p = _payload()
    sig = sign(p, HARDHAT_KEY_0)
    tx_hash = _anchor(w3, p, sig, addr, HARDHAT_KEY_0)
    signer, on_chain_hash = _verify(w3, tx_hash, addr)
    assert signer == HARDHAT_ADDR_0
    assert on_chain_hash == payload_hash(p)
    assert type(on_chain_hash) is bytes


def test_verify_roundtrip_e2e(deployed):
    """The v0.1 ship criterion: sign → anchor → verify → compare hashes."""
    w3, addr, _abi = deployed
    p = _payload()
    sig = sign(p, HARDHAT_KEY_0)
    tx_hash = _anchor(w3, p, sig, addr, HARDHAT_KEY_0)
    signer, on_chain_hash = _verify(w3, tx_hash, addr)
    assert signer == HARDHAT_ADDR_0
    assert on_chain_hash == payload_hash(p)


def test_verify_raises_on_nonexistent_tx(deployed):
    w3, addr, _abi = deployed
    fake_tx = "0x" + "00" * 32
    with pytest.raises(AnchorNotFoundError) as exc:
        _verify(w3, fake_tx, addr)
    assert exc.value.tx_hash == fake_tx


def test_verify_raises_on_wrong_contract(deployed):
    w3, addr, _abi = deployed
    p = _payload()
    sig = sign(p, HARDHAT_KEY_0)
    tx_hash = _anchor(w3, p, sig, addr, HARDHAT_KEY_0)
    wrong = "0x0000000000000000000000000000000000000001"
    with pytest.raises(AnchorNotFoundError):
        _verify(w3, tx_hash, wrong)


# --- v0.2 verify_anchor_with_lineage (anchor + self-attested lineage) ---


def test_verify_with_lineage_happy(deployed):
    w3, addr, _abi = deployed
    p = Payload.model_validate(V02_EXAMPLE)
    sig = sign(p, HARDHAT_KEY_0)
    tx_hash = _anchor(w3, p, sig, addr, HARDHAT_KEY_0)
    signer, on_chain_hash, chain = _verify_with_lineage(w3, tx_hash, p, addr)
    assert signer == HARDHAT_ADDR_0
    assert on_chain_hash == payload_hash(p)
    assert chain == [PARENT]


def test_verify_with_lineage_v01_backward_compat(deployed):
    # A no-policy v0.1 payload verifies identically to plain _verify, with [].
    w3, addr, _abi = deployed
    p = _payload()
    sig = sign(p, HARDHAT_KEY_0)
    tx_hash = _anchor(w3, p, sig, addr, HARDHAT_KEY_0)
    signer, on_chain_hash, chain = _verify_with_lineage(w3, tx_hash, p, addr)
    assert (signer, on_chain_hash) == _verify(w3, tx_hash, addr)
    assert chain == []


def test_verify_with_lineage_anchor_mismatch(deployed):
    w3, addr, _abi = deployed
    p = _payload()
    sig = sign(p, HARDHAT_KEY_0)
    tx_hash = _anchor(w3, p, sig, addr, HARDHAT_KEY_0)
    other = Payload.model_validate({**SCHEMA_EXAMPLE, "score": 0.5})
    with pytest.raises(AnchorMismatchError) as exc:
        _verify_with_lineage(w3, tx_hash, other, addr)
    assert exc.value.tx_hash == tx_hash


def test_verify_with_lineage_anchor_not_found(deployed):
    w3, addr, _abi = deployed
    p = Payload.model_validate(V02_EXAMPLE)
    fake_tx = "0x" + "00" * 32
    with pytest.raises(AnchorNotFoundError):
        _verify_with_lineage(w3, fake_tx, p, addr)


def test_verify_with_lineage_broken_lineage_after_valid_anchor(deployed):
    # The anchor is valid (we anchor this exact payload); the lineage check still fires.
    w3, addr, _abi = deployed
    broken = Payload.model_validate(
        {**V02_EXAMPLE, "policy": {**POLICY, "lineage_chain": ["0x" + "99" * 32]}}
    )
    sig = sign(broken, HARDHAT_KEY_0)
    tx_hash = _anchor(w3, broken, sig, addr, HARDHAT_KEY_0)
    with pytest.raises(LineageError) as exc:
        _verify_with_lineage(w3, tx_hash, broken, addr)
    assert exc.value.reason == "broken_parent"
