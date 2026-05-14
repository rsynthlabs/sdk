// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Test.sol";
import "../src/ExecutionLog.sol";

contract ExecutionLogTest is Test {
    ExecutionLog executionLog;

    function setUp() public {
        executionLog = new ExecutionLog();
    }

    function test_emits_event_on_record() public {
        bytes32 hash = keccak256("test");
        vm.expectEmit(true, true, false, false);
        emit ExecutionLog.ExecutionRecorded(10311, hash, 0);
        executionLog.record(10311, hash, "");
    }
}
