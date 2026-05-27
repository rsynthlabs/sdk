"""scan_signers.py - read-only audit of ExecutionLog signers on base mainnet.

Iterates all ExecutionRecorded events from contract deploy block to latest,
classifies each signer as internal (in KNOWN_WALLETS) or external, writes
structured JSON to stdout and scripts/output/signers-scan-YYYY-MM-DD.json.

run from repo root:
    python scripts/scan_signers.py

env:
    BASE_RPC_URL  override the default https://mainnet.base.org endpoint
"""

import json
import os
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from importlib.resources import files
from pathlib import Path

from web3 import Web3

RPC_URL = os.environ.get("BASE_RPC_URL", "https://mainnet.base.org")
REPO_ROOT = Path(__file__).resolve().parent.parent
DEPLOYMENTS = REPO_ROOT / "contracts" / "deployments" / "base-mainnet.json"
OUTPUT_DIR = REPO_ROOT / "scripts" / "output"

CHUNK_SIZE = 10_000
CHUNK_SLEEP_S = 0.2
PROGRESS_EVERY = 10

KNOWN_WALLETS = {
    "0x132fA3855Dda4b2c085FCf3d79E9c3F15f78F15F": "rsynth-ops (payTo)",
    "0x156d727f372D06132526612b7D34CE1693365bf3": "buyer test (r402 demo signer)",
    "0x0d9242c7Da4a47E815023905e2a82B354fbCE4fd": "relayer (hot wallet)",
    "0xe182BDa14ec3EfBAa72BC0fb6aad3145d9E64bAe": "genesis ephemeral signer",
}
KNOWN_BY_CHECKSUM = {Web3.to_checksum_address(k): v for k, v in KNOWN_WALLETS.items()}

_ABI = json.loads(files("rsynth.abi").joinpath("ExecutionLog.json").read_text())


def iso_utc(ts: int) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def day_utc(ts: int) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")


def now_iso_utc() -> str:
    return (
        datetime.now(tz=timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )


def build_by_signer(events_by_signer, block_ts_cache):
    out = []
    for addr, events in events_by_signer.items():
        ordered = sorted(events, key=lambda e: e["block_number"])
        first = ordered[0]
        last = ordered[-1]
        label = KNOWN_BY_CHECKSUM.get(addr)
        out.append(
            {
                "address": addr,
                "label": label,
                "is_internal": label is not None,
                "anchor_count": len(events),
                "first_anchor_block": first["block_number"],
                "first_anchor_tx": first["tx_hash"],
                "first_anchor_timestamp_utc": iso_utc(block_ts_cache[first["block_number"]]),
                "last_anchor_timestamp_utc": iso_utc(block_ts_cache[last["block_number"]]),
            }
        )
    out.sort(key=lambda x: (x["is_internal"], -x["anchor_count"], x["address"]))
    return out


def main() -> int:
    deploy_info = json.loads(DEPLOYMENTS.read_text())
    contract_addr = Web3.to_checksum_address(deploy_info["executionLog"])
    deploy_block = int(deploy_info["blockNumber"])

    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    latest_block = w3.eth.block_number
    contract = w3.eth.contract(address=contract_addr, abi=_ABI)

    print(f"rpc: {RPC_URL}", file=sys.stderr)
    print(f"contract: {contract_addr}", file=sys.stderr)
    print(f"range: {deploy_block}..{latest_block}", file=sys.stderr)

    chunks = []
    cursor = deploy_block
    while cursor <= latest_block:
        end = min(cursor + CHUNK_SIZE - 1, latest_block)
        chunks.append((cursor, end))
        cursor = end + 1
    total = len(chunks)

    events_by_signer: dict[str, list[dict]] = defaultdict(list)
    block_ts_cache: dict[int, int] = {}
    anchors_by_day: dict[str, int] = defaultdict(int)
    total_anchors = 0
    last_scanned_block = deploy_block - 1
    incomplete = False

    try:
        for i, (cs, ce) in enumerate(chunks):
            if i == 0 or (i + 1) % PROGRESS_EVERY == 0:
                print(f"scanning {cs}..{ce} (chunk {i + 1}/{total})", file=sys.stderr)
            events = contract.events.ExecutionRecorded().get_logs(from_block=cs, to_block=ce)
            for ev in events:
                bn = ev["blockNumber"]
                if bn not in block_ts_cache:
                    block_ts_cache[bn] = w3.eth.get_block(bn)["timestamp"]
                ts = block_ts_cache[bn]
                signer = ev["args"]["signer"]
                events_by_signer[signer].append(
                    {
                        "block_number": bn,
                        "tx_hash": "0x" + ev["transactionHash"].hex(),
                    }
                )
                anchors_by_day[day_utc(ts)] += 1
                total_anchors += 1
            last_scanned_block = ce
            if i < total - 1:
                time.sleep(CHUNK_SLEEP_S)
    except KeyboardInterrupt:
        incomplete = True
        print("interrupted; finalizing partial output", file=sys.stderr)

    by_signer = build_by_signer(events_by_signer, block_ts_cache)
    internal_anchors = sum(s["anchor_count"] for s in by_signer if s["is_internal"])
    external_anchors = total_anchors - internal_anchors
    unique_external_signers = sum(1 for s in by_signer if not s["is_internal"])

    result: dict = {
        "scan_block_range": [
            deploy_block,
            last_scanned_block if incomplete else latest_block,
        ],
        "scanned_at": now_iso_utc(),
        "total_anchors": total_anchors,
        "unique_signers_total": len(by_signer),
        "internal_anchors": internal_anchors,
        "external_anchors": external_anchors,
        "unique_external_signers": unique_external_signers,
        "by_signer": by_signer,
        "anchors_by_day_utc": dict(sorted(anchors_by_day.items())),
    }
    if incomplete:
        result["incomplete"] = True

    today = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    output_path = OUTPUT_DIR / f"signers-scan-{today}.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2) + "\n")

    print(json.dumps(result, indent=2))

    if incomplete:
        print(f"partial output saved to {output_path}", file=sys.stderr)
        return 130
    print(f"output saved to {output_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
