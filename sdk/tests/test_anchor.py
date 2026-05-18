"""Tests for on-chain anchor submission. See SCHEMA.md §4."""

import json
import re
from pathlib import Path

import pytest
from web3 import EthereumTesterProvider, Web3

from rsynth.anchor import AnchorRevertedError, _anchor
from rsynth.payload import Payload, payload_hash
from rsynth.sign import sign

from .test_payload import SCHEMA_EXAMPLE
from .test_sign import HARDHAT_ADDR_0, HARDHAT_KEY_0


HARDHAT_KEY_1 = "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d"
HARDHAT_ADDR_1 = "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"

ARTIFACT = (
    Path(__file__).parents[2] / "contracts/out/ExecutionLog.sol/ExecutionLog.json"
)

TX_HASH_RE = re.compile(r"0x[0-9a-f]{64}")


@pytest.fixture(scope="session")
def deployed():
    if not ARTIFACT.exists():
        pytest.skip(f"Run `forge build` in contracts/ first (missing {ARTIFACT})")
    art = json.loads(ARTIFACT.read_text())
    w3 = Web3(EthereumTesterProvider())
    deployer = w3.eth.accounts[0]
    Contract = w3.eth.contract(abi=art["abi"], bytecode=art["bytecode"]["object"])
    deploy_tx = Contract.constructor().transact({"from": deployer})
    receipt = w3.eth.wait_for_transaction_receipt(deploy_tx)
    for addr in (HARDHAT_ADDR_0, HARDHAT_ADDR_1):
        w3.eth.send_transaction({"from": deployer, "to": addr, "value": 10**18})
    return w3, receipt.contractAddress, art["abi"]


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
