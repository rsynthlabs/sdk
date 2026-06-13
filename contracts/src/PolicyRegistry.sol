// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title PolicyRegistry — append-only on-chain policy lineage registry.
/// @notice See docs/v0.2/POLICY-LINEAGE.md. Storage-based registry: diverges
///         from the event-only sketch in §5 option C. No admin, no upgrades.
///         Registering with an unregistered parent is allowed (off-chain
///         parents are legal); bytes32(0) parentId means root (no parent).
contract PolicyRegistry {
    error PolicyAlreadyRegistered();
    error ZeroPolicyId();

    struct PolicyRecord {
        bytes32 parentId;
        bytes32 sourceUriHash;
        address registrant;
        uint256 registeredBlock;
    }

    mapping(bytes32 => PolicyRecord) public policies;

    event PolicyRegistered(
        bytes32 indexed policyId,
        bytes32 indexed parentId,
        address indexed registrant,
        bytes32 sourceUriHash
    );

    function register(bytes32 policyId, bytes32 parentId, bytes32 sourceUriHash) external {
        if (policyId == bytes32(0)) revert ZeroPolicyId();
        if (policies[policyId].registrant != address(0)) revert PolicyAlreadyRegistered();
        policies[policyId] = PolicyRecord(parentId, sourceUriHash, msg.sender, block.number);
        emit PolicyRegistered(policyId, parentId, msg.sender, sourceUriHash);
    }
}
