"""Tests for the rsynth CLI. See SCHEMA.md §4 and cli.py."""

import argparse
import sys

import pytest

from rsynth.anchor import _anchor
from rsynth.cli import _main, main
from rsynth.payload import Payload
from rsynth.sign import sign

from .test_payload import SCHEMA_EXAMPLE
from .test_sign import HARDHAT_KEY_0


WRONG_ADDR = "0x0000000000000000000000000000000000000001"


def _payload() -> Payload:
    return Payload.model_validate(SCHEMA_EXAMPLE)


def _args(tx_hash: str, contract_addr: str, payload=None) -> argparse.Namespace:
    return argparse.Namespace(
        cmd="verify",
        tx_hash=tx_hash,
        rpc_url=None,
        contract_addr=contract_addr,
        payload=payload,
    )


def test_cli_verify_prints_signer_and_hash(deployed, capsys):
    w3, addr, _abi = deployed
    p = _payload()
    sig = sign(p, HARDHAT_KEY_0)
    tx_hash = _anchor(w3, p, sig, addr, HARDHAT_KEY_0)
    rc = _main(w3, _args(tx_hash, addr))
    out = capsys.readouterr().out
    assert rc == 0
    assert "signer:" in out
    assert "payload_hash:" in out
    assert "block:" in out
    assert "basescan:" in out


def test_cli_verify_with_payload_match_ok(deployed, capsys, tmp_path):
    w3, addr, _abi = deployed
    p = _payload()
    sig = sign(p, HARDHAT_KEY_0)
    tx_hash = _anchor(w3, p, sig, addr, HARDHAT_KEY_0)
    payload_file = tmp_path / "payload.json"
    payload_file.write_text(p.model_dump_json())
    rc = _main(w3, _args(tx_hash, addr, payload=payload_file))
    out = capsys.readouterr().out
    assert rc == 0
    assert "match: ok" in out


def test_cli_verify_with_payload_mismatch(deployed, capsys, tmp_path):
    w3, addr, _abi = deployed
    p = _payload()
    sig = sign(p, HARDHAT_KEY_0)
    tx_hash = _anchor(w3, p, sig, addr, HARDHAT_KEY_0)
    tampered = p.model_copy(update={"score": 0.5})
    payload_file = tmp_path / "payload.json"
    payload_file.write_text(tampered.model_dump_json())
    rc = _main(w3, _args(tx_hash, addr, payload=payload_file))
    out = capsys.readouterr().out
    assert rc == 2
    assert "match: FAIL" in out


def test_cli_verify_anchor_not_found(deployed, capsys):
    w3, addr, _abi = deployed
    rc = _main(w3, _args("0x" + "00" * 32, addr))
    err = capsys.readouterr().err
    assert rc == 3
    assert "not found" in err.lower()


def test_cli_missing_rpc_url(monkeypatch, capsys):
    monkeypatch.delenv("RSYNTH_RPC_URL", raising=False)
    monkeypatch.setattr(
        sys,
        "argv",
        ["rsynth", "verify", "0x" + "00" * 32, "--contract-addr", WRONG_ADDR],
    )
    with pytest.raises(SystemExit) as exc:
        main()
    err = capsys.readouterr().err
    assert exc.value.code == 1
    assert "rpc" in err.lower()
