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

_ABI = json.loads(files("rsynth.abi").joinpath("ExecutionLog.json").read_text())


class AnchorNotFoundError(Exception):
    """Raised when no ExecutionRecorded event found at the given tx_hash."""

    def __init__(self, tx_hash: str, message: str = ""):
        self.tx_hash = tx_hash
        super().__init__(f"Anchor not found at {tx_hash}: {message}")


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
