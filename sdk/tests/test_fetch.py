"""Tests for on-chain anchor verification. See SCHEMA.md §4."""

import pytest

from rsynth.anchor import _anchor
from rsynth.fetch import AnchorNotFoundError, _verify
from rsynth.payload import Payload, payload_hash
from rsynth.sign import sign

from .test_payload import SCHEMA_EXAMPLE
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
