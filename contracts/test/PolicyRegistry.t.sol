// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Test.sol";
import {PolicyRegistry} from "../src/PolicyRegistry.sol";

contract PolicyRegistryTest is Test {
    PolicyRegistry registry;

    bytes32 constant POLICY_A = keccak256("policy-a");
    bytes32 constant POLICY_B = keccak256("policy-b");
    bytes32 constant URI_HASH = keccak256("hf://lerobot/smolvla-base@rev");

    function setUp() public {
        registry = new PolicyRegistry();
    }

    function testRegisterStoresRecord() public {
        registry.register(POLICY_B, POLICY_A, URI_HASH);

        (bytes32 parentId, bytes32 sourceUriHash, address registrant, uint256 registeredBlock) =
            registry.policies(POLICY_B);
        assertEq(parentId, POLICY_A);
        assertEq(sourceUriHash, URI_HASH);
        assertEq(registrant, address(this));
        assertEq(registeredBlock, block.number);
    }

    function testRegisterEmitsEvent() public {
        vm.expectEmit(true, true, true, true);
        emit PolicyRegistry.PolicyRegistered(POLICY_B, POLICY_A, address(this), URI_HASH);
        registry.register(POLICY_B, POLICY_A, URI_HASH);
    }

    function testDuplicateIdReverts() public {
        registry.register(POLICY_A, bytes32(0), URI_HASH);

        vm.expectRevert(PolicyRegistry.PolicyAlreadyRegistered.selector);
        registry.register(POLICY_A, bytes32(0), URI_HASH);
    }

    function testZeroPolicyIdReverts() public {
        vm.expectRevert(PolicyRegistry.ZeroPolicyId.selector);
        registry.register(bytes32(0), POLICY_A, URI_HASH);
    }

    /// @notice Parents may live off-chain: registering a child whose parent
    ///         was never registered must succeed.
    function testUnregisteredParentAllowed() public {
        registry.register(POLICY_B, POLICY_A, URI_HASH);

        (, , address registrant, ) = registry.policies(POLICY_B);
        assertEq(registrant, address(this));
        (, , address parentRegistrant, ) = registry.policies(POLICY_A);
        assertEq(parentRegistrant, address(0));
    }

    function testRootRegistrationWithZeroParent() public {
        registry.register(POLICY_A, bytes32(0), URI_HASH);

        (bytes32 parentId, , address registrant, ) = registry.policies(POLICY_A);
        assertEq(parentId, bytes32(0));
        assertEq(registrant, address(this));
    }
}
