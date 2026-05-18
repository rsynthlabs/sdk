"""Tests for on-chain anchor submission. See SCHEMA.md §4."""

import re

import pytest

from rsynth.anchor import AnchorRevertedError, _anchor
from rsynth.payload import Payload, payload_hash
from rsynth.sign import sign

from .conftest import HARDHAT_ADDR_1, HARDHAT_KEY_1
from .test_payload import SCHEMA_EXAMPLE
from .test_sign import HARDHAT_ADDR_0, HARDHAT_KEY_0


TX_HASH_RE = re.compile(r"0x[0-9a-f]{64}")


def _payload() -> Payload:
    return Payload.model_validate(SCHEMA_EXAMPLE)


def test_anchor_returns_tx_hash_format(deployed):
    w3, addr, _abi = deployed
    p = _payload()
    sig = sign(p, HARDHAT_KEY_0)
    tx_hash = _anchor(w3, p, sig, addr, HARDHAT_KEY_0)
    assert TX_HASH_RE.fullmatch(tx_hash)


def test_anchor_emits_execution_recorded_event(deployed):
    w3, addr, abi = deployed
    p = _payload()
    sig = sign(p, HARDHAT_KEY_0)
    tx_hash = _anchor(w3, p, sig, addr, HARDHAT_KEY_0)
    receipt = w3.eth.get_transaction_receipt(tx_hash)
    contract = w3.eth.contract(address=addr, abi=abi)
    events = contract.events.ExecutionRecorded().process_receipt(receipt)
    assert len(events) == 1
    assert events[0]["args"]["signer"] == HARDHAT_ADDR_0
    assert events[0]["args"]["payloadHash"] == payload_hash(p)


def test_anchor_raises_on_invalid_signature(deployed):
    w3, addr, _abi = deployed
    p = _payload()
    bad_sig = b"\x00" * 65
    with pytest.raises(AnchorRevertedError) as exc:
        _anchor(w3, p, bad_sig, addr, HARDHAT_KEY_0)
    assert TX_HASH_RE.fullmatch(exc.value.tx_hash)


def test_anchor_sender_independent_of_signer(deployed):
    w3, addr, abi = deployed
    p = _payload()
    sig = sign(p, HARDHAT_KEY_0)
    tx_hash = _anchor(w3, p, sig, addr, HARDHAT_KEY_1)
    receipt = w3.eth.get_transaction_receipt(tx_hash)
    tx = w3.eth.get_transaction(tx_hash)
    contract = w3.eth.contract(address=addr, abi=abi)
    events = contract.events.ExecutionRecorded().process_receipt(receipt)
    assert events[0]["args"]["signer"] == HARDHAT_ADDR_0
    assert tx["from"] == HARDHAT_ADDR_1
