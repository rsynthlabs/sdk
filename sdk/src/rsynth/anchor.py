"""On-chain anchor submission. See SCHEMA.md §4."""

import json
from importlib.resources import files

from eth_account import Account
from web3 import Web3
from web3.exceptions import ContractLogicError

from .payload import Payload, payload_hash

_ABI = json.loads(files("rsynth.abi").joinpath("ExecutionLog.json").read_text())


def _is_revert(e: BaseException) -> bool:
    # Real chains surface reverts as ContractLogicError. In-process EVMs
    # (eth_tester, used by SDK tests) raise eth_tester.exceptions.TransactionFailed
    # — matched by name to avoid importing a test-only dep.
    return isinstance(e, ContractLogicError) or type(e).__name__ == "TransactionFailed"


class AnchorRevertedError(Exception):
    """Raised when ExecutionLog.record() tx reverts on-chain."""

    def __init__(self, tx_hash: str, message: str = ""):
        self.tx_hash = tx_hash
        super().__init__(f"Anchor reverted (tx={tx_hash}): {message}")


def anchor(
    payload: Payload,
    signature: bytes,
    rpc_url: str,
    contract_addr: str,
    sender_key: str,
) -> str:
    """Submit ExecutionLog.record(payloadHash, signature) tx.

    Returns the transaction hash (0x-prefixed hex string).
    Waits for receipt; raises AnchorRevertedError on status==0.

    Note: sender_key MAY differ from the signature's signer —
    ExecutionLog is sender-agnostic (relayer pattern).
    """
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    return _anchor(w3, payload, signature, contract_addr, sender_key)


def _anchor(
    w3: Web3,
    payload: Payload,
    signature: bytes,
    contract_addr: str,
    sender_key: str,
) -> str:
    # Private hook so tests can inject Web3(EthereumTesterProvider()) without
    # spinning up an HTTP RPC. Public surface stays `rpc_url: str`.
    sender_addr = Account.from_key(sender_key).address
    ph = payload_hash(payload)
    contract = w3.eth.contract(
        address=Web3.to_checksum_address(contract_addr), abi=_ABI
    )

    try:
        gas_estimate = contract.functions.record(ph, signature).estimate_gas(
            {"from": sender_addr}
        )
        gas_limit = gas_estimate * 12 // 10
    except Exception as e:
        if not _is_revert(e):
            raise
        # Fallback lets a reverting tx still reach send so the caller gets
        # a tx_hash; on real chains the receipt will carry status==0.
        gas_limit = 200_000

    tx = contract.functions.record(ph, signature).build_transaction(
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
            raise AnchorRevertedError(tx_hash=f"0x{signed.hash.hex()}") from e
        raise
    receipt = w3.eth.wait_for_transaction_receipt(sent)

    tx_hash_hex = f"0x{receipt.transactionHash.hex()}"
    if receipt.status == 0:
        raise AnchorRevertedError(tx_hash=tx_hash_hex)
    return tx_hash_hex
