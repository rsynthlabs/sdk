"""rsynth — Verifiable Robot Execution SDK."""

from .anchor import AnchorRevertedError, anchor
from .fetch import AnchorNotFoundError
from .fetch import verify as verify_anchor
from .payload import Payload, canonical_bytes, payload_hash
from .sign import sign, verify

__version__ = "0.0.1"
__all__ = [
    "Payload",
    "canonical_bytes",
    "payload_hash",
    "sign",
    "verify",
    "anchor",
    "AnchorRevertedError",
    "verify_anchor",
    "AnchorNotFoundError",
]
