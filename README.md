# rsynth SDK

verifiable robot execution. sign payloads, anchor on base, verify on-chain. zero hardware required.

- v0.1 — days 1-7 shipped, 28 tests passing
- license: MIT
- `$R` on base · [`0x9CC8...5757`](https://basescan.org/token/0x9CC8C9C88ba07Ce24D54597E174C4127C7995757)

## why

robot actions today are unverifiable blobs. rsynth turns any robot execution into a signed payload, hashed and anchored on base. counterparties verify by tx hash — no payload-side trust required.

## install

```bash
pip install -e ./sdk           # python sdk + cli
```

## 30-second example

```python
from rsynth import Payload, sign, anchor, verify_anchor, payload_hash

payload = Payload(...)  # see SCHEMA.md §1
sig = sign(payload, my_key)
tx = anchor(payload, sig, RPC_URL, CONTRACT_ADDR, sender_key)
signer, on_chain_hash = verify_anchor(tx, RPC_URL, CONTRACT_ADDR)
assert on_chain_hash == payload_hash(payload)
```

## cli

```bash
rsynth verify <tx_hash> --rpc-url <url> --contract-addr <addr>
rsynth verify <tx_hash> ... --payload payload.json   # also compares hash
```

exit codes: `0=ok`, `1=misuse`, `2=hash mismatch`, `3=not found`, `4=rpc error`, `5=invalid payload`.

## working example

see [`examples/lerobot_eval/`](./examples/lerobot_eval/) — end-to-end demo loading lerobot/pusht episode 0, computing trajectory metrics, signing, anchoring, verifying. ~50 lines.

## architecture

```
payload (canonical JSON)
  -> keccak256
  -> EIP-191 personal-sign
  -> ExecutionLog.record() on base
  -> ExecutionRecorded event (signer, payloadHash, timestamp)
```

## repo layout

- `sdk/` — python package (payload, sign, anchor, fetch, cli)
- `contracts/` — solidity (ExecutionLog.sol, deploy script, foundry tests)
- `examples/lerobot_eval/` — working sim demo
- [`SCHEMA.md`](./SCHEMA.md) — execution payload schema spec
- [`docs/SETUP.md`](./docs/SETUP.md) — developer setup notes

## tests

```bash
cd sdk && pip install -e '.[test]' && pytest -v
```

expected: 28 tests passing.

also: `forge test` in `contracts/` for solidity-side tests (4 forge tests including a python↔solidity cross-language vector).

## roadmap

- **v0.1** (now) — sign / anchor / verify_anchor, cli, lerobot example
- **v0.1.1** — mujoco example, json output mode for cli
- **v0.2** — erc-8004 registry verification, batched anchoring, x402 verifier-as-service

## license

MIT. see [LICENSE](./LICENSE).

---

[@ResearchSynth](https://x.com/ResearchSynth) · [rsynth.ai](https://rsynth.ai)
