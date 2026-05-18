"""Signing and verification. See SCHEMA.md §3."""

from eth_account import Account
from eth_account.messages import encode_defunct

from .payload import Payload, payload_hash


def sign(payload: Payload, private_key: str) -> bytes:
    """EIP-191 personal-sign over keccak256(canonical_bytes(payload)).

    Returns 65-byte signature (r, s, v).
    """
    message = encode_defunct(primitive=payload_hash(payload))
    signed = Account.sign_message(message, private_key=private_key)
    return bytes(signed.signature)


def verify(payload: Payload, signature: bytes) -> str:
    """Recover signer address from an EIP-191 signature over the payload hash.

    Returns the EIP-55 checksummed address.
    """
    message = encode_defunct(primitive=payload_hash(payload))
    return Account.recover_message(message, signature=signature)
