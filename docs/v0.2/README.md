# v0.2: policy lineage

policy provenance for verifiable robot execution. additive over v0.1. spec phase.

`commit. anchor. inherit.`

## status

IMPLEMENTED through the policy registry increment: `PolicyRegistry.sol`, `registry.py` (register / on-chain chain walk), and an optional `registry_addr` cross-check in `verify_anchor_with_lineage`. backward compatible with v0.1.

- v0.1 SDK + `ExecutionLog` contract continue working unchanged
- v0.2 SDK reads v0.1 anchors via `version` string dispatch
- no mandatory upgrade for downstream consumers
- the shipped registry is storage-based (mapping + duplicate revert), diverging from the event-only option C sketch in `POLICY-LINEAGE.md` §5 - the spec needs updating to match

## contents

- [`POLICY-LINEAGE.md`](./POLICY-LINEAGE.md) - full primitive spec: motivation, concepts, schema, contract extension, sdk changes, migration, open questions
- [`SCHEMA-DIFF.md`](./SCHEMA-DIFF.md) - payload diff for verifier authors

## baseline

v0.1 spec lives at [`../../SCHEMA.md`](../../SCHEMA.md). read it first.
