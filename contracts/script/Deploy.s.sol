// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Script.sol";
import "../src/ExecutionLog.sol";

contract Deploy is Script {
    function run() external returns (ExecutionLog) {
        vm.startBroadcast();
        ExecutionLog log = new ExecutionLog();
        vm.stopBroadcast();
        return log;
    }
}
