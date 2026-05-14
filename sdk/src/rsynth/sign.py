"""Signing and verification. See SCHEMA.md §3."""

from .payload import Payload


def sign(payload: Payload, private_key: str) -> bytes:
    # TODO: implement per SCHEMA.md §3
    raise NotImplementedError


def verify(payload: Payload, signature: bytes, expected_signer: str) -> bool:
    # TODO: implement per SCHEMA.md §3
    raise NotImplementedError
