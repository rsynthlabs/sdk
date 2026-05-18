# LeRobot eval example

End-to-end demo: load `lerobot/pusht` episode 0, compute trajectory metrics, sign a Payload with an ephemeral key, anchor it on Base via `ExecutionLog`, and verify the on-chain event round-trips.

## Install

    cd ../../sdk           # outer-sdk/sdk
    pip install -e '.[example]'

(This pulls in lerobot + torch — ~2 GB. Run once and keep the venv around.)

## Env vars

- `BASE_RPC_URL` — Base RPC endpoint (Alchemy, Infura, QuickNode, …)
- `EXECUTION_LOG_ADDR` — deployed `ExecutionLog` contract address on the same chain
- `SENDER_PRIVATE_KEY` — wallet that pays gas (does **not** need to match the signing key)

## Run

    python run.py

## Expected output

    agent key: 0x4A0F…7d2C (ephemeral)
    anchored: https://basescan.org/tx/0xabc…
    verified: signer=0x4A0F…7d2C
    hash: 0x26444c4b…

## Cost

~$0.01–0.05 per anchor on Base mainnet (single `record()` call).

## Safety

- The agent key is ephemeral — generated per run, printed to stdout, never persisted. If the wallet gets funded by accident, drain it.
- `SENDER_PRIVATE_KEY` is the gas payer. Use a minimally funded throwaway.
- This demo signs and anchors a **real** payload. The `ExecutionRecorded` event is permanent on-chain. Don't run against mainnet with anything you wouldn't want indexed forever.
