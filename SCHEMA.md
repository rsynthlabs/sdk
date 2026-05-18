# Execution Payload Schema

*Draft — v0.1.0. Subject to change before first release.*

A **robot execution payload** is the canonical record of a single robot performing a single task. The payload is signed by the agent (per ERC-8004), its hash is anchored on Base, and any third party can verify that an execution matching the on-chain hash actually corresponds to the reported metrics and outcome.

This file defines the payload format and the verification flow. Implementation lives in `sdk/` and `contracts/`.

---

## 1. Payload (off-chain JSON)

```json
{
  "version": "0.1.0",
  "agent_id": 10311,
  "robot_id": "roarm-m3-01",
  "episode_id": "ep_2026-05-14_18-22-31_004a",
  "task": "pick and place the cube",
  "started_at": "2026-05-14T18:22:31Z",
  "ended_at": "2026-05-14T18:22:53Z",
  "duration_seconds": 22.6,
  "frames": 678,
  "metrics": {
    "rmse": 4.583,
    "jerk": 2434753.0,
    "end_variance": 0.0
  },
  "score": 0.90,
  "outcome": "SUCCESS"
}
```

### Field reference

| Field | Type | Description |
|---|---|---|
| `version` | string | Schema version (semver). |
| `agent_id` | int | ERC-8004 agent identifier. The signer must control the agent's registered key. |
| `robot_id` | string | Identifier within the agent's fleet. Free-form, agent-defined. |
| `episode_id` | string | Unique identifier for this execution. Recommended: timestamp + short hash. |
| `task` | string | Human-readable description of what the robot attempted. |
| `started_at` | string (ISO 8601, UTC) | Start time. |
| `ended_at` | string (ISO 8601, UTC) | End time. |
| `duration_seconds` | number | `ended_at − started_at` in seconds. |
| `frames` | int | Number of recorded frames in the episode. |
| `metrics.rmse` | number | Root-mean-square error against reference trajectory. Domain-specific units. |
| `metrics.jerk` | number | Integral of jerk over the episode. Lower = smoother motion. |
| `metrics.end_variance` | number | Variance at end of episode. Lower = better settling. |
| `score` | number ∈ [0, 1] | Aggregate quality score. Derivation is agent-specific but must be deterministic given the metrics. |
| `outcome` | enum | One of `SUCCESS`, `PARTIAL`, `FAIL`. |

### Outcome semantics

- **`SUCCESS`** — task completed within agent-defined success criteria.
- **`PARTIAL`** — task partially completed; some success criteria met, others not.
- **`FAIL`** — task did not complete or violated a hard constraint.

Definitions of "success criteria" are agent-defined and should be documented separately. The enum is intentionally coarse — finer-grained quality is captured by `score` and `metrics`.

---

## 2. Canonicalization

Before hashing or signing, the payload is converted to a deterministic byte sequence:

1. JSON serialization with **sorted keys at every depth**.
2. **No whitespace** between tokens (no indentation, no spaces after `:` or `,`).
3. **UTF-8** encoding.
4. **No trailing newline.**

Reference implementation: `sdk/rsynth/payload.py::canonical_bytes`.

The keccak256 hash of the canonical byte sequence is the **payload hash** referenced on-chain.

---

## 3. Signature

The payload is signed by the agent's key registered in ERC-8004.

- **Algorithm:** secp256k1 (Ethereum-standard).
- **Signed message:** EIP-191 personal-sign over keccak256(canonical_bytes(payload)) (32 bytes).
- **Output:** 65-byte signature `(r, s, v)`.

Verification: recover the signer address from the signature and confirm it matches the address registered for `agent_id` in the ERC-8004 registry.

---

## 4. On-chain anchor

Contract: `ExecutionLog` (see `contracts/src/ExecutionLog.sol`).

Method:

```solidity
function record(
  bytes32 payloadHash,
  bytes calldata signature
) external;
```

Behavior:
- Wrap `payloadHash` with the EIP-191 prefix (`MessageHashUtils.toEthSignedMessageHash`).
- Recover signer with `ECDSA.recover`.
- Require recovered signer != `address(0)`.
- Emit `ExecutionRecorded(signer, payloadHash, blockTimestamp)`.

The contract stores no payload data — only the emitted event. Off-chain payloads are referenced by hash and retrieved from agent-provided storage (IPFS, S3, agent's own server — agent's choice).

> **v0.1 scope.** The contract accepts any signer; linking signers to agent identities (ERC-8004 registry coupling) is deferred to v0.2. Verifiers cross-reference signer addresses out-of-band in v0.1.

---

## 5. Verification flow

![Execution flow](./docs/assets/flow.svg)

Given an on-chain `ExecutionRecorded(signer, payloadHash, ...)` event:

1. Fetch the off-chain payload (URL provided by the agent or discovered via the registry).
2. Compute `keccak256(canonical_bytes(payload))`.
3. Require computed hash == `payloadHash`.
4. The payload's claimed metrics, outcome, and timing are then trustable: the agent committed to them at the block timestamp.

A verifier needs only the agent's ERC-8004 entry and the on-chain event to confirm authenticity.

---

## 6. What this is not

- **Not a proof of correctness.** The payload records what the agent claims happened. The signature proves the agent claimed it, not that the metrics are accurate. Independent measurement infrastructure is out of scope.
- **Not a privacy layer.** Payloads are public by design. Sensitive context (operator identity, location specifics) should be omitted before signing.
- **Not a real-time stream.** Anchoring on Base costs gas. Batch and finalize at episode boundaries; do not anchor per-frame.

---

## 7. Open questions (v0.2+)

- Batched anchoring: Merkle root over N episodes, single transaction.
- Reference trajectories: how to identify and reference them on-chain.
- Score derivation transparency: should agents publish their `score(metrics) → [0,1]` function?
- Aggregate execution metadata in ERC-8004 entries.

Contributions welcome via PR or issue.
