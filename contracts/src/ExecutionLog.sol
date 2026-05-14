// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title ExecutionLog — anchor robot execution payload hashes on-chain.
/// @notice See SCHEMA.md §4. This is a scaffold; verification logic is not yet implemented.
contract ExecutionLog {
    event ExecutionRecorded(
        uint256 indexed agentId,
        bytes32 indexed payloadHash,
        uint256 blockTimestamp
    );

    /// @notice Anchor a signed payload hash. Reverts if signature does not match
    ///         the address registered for `agentId` in the ERC-8004 registry.
    /// @dev    Implementation pending. Currently no-op except event emission.
    function record(
        uint256 agentId,
        bytes32 payloadHash,
        bytes calldata signature
    ) external {
        // TODO: ERC-8004 registry lookup + EIP-191 recover + match check.
        // For now, emit unconditionally so off-chain tooling can be tested.
        signature; // silence unused-var warning
        emit ExecutionRecorded(agentId, payloadHash, block.timestamp);
    }
}
