"""rsynth — Verifiable Robot Execution SDK."""

from .anchor import AnchorRevertedError, anchor
from .fetch import AnchorMismatchError, AnchorNotFoundError, LineageError, VersionError
from .fetch import verify as verify_anchor
from .fetch import validate_version, verify_anchor_with_lineage
from .payload import Payload, PolicyMeta, canonical_bytes, payload_hash
from .registry import PolicyChain, RegisterRevertedError, fetch_policy_chain, register_policy
from .sign import sign, verify

__version__ = "0.0.1"
__all__ = [
    "Payload",
    "PolicyMeta",
    "canonical_bytes",
    "payload_hash",
    "sign",
    "verify",
    "anchor",
    "AnchorRevertedError",
    "verify_anchor",
    "verify_anchor_with_lineage",
    "validate_version",
    "AnchorNotFoundError",
    "AnchorMismatchError",
    "LineageError",
    "VersionError",
    "register_policy",
    "fetch_policy_chain",
    "PolicyChain",
    "RegisterRevertedError",
]
