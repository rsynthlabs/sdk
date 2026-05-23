// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Script.sol";
import {ExecutionLog} from "../src/ExecutionLog.sol";

contract Deploy is Script {
    function run() external returns (ExecutionLog log) {
        string memory network = vm.envOr("RSYNTH_NETWORK", string("base-sepolia"));

        vm.startBroadcast();
        log = new ExecutionLog();
        vm.stopBroadcast();

        vm.createDir("deployments", true);
        string memory root = "deployment";
        vm.serializeAddress(root, "executionLog", address(log));
        vm.serializeUint(root, "chainId", block.chainid);
        vm.serializeUint(root, "blockNumber", block.number);
        string memory json = vm.serializeAddress(root, "deployer", tx.origin);
        vm.writeJson(json, string.concat("deployments/", network, ".json"));
    }
}
