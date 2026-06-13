"""On-chain policy lineage registry. See docs/v0.2/POLICY-LINEAGE.md."""

import json
from dataclasses import dataclass
from importlib.resources import files

from eth_account import Account
from web3 import Web3

from .anchor import _is_revert

_ABI = json.loads(files("rsynth.abi").joinpath("PolicyRegistry.json").read_text())

_ZERO_BYTES32 = b"\x00" * 32
_ZERO_ADDR = "0x0000000000000000000000000000000000000000"

# Matches PolicyMeta.lineage_chain max_length; also bounds on-chain cycles.
MAX_CHAIN_DEPTH = 16


class RegisterRevertedError(Exception):
    """Raised when PolicyRegistry.register() tx reverts on-chain."""

    def __init__(self, tx_hash: str, message: str = ""):
        self.tx_hash = tx_hash
        super().__init__(f"Register reverted (tx={tx_hash}): {message}")


@dataclass(frozen=True)
class PolicyChain:
    """Result of an on-chain lineage walk.

    chain: ancestor policy ids, oldest to newest (same orientation as
    PolicyMeta.lineage_chain — chain[-1] is the direct parent).
    registered: whether the head policy_id has an on-chain record.
    terminal: why the walk stopped — "unregistered" (head has no record),
    "root" (parentId == 0), "offchain_parent" (a parent is pointed to but
    never registered; it is included as the oldest hop), or "depth_capped"
    (walk hit MAX_CHAIN_DEPTH).
    """

    chain: list[str]
    registered: bool
    terminal: str


def _to_bytes32(hexstr: str) -> bytes:
    if not isinstance(hexstr, str) or not hexstr.startswith("0x"):
        raise ValueError(f"policy id must be a 0x-prefixed hex string, got {hexstr!r}")
    raw = bytes.fromhex(hexstr[2:])
    if len(raw) != 32:
        raise ValueError(f"policy id must be 32 bytes, got {len(raw)}")
    return raw


def _to_hex(b: bytes) -> str:
    return f"0x{b.hex()}"


def register_policy(
    policy_id: str,
    parent_id: str | None,
    source_uri: str,
    rpc_url: str,
    registry_addr: str,
    sender_key: str,
) -> str:
    """Submit PolicyRegistry.register(policyId, parentId, sourceUriHash) tx.

    parent_id None means root (stored as bytes32(0)). sourceUriHash is
    keccak256(source_uri), computed here — callers pass the URI string.
    Returns the transaction hash (0x-prefixed hex string). Waits for
    receipt; raises RegisterRevertedError on revert (e.g. duplicate id).
    """
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    return _register_policy(w3, policy_id, parent_id, source_uri, registry_addr, sender_key)


def _register_policy(
    w3: Web3,
    policy_id: str,
    parent_id: str | None,
    source_uri: str,
    registry_addr: str,
    sender_key: str,
) -> str:
    # Private hook so tests can inject Web3(EthereumTesterProvider()) without
    # spinning up an HTTP RPC. Public surface stays `rpc_url: str`.
    pid = _to_bytes32(policy_id)
    parent = _to_bytes32(parent_id) if parent_id is not None else _ZERO_BYTES32
    uri_hash = Web3.keccak(text=source_uri)
    sender_addr = Account.from_key(sender_key).address
    contract = w3.eth.contract(
        address=Web3.to_checksum_address(registry_addr), abi=_ABI
    )

    try:
        gas_estimate = contract.functions.register(pid, parent, uri_hash).estimate_gas(
            {"from": sender_addr}
        )
        gas_limit = gas_estimate * 12 // 10
    except Exception as e:
        if not _is_revert(e):
            raise
        # Fallback lets a reverting tx still reach send so the caller gets
        # a tx_hash; on real chains the receipt will carry status==0.
        gas_limit = 200_000

    tx = contract.functions.register(pid, parent, uri_hash).build_transaction(
        {
            "from": sender_addr,
            "nonce": w3.eth.get_transaction_count(sender_addr),
            "chainId": w3.eth.chain_id,
            "gas": gas_limit,
        }
    )
    signed = Account.sign_transaction(tx, sender_key)
    try:
        sent = w3.eth.send_raw_transaction(signed.raw_transaction)
    except Exception as e:
        # In-process EVMs (eth_tester) pre-execute and reject reverting txs
        # at submission rather than mining status==0. Real chains accept and
        # surface the revert in the receipt — so this branch only fires in tests.
        if _is_revert(e):
            raise RegisterRevertedError(tx_hash=f"0x{signed.hash.hex()}") from e
        raise
    receipt = w3.eth.wait_for_transaction_receipt(sent)

    tx_hash_hex = f"0x{receipt.transactionHash.hex()}"
    if receipt.status == 0:
        raise RegisterRevertedError(tx_hash=tx_hash_hex)
    return tx_hash_hex


def fetch_policy_chain(policy_id: str, rpc_url: str, registry_addr: str) -> PolicyChain:
    """Walk parent links on-chain from policy_id, max depth MAX_CHAIN_DEPTH.

    Pure reads (eth_call against the public `policies` mapping); never raises
    on missing records — absence is reported via PolicyChain.registered and
    PolicyChain.terminal.
    """
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    return _fetch_policy_chain(w3, policy_id, registry_addr)


def _fetch_policy_chain(w3: Web3, policy_id: str, registry_addr: str) -> PolicyChain:
    contract = w3.eth.contract(
        address=Web3.to_checksum_address(registry_addr), abi=_ABI
    )

    def _record(pid: bytes) -> tuple[bytes, bytes, str, int]:
        parent, uri_hash, registrant, block_num = contract.functions.policies(pid).call()
        return bytes(parent), bytes(uri_hash), registrant, block_num

    current = _to_bytes32(policy_id)
    parent, _, registrant, _ = _record(current)
    if registrant == _ZERO_ADDR:
        return PolicyChain(chain=[], registered=False, terminal="unregistered")

    hops: list[str] = []  # newest to oldest while walking
    terminal = "depth_capped"
    while len(hops) < MAX_CHAIN_DEPTH:
        if parent == _ZERO_BYTES32:
            terminal = "root"
            break
        hops.append(_to_hex(parent))
        parent_record = _record(parent)
        if parent_record[2] == _ZERO_ADDR:
            # Claimed ancestor that lives off-chain: included as the oldest
            # hop, but the walk cannot continue past it.
            terminal = "offchain_parent"
            break
        parent = parent_record[0]

    hops.reverse()
    return PolicyChain(chain=hops, registered=True, terminal=terminal)
