# v0.1 to v0.2 payload diff

*Draft, v0.2.0. Not yet released. For verifier authors implementing v0.2 support alongside existing v0.1 support.*

baseline: [`../../SCHEMA.md`](../../SCHEMA.md) (v0.1.0). narrative spec: [`POLICY-LINEAGE.md`](./POLICY-LINEAGE.md).

---

## 1. version semantics

the `version` field controls dispatch. it is required in both v0.1 and v0.2.

| value | path |
|---|---|
| `"0.1.0"` | legacy. no `policy` block expected. verify per v0.1 SCHEMA.md. |
| `"0.2.0"` | lineage. `policy` block required. verify per this document. |
| anything else | reject. |

dispatch on the string, not on presence of the `policy` key.

## 2. side-by-side example

### v0.1.0

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

### v0.2.0

```json
{
  "version": "0.2.0",
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
  "outcome": "SUCCESS",
  "policy": {
    "id": "0x9f3a1b...c0d2",
    "parent_id": "0x4d2e8c...a1b7",
    "source_uri": "hf://lerobot/smolvla-base@a1b2c3d",
    "lineage_chain": ["0x4d2e8c...a1b7"]
  }
}
```

## 3. added fields

| field | type | required | description |
|---|---|---|---|
| `policy` | object | yes (v0.2) | lineage block. one entry per payload. |
| `policy.id` | string, `0x`-prefixed 32-byte hex | yes (v0.2) | commitment to this policy. canonicalization left open, see [`POLICY-LINEAGE.md`](./POLICY-LINEAGE.md) §9. |
| `policy.parent_id` | string `\|` null | yes (v0.2) | parent commitment. null for root policies. |
| `policy.source_uri` | string | yes (v0.2) | resolvable pointer (`hf://`, `ipfs://`, `s3://`, `https://`, ...). not load-bearing for verification. |
| `policy.lineage_chain` | string array | no | optional ancestor list, oldest to newest, max length 16. convenience cache. canonical chain = on-chain `PolicyLineage` events. |

## 4. removed or renamed fields

none. v0.2 is purely additive. every v0.1 field is preserved with identical type and semantics.

## 5. canonicalization

unchanged. see [`../../SCHEMA.md`](../../SCHEMA.md) §2.

1. JSON serialization with sorted keys at every depth.
2. No whitespace between tokens.
3. UTF-8 encoding.
4. No trailing newline.
5. Hash: `keccak256(canonical_bytes(payload))`. 32 bytes.

the `policy` block is included in the hash automatically. sorted-key serialization places `policy` before `robot_id`, `score`, etc.

## 6. signature

unchanged. EIP-191 personal-sign over `keccak256(canonical_bytes(payload))`, 65-byte `(r, s, v)`. the signature now cryptographically commits to the `policy` block by construction.

## 7. hash compatibility

a v0.1 payload re-encoded with a `policy` block becomes a v0.2 payload with a different hash. there is no in-place upgrade for already-anchored v0.1 payloads. operators wanting retroactive lineage must re-anchor.

implication for indexers: `ExecutionRecorded.payloadHash` values from v0.1 and v0.2 are drawn from disjoint hash sets only when the underlying payloads differ in any field, which they do whenever `version` differs. no collision risk in practice.

## 8. verifier dispatch

reference pseudocode for a verifier supporting both versions:

```python
import json
from rsynth import canonical_bytes, payload_hash, verify_anchor

def verify(tx_hash, payload_path, rpc_url, contract_addr, registry_addr=None):
    payload = json.loads(open(payload_path).read())
    version = payload.get("version")

    signer, on_chain_hash = verify_anchor(tx_hash, rpc_url, contract_addr)
    assert payload_hash(payload) == on_chain_hash

    if version == "0.1.0":
        return {"signer": signer, "hash": on_chain_hash}

    if version == "0.2.0":
        assert "policy" in payload
        chain = walk_lineage(payload["policy"]["id"], rpc_url, registry_addr)
        return {"signer": signer, "hash": on_chain_hash, "policy_chain": chain}

    raise ValueError(f"unknown payload version: {version}")
```

`walk_lineage` queries the `PolicyRegistry` contract for `PolicyLineage` events filtered by `policyId`, follows `parentId` back to root or to a node with `parent_id = null`, and returns the ordered chain.
