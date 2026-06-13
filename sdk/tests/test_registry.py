"""Tests for the on-chain policy registry. See docs/v0.2/POLICY-LINEAGE.md."""

import pytest
from web3 import Web3

from rsynth.anchor import _anchor
from rsynth.fetch import LineageError, _verify_with_lineage
from rsynth.payload import Payload
from rsynth.registry import (
    MAX_CHAIN_DEPTH,
    RegisterRevertedError,
    _fetch_policy_chain,
    _register_policy,
)
from rsynth.sign import sign

from .test_payload import SCHEMA_EXAMPLE
from .test_sign import HARDHAT_ADDR_0, HARDHAT_KEY_0

URI = "hf://lerobot/smolvla-base@a1b2c3d"


def _pid(tag: str) -> str:
    # The registry fixture is session-scoped and append-only, so every test
    # derives its own policy ids from a unique tag to stay isolated.
    return "0x" + bytes(Web3.keccak(text=tag)).hex()


def _v02(policy_id: str, parent_id: str | None, chain: list[str] | None) -> Payload:
    return Payload.model_validate(
        {
            **SCHEMA_EXAMPLE,
            "version": "0.2.0",
            "policy": {
                "id": policy_id,
                "parent_id": parent_id,
                "source_uri": URI,
                "lineage_chain": chain,
            },
        }
    )


# --- register_policy ---


def test_register_policy_returns_tx_hash(deployed_registry):
    w3, addr, _abi = deployed_registry
    tx_hash = _register_policy(w3, _pid("reg-hash"), None, URI, addr, HARDHAT_KEY_0)
    assert tx_hash.startswith("0x") and len(tx_hash) == 66


def test_register_stores_record(deployed_registry):
    w3, addr, abi = deployed_registry
    pid, parent = _pid("reg-store"), _pid("reg-store-parent")
    _register_policy(w3, pid, parent, URI, addr, HARDHAT_KEY_0)
    contract = w3.eth.contract(address=addr, abi=abi)
    parent_id, uri_hash, registrant, block_num = contract.functions.policies(
        bytes.fromhex(pid[2:])
    ).call()
    assert bytes(parent_id) == bytes.fromhex(parent[2:])
    assert bytes(uri_hash) == bytes(Web3.keccak(text=URI))
    assert registrant == HARDHAT_ADDR_0
    assert block_num > 0


def test_register_duplicate_raises(deployed_registry):
    w3, addr, _abi = deployed_registry
    pid = _pid("reg-dup")
    _register_policy(w3, pid, None, URI, addr, HARDHAT_KEY_0)
    with pytest.raises(RegisterRevertedError):
        _register_policy(w3, pid, None, URI, addr, HARDHAT_KEY_0)


def test_register_unregistered_parent_allowed(deployed_registry):
    # Off-chain parents are legal: the contract has no parent existence check.
    w3, addr, _abi = deployed_registry
    tx_hash = _register_policy(
        w3, _pid("reg-orphan"), _pid("reg-orphan-never-registered"), URI, addr, HARDHAT_KEY_0
    )
    assert tx_hash.startswith("0x")


def test_register_rejects_malformed_id(deployed_registry):
    w3, addr, _abi = deployed_registry
    with pytest.raises(ValueError):
        _register_policy(w3, "0x1234", None, URI, addr, HARDHAT_KEY_0)
    with pytest.raises(ValueError):
        _register_policy(w3, "11" * 32, None, URI, addr, HARDHAT_KEY_0)


# --- fetch_policy_chain ---


def test_fetch_chain_unregistered_head(deployed_registry):
    w3, addr, _abi = deployed_registry
    result = _fetch_policy_chain(w3, _pid("walk-nothing"), addr)
    assert result.registered is False
    assert result.chain == []
    assert result.terminal == "unregistered"


def test_fetch_chain_root(deployed_registry):
    w3, addr, _abi = deployed_registry
    pid = _pid("walk-root")
    _register_policy(w3, pid, None, URI, addr, HARDHAT_KEY_0)
    result = _fetch_policy_chain(w3, pid, addr)
    assert result.registered is True
    assert result.chain == []
    assert result.terminal == "root"


def test_fetch_chain_multi_hop(deployed_registry):
    w3, addr, _abi = deployed_registry
    a, b, c = _pid("walk-a"), _pid("walk-b"), _pid("walk-c")
    _register_policy(w3, a, None, URI, addr, HARDHAT_KEY_0)
    _register_policy(w3, b, a, URI, addr, HARDHAT_KEY_0)
    _register_policy(w3, c, b, URI, addr, HARDHAT_KEY_0)
    result = _fetch_policy_chain(w3, c, addr)
    assert result.chain == [a, b]  # oldest to newest, chain[-1] = direct parent
    assert result.terminal == "root"


def test_fetch_chain_offchain_parent(deployed_registry):
    # The walk stops at an unregistered parent but includes it as the oldest
    # hop — it is a claimed ancestor, just not resolvable on-chain.
    w3, addr, _abi = deployed_registry
    pid, ghost = _pid("walk-stub"), _pid("walk-stub-ghost")
    _register_policy(w3, pid, ghost, URI, addr, HARDHAT_KEY_0)
    result = _fetch_policy_chain(w3, pid, addr)
    assert result.chain == [ghost]
    assert result.terminal == "offchain_parent"


def test_fetch_chain_depth_cap_on_cycle(deployed_registry):
    # A cycle on-chain just spins until the cap; no cycle detection needed.
    w3, addr, _abi = deployed_registry
    a, b = _pid("walk-cycle-a"), _pid("walk-cycle-b")
    _register_policy(w3, a, b, URI, addr, HARDHAT_KEY_0)
    _register_policy(w3, b, a, URI, addr, HARDHAT_KEY_0)
    result = _fetch_policy_chain(w3, a, addr)
    assert len(result.chain) == MAX_CHAIN_DEPTH
    assert result.terminal == "depth_capped"


# --- verify_anchor_with_lineage registry cross-check ---


def _anchor_payload(w3, p, log_addr):
    sig = sign(p, HARDHAT_KEY_0)
    return _anchor(w3, p, sig, log_addr, HARDHAT_KEY_0)


def test_crosscheck_fully_registered_chain_ok(deployed, deployed_registry):
    w3, log_addr, _ = deployed
    _, reg_addr, _ = deployed_registry
    parent, pid = _pid("cc-ok-parent"), _pid("cc-ok")
    _register_policy(w3, parent, None, URI, reg_addr, HARDHAT_KEY_0)
    _register_policy(w3, pid, parent, URI, reg_addr, HARDHAT_KEY_0)
    p = _v02(pid, parent, [parent])
    tx_hash = _anchor_payload(w3, p, log_addr)
    signer, _, chain = _verify_with_lineage(w3, tx_hash, p, log_addr, reg_addr)
    assert signer == HARDHAT_ADDR_0
    assert chain == [parent]


def test_crosscheck_unregistered_policy_raises(deployed, deployed_registry):
    w3, log_addr, _ = deployed
    _, reg_addr, _ = deployed_registry
    p = _v02(_pid("cc-unreg"), None, None)
    tx_hash = _anchor_payload(w3, p, log_addr)
    with pytest.raises(LineageError) as exc:
        _verify_with_lineage(w3, tx_hash, p, log_addr, reg_addr)
    assert exc.value.reason == "unregistered"


def test_crosscheck_parent_mismatch_raises(deployed, deployed_registry):
    # Registered with one parent on-chain, self-attesting a different one.
    w3, log_addr, _ = deployed
    _, reg_addr, _ = deployed_registry
    pid = _pid("cc-twoface")
    onchain_parent, claimed_parent = _pid("cc-twoface-real"), _pid("cc-twoface-claimed")
    _register_policy(w3, pid, onchain_parent, URI, reg_addr, HARDHAT_KEY_0)
    p = _v02(pid, claimed_parent, [claimed_parent])
    tx_hash = _anchor_payload(w3, p, log_addr)
    with pytest.raises(LineageError) as exc:
        _verify_with_lineage(w3, tx_hash, p, log_addr, reg_addr)
    assert exc.value.reason == "chain_mismatch"


def test_crosscheck_offchain_ancestors_allowed(deployed, deployed_registry):
    # Walk stops at an unregistered parent; self-attested entries older than
    # that point are accepted as off-chain ancestors (suffix rule).
    w3, log_addr, _ = deployed
    _, reg_addr, _ = deployed_registry
    pid, parent, grandparent = _pid("cc-off"), _pid("cc-off-parent"), _pid("cc-off-grand")
    _register_policy(w3, pid, parent, URI, reg_addr, HARDHAT_KEY_0)
    p = _v02(pid, parent, [grandparent, parent])
    tx_hash = _anchor_payload(w3, p, log_addr)
    signer, _, chain = _verify_with_lineage(w3, tx_hash, p, log_addr, reg_addr)
    assert signer == HARDHAT_ADDR_0
    assert chain == [grandparent, parent]


def test_crosscheck_onchain_root_contradicts_self_chain(deployed, deployed_registry):
    # parentId == 0 on-chain is a positive "no parent" assertion: older
    # self-attested ancestors contradict the record rather than extend it.
    w3, log_addr, _ = deployed
    _, reg_addr, _ = deployed_registry
    pid, claimed_parent = _pid("cc-root"), _pid("cc-root-claimed")
    _register_policy(w3, pid, None, URI, reg_addr, HARDHAT_KEY_0)
    p = _v02(pid, claimed_parent, [claimed_parent])
    tx_hash = _anchor_payload(w3, p, log_addr)
    with pytest.raises(LineageError) as exc:
        _verify_with_lineage(w3, tx_hash, p, log_addr, reg_addr)
    assert exc.value.reason == "chain_mismatch"


def test_crosscheck_empty_self_chain_with_onchain_parent_raises(deployed, deployed_registry):
    # Under-claiming registered ancestry contradicts the on-chain record.
    w3, log_addr, _ = deployed
    _, reg_addr, _ = deployed_registry
    pid, onchain_parent = _pid("cc-under"), _pid("cc-under-parent")
    _register_policy(w3, pid, onchain_parent, URI, reg_addr, HARDHAT_KEY_0)
    p = _v02(pid, None, None)
    tx_hash = _anchor_payload(w3, p, log_addr)
    with pytest.raises(LineageError) as exc:
        _verify_with_lineage(w3, tx_hash, p, log_addr, reg_addr)
    assert exc.value.reason == "chain_mismatch"


def test_no_registry_addr_skips_crosscheck(deployed, deployed_registry):
    # Without registry_addr the behavior is identical to increments 1-5,
    # even for a policy the registry has never seen.
    w3, log_addr, _ = deployed
    p = _v02(_pid("cc-skip"), None, None)
    tx_hash = _anchor_payload(w3, p, log_addr)
    signer, _, chain = _verify_with_lineage(w3, tx_hash, p, log_addr)
    assert signer == HARDHAT_ADDR_0
    assert chain == []


def test_crosscheck_v01_payload_noop(deployed, deployed_registry):
    # A v0.1 payload never touches the registry even when registry_addr is given.
    w3, log_addr, _ = deployed
    _, reg_addr, _ = deployed_registry
    p = Payload.model_validate(SCHEMA_EXAMPLE)
    tx_hash = _anchor_payload(w3, p, log_addr)
    signer, _, chain = _verify_with_lineage(w3, tx_hash, p, log_addr, reg_addr)
    assert signer == HARDHAT_ADDR_0
    assert chain == []
