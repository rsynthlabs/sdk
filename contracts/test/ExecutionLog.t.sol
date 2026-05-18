// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Test.sol";
import {ExecutionLog} from "../src/ExecutionLog.sol";
import {MessageHashUtils} from "@openzeppelin/contracts/utils/cryptography/MessageHashUtils.sol";

contract ExecutionLogTest is Test {
    using MessageHashUtils for bytes32;

    ExecutionLog executionLog;

    uint256 constant HARDHAT_KEY_0 =
        0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80;
    address constant HARDHAT_ADDR_0 =
        0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266;

    bytes32 constant SCHEMA_EXAMPLE_HASH =
        0x26444c4ba73c1f692533ddcf1827e56f5cefe27cbbd169c87ff11c443e99aa8d;
    bytes constant SCHEMA_EXAMPLE_SIG =
        hex"fb2c5b4fc6ab2a10b3026da227d1419529c7ac84f56779bdf3b862eebdec4102"
        hex"08bed0e00f2465d76f935a95e5abce64e064546a6c9a5a59e3336e578877ff9c1c";

    function setUp() public {
        executionLog = new ExecutionLog();
    }

    function _sign(uint256 pk, bytes32 payloadHash) internal pure returns (bytes memory) {
        bytes32 digest = payloadHash.toEthSignedMessageHash();
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(pk, digest);
        return abi.encodePacked(r, s, v);
    }

    function testRecordEmitsEvent() public {
        bytes32 payloadHash = keccak256("test-payload");
        bytes memory sig = _sign(HARDHAT_KEY_0, payloadHash);

        vm.expectEmit(true, true, false, true);
        emit ExecutionLog.ExecutionRecorded(HARDHAT_ADDR_0, payloadHash, block.timestamp);
        executionLog.record(payloadHash, sig);
    }

    function testRecordIndependentOfSender() public {
        bytes32 payloadHash = keccak256("from-another-relayer");
        bytes memory sig = _sign(HARDHAT_KEY_0, payloadHash);

        address relayer = address(0xBEEF);
        vm.prank(relayer);

        vm.expectEmit(true, true, false, true);
        emit ExecutionLog.ExecutionRecorded(HARDHAT_ADDR_0, payloadHash, block.timestamp);
        executionLog.record(payloadHash, sig);
    }

    function testRecordRevertsOnMalformedSignature() public {
        bytes32 payloadHash = keccak256("malformed");
        bytes memory badSig = new bytes(65);

        vm.expectRevert();
        executionLog.record(payloadHash, badSig);
    }

    /// @notice Cross-language vector: a signature produced by Python
    ///         (sdk/src/rsynth/sign.py over SCHEMA_EXAMPLE, Hardhat key #0)
    ///         must recover to the same address inside Solidity. Catches
    ///         EIP-191 prefix or canonicalization drift at the boundary.
    function testRecoversPythonProducedSignature() public {
        vm.expectEmit(true, true, false, true);
        emit ExecutionLog.ExecutionRecorded(
            HARDHAT_ADDR_0,
            SCHEMA_EXAMPLE_HASH,
            block.timestamp
        );
        executionLog.record(SCHEMA_EXAMPLE_HASH, SCHEMA_EXAMPLE_SIG);
    }
}
