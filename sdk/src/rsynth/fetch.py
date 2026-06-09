"""On-chain anchor verification. See SCHEMA.md §4.

Naming note: at the package level this function is re-exported as
`verify_anchor` to avoid collision with `sign.verify` (signature
recovery). Internally the module keeps the canonical name `verify`.
"""

import json
from importlib.resources import files

from web3 import Web3
from web3.exceptions import TransactionNotFound
from web3.logs import DISCARD

from .payload import Payload, payload_hash

_ABI = json.loads(files("rsynth.abi").joinpath("ExecutionLog.json").read_text())


class AnchorNotFoundError(Exception):
    """Raised when no ExecutionRecorded event found at the given tx_hash."""

    def __init__(self, tx_hash: str, message: str = ""):
        self.tx_hash = tx_hash
        super().__init__(f"Anchor not found at {tx_hash}: {message}")


class AnchorMismatchError(Exception):
    """Raised when the anchored hash does not match payload_hash(payload)."""

    def __init__(self, tx_hash: str, message: str = ""):
        self.tx_hash = tx_hash
        super().__init__(f"Anchor hash mismatch at {tx_hash}: {message}")


class LineageError(Exception):
    """Raised when a payload's self-attested policy lineage is invalid.

    `reason` is one of: malformed, depth_overflow, broken_parent.
    """

    def __init__(self, reason: str, message: str = ""):
        self.reason = reason
        super().__init__(f"Invalid policy lineage ({reason}): {message}")


class VersionError(Exception):
    """Raised when a payload's version string is inconsistent with its policy block.

    `reason` is one of: unknown_version, policy_required, policy_forbidden.
    """

    def __init__(self, reason: str, message: str = ""):
        self.reason = reason
        super().__init__(f"Invalid payload version ({reason}): {message}")


def verify(tx_hash: str, rpc_url: str, contract_addr: str) -> tuple[str, bytes]:
    """Fetch ExecutionRecorded event from a tx receipt.

    Returns (signer_address, payload_hash_bytes32). The caller is responsible
    for comparing payload_hash_bytes32 against their off-chain payload via
    payload_hash(payload) — fetch.verify does NOT take a payload object.

    Raises AnchorNotFoundError if the receipt has no ExecutionRecorded log
    from contract_addr (wrong tx, wrong contract, or pending tx).
    """
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    return _verify(w3, tx_hash, contract_addr)


def _verify(w3: Web3, tx_hash: str, contract_addr: str) -> tuple[str, bytes]:
    try:
        receipt = w3.eth.get_transaction_receipt(tx_hash)
    except TransactionNotFound as e:
        raise AnchorNotFoundError(tx_hash, "transaction not found") from e

    contract_addr_cs = Web3.to_checksum_address(contract_addr)
    contract = w3.eth.contract(address=contract_addr_cs, abi=_ABI)
    decoded = contract.events.ExecutionRecorded().process_receipt(
        receipt, errors=DISCARD
    )
    # process_receipt matches logs by topic[0] only — it does NOT filter by
    # log.address. We do that ourselves so a tx that emits ExecutionRecorded
    # from a different ExecutionLog instance is correctly rejected.
    matched = [
        e
        for e in decoded
        if Web3.to_checksum_address(e["address"]) == contract_addr_cs
    ]
    if not matched:
        raise AnchorNotFoundError(tx_hash)
    # v0.1 invariant: one record() call per tx → one ExecutionRecorded per receipt.
    event = matched[0]
    return event["args"]["signer"], bytes(event["args"]["payloadHash"])


def _validate_lineage(payload: Payload) -> list[str]:
    """Validate a payload's self-attested policy lineage. See POLICY-LINEAGE.md.

    Returns the validated lineage chain (ancestors, oldest to newest). A payload
    with no policy block (v0.1) returns an empty chain and never raises — it
    verifies identically to v0.1. Raises LineageError on a malformed policy, a
    chain deeper than 16, or a non-empty chain that does not end at parent_id.
    """
    policy = payload.policy
    if policy is None:
        return []
    if not policy.id or not policy.source_uri:
        raise LineageError("malformed", "policy id and source_uri are required")
    chain = policy.lineage_chain or []
    if len(chain) > 16:
        raise LineageError("depth_overflow", f"lineage_chain has {len(chain)} links (max 16)")
    if any(not link for link in chain):
        raise LineageError("malformed", "lineage_chain contains an empty link")
    if chain and chain[-1] != policy.parent_id:
        raise LineageError("broken_parent", "newest lineage_chain link must equal parent_id")
    return chain


def validate_version(payload: Payload) -> str:
    """Validate version/policy consistency. See docs/v0.2/SCHEMA-DIFF.md §1.

    "0.1.0" must NOT carry a policy block (legacy path); "0.2.0" MUST carry one
    (lineage path); any other version is rejected. Dispatch is on the version
    string, never on presence of the policy key. Returns the validated version.

    Pure: never touches canonical_bytes / payload_hash / sign, so a v0.1
    "0.1.0"/no-policy payload passes here and still hashes byte-identically.

    Raises VersionError(reason=): policy_forbidden ("0.1.0" + policy),
    policy_required ("0.2.0" + no policy), unknown_version (any other version).
    """
    version = payload.version
    has_policy = payload.policy is not None
    if version == "0.1.0":
        if has_policy:
            raise VersionError("policy_forbidden", "version 0.1.0 must not carry a policy block")
        return version
    if version == "0.2.0":
        if not has_policy:
            raise VersionError("policy_required", "version 0.2.0 requires a policy block")
        return version
    raise VersionError("unknown_version", f"unsupported payload version: {version!r}")


def _verify_with_lineage(
    w3: Web3, tx_hash: str, payload: Payload, contract_addr: str
) -> tuple[str, bytes, list[str]]:
    signer, on_chain_hash = _verify(w3, tx_hash, contract_addr)
    if on_chain_hash != payload_hash(payload):
        raise AnchorMismatchError(tx_hash, "anchored hash does not match payload_hash(payload)")
    return signer, on_chain_hash, _validate_lineage(payload)


def verify_anchor_with_lineage(
    tx_hash: str, payload: Payload, rpc_url: str, contract_addr: str
) -> tuple[str, bytes, list[str]]:
    """Verify an on-chain anchor and validate the payload's policy lineage.

    Like `verify`, but takes the payload: it compares the anchored hash against
    payload_hash(payload) itself (raising AnchorMismatchError on a mismatch) and
    walks the self-attested policy.lineage_chain. Returns
    (signer_address, payload_hash_bytes32, policy_chain). policy_chain is the
    validated lineage (oldest to newest), empty for a v0.1 / no-policy payload.

    Raises AnchorNotFoundError (no record at tx_hash), AnchorMismatchError
    (hash mismatch), or LineageError (malformed / over-deep / broken lineage).
    """
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    return _verify_with_lineage(w3, tx_hash, payload, contract_addr)
