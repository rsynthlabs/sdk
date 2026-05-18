"""Tests for EIP-191 sign/verify. See SCHEMA.md §3."""

from rsynth.payload import Payload
from rsynth.sign import sign, verify

from .test_payload import SCHEMA_EXAMPLE


HARDHAT_KEY_0 = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
HARDHAT_ADDR_0 = "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"

SCHEMA_EXAMPLE_SIG = (
    "fb2c5b4fc6ab2a10b3026da227d1419529c7ac84f56779bdf3b862eebdec4102"
    "08bed0e00f2465d76f935a95e5abce64e064546a6c9a5a59e3336e578877ff9c"
    "1c"
)


def _payload() -> Payload:
    return Payload.model_validate(SCHEMA_EXAMPLE)


def test_sign_returns_65_bytes():
    sig = sign(_payload(), HARDHAT_KEY_0)
    assert isinstance(sig, bytes)
    assert len(sig) == 65


def test_sign_verify_roundtrip():
    payload = _payload()
    sig = sign(payload, HARDHAT_KEY_0)
    assert verify(payload, sig) == HARDHAT_ADDR_0


def test_known_vector_signature():
    # ECDSA via eth_account is deterministic (RFC 6979). Locking the exact
    # signature bytes catches drift in canonical_bytes or the signing path.
    sig = sign(_payload(), HARDHAT_KEY_0)
    assert sig.hex() == SCHEMA_EXAMPLE_SIG


def test_tampered_payload_recovers_different_address():
    # Verifying the original signature against a mutated payload must not
    # recover the original signer — otherwise integrity is not enforced.
    payload = _payload()
    sig = sign(payload, HARDHAT_KEY_0)
    tampered = payload.model_copy(update={"score": 0.95})
    assert verify(tampered, sig) != HARDHAT_ADDR_0
