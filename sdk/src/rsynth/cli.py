"""rsynth CLI. See docs/SETUP.md."""

import argparse
import json
import os
import sys
from pathlib import Path

from pydantic import ValidationError
from web3 import Web3
from web3.exceptions import ProviderConnectionError, Web3RPCError

from .fetch import AnchorNotFoundError, _verify
from .payload import Payload, payload_hash


class _Parser(argparse.ArgumentParser):
    """Override argparse's default exit-2-on-error so CLI misuse exits 1.

    Without this, argparse would steal exit code 2 for parse errors,
    colliding with our "hash mismatch" exit-2 contract.
    """

    def error(self, message: str) -> None:  # type: ignore[override]
        self.print_usage(sys.stderr)
        print(f"error: {message}", file=sys.stderr)
        sys.exit(1)


def _build_parser() -> _Parser:
    parser = _Parser(prog="rsynth")
    sub = parser.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("verify", help="verify an on-chain anchor by tx_hash")
    v.add_argument("tx_hash")
    v.add_argument("--rpc-url", default=os.environ.get("RSYNTH_RPC_URL"))
    v.add_argument("--contract-addr", default=os.environ.get("RSYNTH_CONTRACT_ADDR"))
    v.add_argument(
        "--payload",
        type=Path,
        default=None,
        help="optional payload.json - compare its hash against on-chain",
    )
    return parser


def _main(w3: Web3, args: argparse.Namespace) -> int:
    try:
        signer, on_chain_hash = _verify(w3, args.tx_hash, args.contract_addr)
    except AnchorNotFoundError as e:
        print(f"anchor not found: {e}", file=sys.stderr)
        return 3
    except (ProviderConnectionError, Web3RPCError, ConnectionError, TimeoutError) as e:
        print(f"rpc unreachable: {e}", file=sys.stderr)
        return 4

    receipt = w3.eth.get_transaction_receipt(args.tx_hash)
    print(f"signer: {signer}")
    print(f"payload_hash: 0x{on_chain_hash.hex()}")
    print(f"block: {receipt.blockNumber}")
    print(f"basescan: https://basescan.org/tx/{args.tx_hash}")

    if args.payload is not None:
        try:
            data = json.loads(args.payload.read_text())
            local = Payload.model_validate(data)
        except (OSError, json.JSONDecodeError, ValidationError) as e:
            print(f"invalid payload: {e}", file=sys.stderr)
            return 5
        local_hash = payload_hash(local)
        if local_hash != on_chain_hash:
            print(
                f"match: FAIL (local=0x{local_hash.hex()}, "
                f"on-chain=0x{on_chain_hash.hex()})"
            )
            return 2
        print("match: ok")

    return 0


def main() -> None:
    args = _build_parser().parse_args()
    if not args.rpc_url:
        print("--rpc-url required (or set RSYNTH_RPC_URL)", file=sys.stderr)
        sys.exit(1)
    if not args.contract_addr:
        print(
            "--contract-addr required (or set RSYNTH_CONTRACT_ADDR)", file=sys.stderr
        )
        sys.exit(1)
    w3 = Web3(Web3.HTTPProvider(args.rpc_url))
    sys.exit(_main(w3, args))


if __name__ == "__main__":
    main()
