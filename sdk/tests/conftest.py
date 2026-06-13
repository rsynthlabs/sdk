"""Shared pytest fixtures and constants. See test_anchor.py and test_fetch.py."""

import json
import sys
from pathlib import Path

import pytest
from web3 import EthereumTesterProvider, Web3

from .test_sign import HARDHAT_ADDR_0


HARDHAT_KEY_1 = "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d"
HARDHAT_ADDR_1 = "0x70997970C51812dc3A010C7d01b50e0d17dc79C8"

ARTIFACT = (
    Path(__file__).parents[2] / "contracts/out/ExecutionLog.sol/ExecutionLog.json"
)
REGISTRY_ARTIFACT = (
    Path(__file__).parents[2] / "contracts/out/PolicyRegistry.sol/PolicyRegistry.json"
)


def _deploy_artifact(w3, artifact_path):
    art = json.loads(artifact_path.read_text())
    deployer = w3.eth.accounts[0]
    Contract = w3.eth.contract(abi=art["abi"], bytecode=art["bytecode"]["object"])
    deploy_tx = Contract.constructor().transact({"from": deployer})
    receipt = w3.eth.wait_for_transaction_receipt(deploy_tx)
    return receipt.contractAddress, art["abi"]


@pytest.fixture(scope="session")
def deployed():
    if not ARTIFACT.exists():
        print(
            "\n[conftest] contracts/out/ExecutionLog.sol/ExecutionLog.json missing.\n"
            "[conftest] Run `forge build` in contracts/ before pytest to enable\n"
            "[conftest] 12 anchor/fetch/cli tests (currently SKIPPED).\n",
            file=sys.stderr,
        )
        pytest.skip("forge artifact missing (run `forge build` in contracts/)")
    w3 = Web3(EthereumTesterProvider())
    contract_addr, abi = _deploy_artifact(w3, ARTIFACT)
    deployer = w3.eth.accounts[0]
    for addr in (HARDHAT_ADDR_0, HARDHAT_ADDR_1):
        w3.eth.send_transaction({"from": deployer, "to": addr, "value": 10**18})
    return w3, contract_addr, abi


@pytest.fixture(scope="session")
def deployed_registry(deployed):
    # PolicyRegistry on the SAME chain as ExecutionLog, so one injected w3
    # serves both the anchor read and the registry walk in _verify_with_lineage.
    if not REGISTRY_ARTIFACT.exists():
        pytest.skip("forge artifact missing (run `forge build` in contracts/)")
    w3, _, _ = deployed
    registry_addr, abi = _deploy_artifact(w3, REGISTRY_ARTIFACT)
    return w3, registry_addr, abi
