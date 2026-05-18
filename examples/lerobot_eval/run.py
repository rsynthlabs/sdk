"""End-to-end lerobot/pusht eval demo. Run: `python run.py`."""

import os
import sys
from datetime import datetime, timedelta, timezone

import numpy as np
from eth_account import Account

from rsynth import Payload, anchor, payload_hash, sign, verify_anchor

from metrics import end_variance, jerk, rmse


REQUIRED_ENV = ("BASE_RPC_URL", "EXECUTION_LOG_ADDR", "SENDER_PRIVATE_KEY")


def main() -> None:
    missing = [v for v in REQUIRED_ENV if not os.environ.get(v)]
    if missing:
        print(f"missing required env vars: {', '.join(missing)}", file=sys.stderr)
        print(f"see {os.path.dirname(__file__)}/README.md", file=sys.stderr)
        sys.exit(1)

    rpc, contract, sender_key = (os.environ[v] for v in REQUIRED_ENV)

    # Deferred so `python run.py` with missing env vars exits cleanly even
    # when the heavy example-extras (lerobot + torch) aren't installed.
    from lerobot.common.datasets.lerobot_dataset import LeRobotDataset

    acct = Account.create()
    print(f"agent key: {acct.address} (ephemeral)")

    ds = LeRobotDataset("lerobot/pusht", episodes=[0])
    actions = np.stack([np.asarray(f["action"]) for f in ds])
    timestamps = [float(f["timestamp"]) for f in ds]
    duration = float(timestamps[-1] - timestamps[0])

    started = datetime.now(timezone.utc)
    payload = Payload(
        version="0.1.0",
        agent_id=10311,
        robot_id="sim-lerobot-pusht-ep0",
        episode_id=f"ep_{started.strftime('%Y-%m-%dT%H-%M-%SZ')}_pusht0",
        task="push T to goal (lerobot/pusht reference replay)",
        started_at=started.strftime("%Y-%m-%dT%H:%M:%SZ"),
        ended_at=(started + timedelta(seconds=duration)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        duration_seconds=duration,
        frames=int(actions.shape[0]),
        metrics={
            "rmse": rmse(actions),
            "jerk": jerk(actions),
            "end_variance": end_variance(actions),
        },
        score=0.90,
        outcome="SUCCESS",
    )

    sig = sign(payload, acct.key.hex())
    tx_hash = anchor(payload, sig, rpc, contract, sender_key)
    print(f"anchored: https://basescan.org/tx/{tx_hash}")

    signer, on_chain_hash = verify_anchor(tx_hash, rpc, contract)
    assert signer == acct.address, f"signer mismatch: {signer} vs {acct.address}"
    assert on_chain_hash == payload_hash(payload), "hash mismatch"
    print(f"verified: signer={signer}")
    print(f"hash: 0x{on_chain_hash.hex()}")


if __name__ == "__main__":
    main()
