# policy lineage

*Draft, v0.2.0. Subject to change before release. This file proposes an additive primitive over the v0.1 execution payload defined in [`../../SCHEMA.md`](../../SCHEMA.md). v0.1 contract and SDK behavior remain unchanged.*

`commit. anchor. inherit.`

---

## 1. motivation

v0.1 anchors prove that a specific key signed a specific execution payload at a specific block. that is enough to bind a robot to a claimed metric, outcome, and timestamp. it is not enough to bind a robot to the *policy* that generated the action.

open VLA models are forks of forks. `smolvla-base` is finetuned by hundreds of teams; `openvla`, `molmoact`, and `π0` are each forking out independent lineage trees. when a robot anchors an execution today, there is no on-chain record of which weights ran. two robots claiming the same `score` may be running entirely different policies, and a downstream consumer cannot tell.

v0.2 fills that gap with one additive field on the payload and one auxiliary contract. concrete example: an operator finetunes `lerobot/smolvla-base` for a kitchen pick-and-place task, publishes the resulting weights, and anchors each evaluation episode. with v0.2, every anchored payload references `policy.id` (the commitment to the finetuned weights) and `policy.parent_id` (the commitment to `smolvla-base`). third parties walk the on-chain lineage chain to audit which policy actually ran, without trusting the operator's claims.

## 2. concepts

- **`policy_id`**: 32-byte commitment to a specific policy. canonicalization (weights-hash vs revision-hash vs custom manifest) is left open in §9.
- **`parent_policy_id`**: 32-byte commitment to the previous version this policy was forked or finetuned from. nullable for root policies that have no parent in this registry.
- **`lineage_chain`**: optional ordered list of ancestor `policy_id`s, oldest to newest, max depth 16. self-attested convenience field on the payload. the canonical chain is the one walked from on-chain `PolicyLineage` events.
- **`source_uri`**: human-readable pointer to weights or manifest (`hf://lerobot/smolvla-base@<revision>`, `ipfs://<cid>`, `s3://...`). not load-bearing for cryptographic verification, useful for discovery.

## 3. payload v0.2 schema diff vs v0.1

v0.2 adds one block, `policy`, and bumps the `version` string to `"0.2.0"`. all other v0.1 fields are unchanged. additive only, no renames, no removals.

```diff
 {
-  "version": "0.1.0",
+  "version": "0.2.0",
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
-  "outcome": "SUCCESS"
+  "outcome": "SUCCESS",
+  "policy": {
+    "id": "0x<32 bytes hex>",
+    "parent_id": "0x<32 bytes hex> | null",
+    "source_uri": "hf://lerobot/smolvla-base@<revision>",
+    "lineage_chain": ["0x...", "0x..."]
+  }
 }
```

full field reference and per-field types live in [`SCHEMA-DIFF.md`](./SCHEMA-DIFF.md).

## 4. canonicalization

unchanged from v0.1. see [`../../SCHEMA.md`](../../SCHEMA.md) §2:

1. JSON serialization with sorted keys at every depth.
2. No whitespace between tokens.
3. UTF-8 encoding.
4. No trailing newline.

hash function is unchanged: `keccak256(canonical_bytes(payload))`. the `policy` block is included in the hash automatically because sorted-key serialization covers it.

**version detection**: v0.2 verifiers dispatch on the `version` string. `"0.1.0"` takes the legacy path (no `policy` block expected). `"0.2.0"` takes the lineage path (`policy` block required). unknown versions are rejected. presence-of-key dispatch is explicitly NOT used; the `version` field is the source of truth.

## 5. contract api extension

three options, with tradeoff analysis.

### option A: extend the existing ExecutionLog contract

add `recordWithPolicy(bytes32 payloadHash, bytes calldata signature, bytes32 policyId, bytes32 parentId)` to `ExecutionLog.sol`.

blocked. the v0.1 contract is immutable and already deployed at the live base address. there is no upgrade pattern. rejecting any code change to the deployed contract is a hard constraint.

### option B: deploy ExecutionLogV2

ship a new `ExecutionLogV2.sol` at a new address. it takes the same `(payloadHash, signature)` plus `(policyId, parentId)` and emits a single combined event.

workable but weaker. downstream verifiers now have to learn two contract addresses, two event shapes, and a dispatch rule. v0.1 anchors at the v0.1 address remain canonical for v0.1 payloads; v0.2 anchors live at a separate address. this splits the verifier surface and complicates indexers.

### option C (recommended): auxiliary PolicyRegistry

deploy a small `PolicyRegistry.sol` contract that owns one event:

```solidity
event PolicyLineage(
    bytes32 indexed payloadHash,
    bytes32 indexed policyId,
    bytes32 parentId
);

function register(
    bytes32 payloadHash,
    bytes32 policyId,
    bytes32 parentId
) external {
    emit PolicyLineage(payloadHash, policyId, parentId);
}
```

the SDK calls both `ExecutionLog.record(hash, sig)` and `PolicyRegistry.register(hash, policyId, parentId)`. two sub-shapes:

- **C-a (preferred)**: two separate transactions, or one batched transaction via Multicall3 (`0xcA11bde05977b3631167028862bE2a173976CA11`, deployed on base). zero changes to v0.1. zero orchestrator dependency. v0.1 verifiers see exactly the same `ExecutionLog.record` event they already see; new v0.2 verifiers additionally walk `PolicyLineage` events from the registry address.
- **C-b**: deploy a `ExecutionLogPlus.sol` orchestrator that internally `call`s `ExecutionLog.record(...)` and emits `PolicyLineage` in the same tx. single transaction, but adds a new contract dependency and a cross-contract call.

**recommend C-a.** smallest blast radius. v0.1 contract is byte-untouched. v0.1 verifiers and indexers are unaffected. the only new on-chain artifact is the `PolicyRegistry` deployment. anchoring becomes either two cheap txs or one Multicall3 batch, at the operator's choice.

## 6. sdk changes

planned for the v0.2 implementation pass (not part of this spec):

- `Payload` model gains an optional `PolicyMeta` field: `id`, `parent_id`, `source_uri`, `lineage_chain`. `model_dump(mode="json")` keeps the v0.2 block in canonical form automatically.
- `canonical_bytes` and `payload_hash` are unchanged. sorted-key JSON serialization covers the new block with no code changes.
- new CLI subcommand:
  ```
  rsynth lineage <policy_id> --rpc-url <url> --registry-addr <addr>
  ```
  walks `PolicyLineage` events from the registry, prints ancestors oldest-to-newest, exits 0 on success or 3 if the policy is not registered.
- existing `rsynth verify` gains optional behavior: when `--payload` is supplied and `version == "0.2.0"`, also resolve and print `policy.id` and the chain depth from on-chain events.
- new high-level helper: `verify_anchor_with_lineage(tx_hash, payload, rpc_url, contract_addr, registry_addr) -> (signer, payload_hash, policy_chain)`.

backward compat is maintained at the SDK layer: v0.2 SDK accepts v0.1 payloads, returns an empty `policy_chain` for them, and never queries the registry when the payload is v0.1.

## 7. cross-chain considerations

single-chain only for v0.2 (base mainnet). `PolicyRegistry` deploys to the same chain as `ExecutionLog`. multi-chain anchor adapters and cross-chain lineage walks are out of scope; tracked for v0.3+.

## 8. migration path

- v0.1 SDK and contract continue working unchanged.
- v0.2 SDK reads v0.1 anchors via `version` string dispatch. no breaking change for existing verifiers.
- v0.2 is opt-in for operators. no mandatory upgrade for downstream consumers.
- the only required on-chain action is the `PolicyRegistry` deployment. `ExecutionLog` stays at its current base address.
- a v0.1 payload re-encoded with a `policy` block becomes a v0.2 payload with a different hash. there is no in-place upgrade for already-anchored v0.1 payloads. operators who want lineage retroactively must re-anchor.

## 9. open questions

- **policy_id canonicalization**: deterministic from weights (e.g. `keccak256` of a sorted weights manifest, or the merkle root of a chunked weights file) vs an arbitrary commitment chosen by the operator. former is auditable but expensive to compute; latter is cheap but trust-shifted.
- **hf hub revision hashes vs custom manifest**: should `policy.id` accept hf revision hashes directly, or always require a wrapped manifest hash? affects how operators using off-the-shelf hf checkpoints integrate.
- **privacy**: lineage chains may reveal proprietary finetune ancestry. should `parent_id` be opt-in, or always required? null-for-root collides with null-for-private. one option: distinguish null (root) from `0xff..ff` (withheld).
- **registration ordering**: does `PolicyRegistry.register` require the `parent_id` to already be registered, or can chains be assembled out of order? in-order enforcement makes walks simple but introduces a registration ordering constraint between collaborators.
- **lineage_chain payload field**: redundant with the on-chain walk. keep as convenience cache, or drop and force verifiers to walk on-chain?

## 10. slogan

```
commit. anchor. inherit.
```

mirrors the v0.1 cadence `sign. anchor. verify.`. used as the public-facing v0.2 triplet on the landing page and in this spec directory.
